"""LG04: M3 detector/crop -> paired multilingual OpenCLIP -> crop cosine.

Pilot session 1 only. No tracking, identity metrics, ASR or rejection threshold.
All media paths in sources.csv are relative to that CSV (absolute paths allowed).
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "checkpoints/hf_cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / "data/cache/ultralytics"))

import numpy as np

FIELDS = ["candidate_id", "session_id", "camera_id", "source_id", "frame_index",
          "timestamp_ms", "confidence", "bbox_xyxy", "padded_bbox", "crop_path"]


def resolve(p):
    return (ROOT / p).resolve()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def normalized(v):
    v = np.asarray(v, dtype=np.float32)
    if v.ndim != 2 or not np.isfinite(v).all():
        raise ValueError("Embeddings must be a finite 2D matrix")
    lengths = np.linalg.norm(v, axis=1, keepdims=True)
    if np.any(lengths <= 0):
        raise ValueError("Zero embedding")
    return v / lengths


def ranking(gallery, query, k):
    if k < 1:
        raise ValueError("top-k must be positive")
    g, q = normalized(gallery), normalized(query)
    if q.shape != (1, g.shape[1]):
        raise ValueError("Query and gallery must share an embedding space")
    scores = (g @ q[0]).clip(-1, 1)
    # Stable ordering: ties use gallery/candidate order.
    ids = np.argsort(-scores, kind="stable")[:k]
    return ids, scores[ids]


def sources(config):
    path = resolve(config["sources"])
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No pilot inputs in {path}")
    for i, row in enumerate(rows):
        if row.get("session_id") != "session1" or not row.get("camera_id", "").strip():
            raise ValueError("Every input needs session_id=session1 and camera_id")
        p = Path(row["path"])
        row["resolved_path"] = str((path.parent / p).resolve())
        if not Path(row["resolved_path"]).is_file():
            raise FileNotFoundError(row["resolved_path"])
        row["timestamp_offset_ms"] = float(row.get("timestamp_offset_ms") or 0)
        if not np.isfinite(row["timestamp_offset_ms"]):
            raise ValueError("Invalid timestamp offset")
        row["source_id"] = f"source_{i:03d}"
    return rows


def preflight(config):
    failures = []
    for name in ("torch", "cv2", "yaml", "ultralytics", "open_clip"):
        if importlib.util.find_spec(name) is None:
            failures.append(f"Missing Python module: {name}")
    try:
        rows = sources(config)
    except (OSError, ValueError, KeyError) as e:
        failures.append(str(e)); rows = []
    weight = resolve(config["weights"])
    if not weight.is_file():
        failures.append(f"Missing M3 weights: {weight}")
    elif sha(weight) != config["weights_sha256"]:
        failures.append("M3 weight SHA256 mismatch")
    for name in ("detector.py", "crop_person.py"):
        p = resolve(config["m3_package"]) / "src" / name
        if not p.is_file():
            failures.append(f"Missing M3 module: {p}")
    if config["session_id"] != "session1" or config["frame_stride"] < 1:
        failures.append("Only session1 with positive frame_stride is supported")
    if config["device"] == "cuda" and importlib.util.find_spec("torch"):
        import torch
        if not torch.cuda.is_available(): failures.append("CUDA is unavailable")
    return {"ready_for_index": not failures, "failures": failures,
            "input_sources": len(rows), "model": config["openclip_model"],
            "scope": "preflight only; model cache checked on model loading"}


def m3_module(config, name):
    path = resolve(config["m3_package"]) / "src" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"m3_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encoder(config):
    import torch
    import open_clip
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    model, _, transform = open_clip.create_model_and_transforms(
        config["openclip_model"], pretrained=config["openclip_pretrained"])
    model.eval().to(config["device"])
    return model, transform, open_clip.get_tokenizer(config["openclip_model"])


def frames(row, config):
    import cv2
    p = Path(row["resolved_path"])
    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
        image = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError(f"Cannot decode {p}")
        yield 0, row["timestamp_offset_ms"], image
        return
    cap = cv2.VideoCapture(str(p))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or not np.isfinite(fps) or fps <= 0:
            raise ValueError(f"Cannot read video/FPS: {p}")
        i, selected = 0, 0
        while True:
            ok, image = cap.read()
            if not ok: break
            if i % config["frame_stride"] == 0:
                yield i, row["timestamp_offset_ms"] + i / fps * 1000, image
                selected += 1
                limit = config["max_frames_per_source"]
                if limit is not None and selected >= limit: break
            i += 1
        if selected == 0: raise ValueError(f"No readable video frames: {p}")
    finally:
        cap.release()


def index(config, config_path):
    ready = preflight(config)
    if not ready["ready_for_index"]:
        raise ValueError("\n".join(ready["failures"]))
    import cv2
    import torch
    import yaml
    from PIL import Image
    rows = sources(config)
    out = resolve(config["output"])
    if out.exists(): raise ValueError(f"Output exists; choose a new output path: {out}")
    # Load cached encoder before creating output so missing cache leaves no partial index.
    model, transform, _ = encoder(config)
    out.mkdir(parents=True)
    (out / "crops").mkdir()
    runtime = {"detector": {"weights": str(resolve(config["weights"]))},
               "target": {"class_id": 0, "class_name": "person"},
               "inference": {"imgsz": config["imgsz"], "conf": config["confidence"],
                             "iou": config["iou"], "device": 0 if config["device"] == "cuda" else "cpu"},
               "crop": {k: config[k] for k in ("padding_ratio", "min_width", "min_height")}}
    runtime_path = out / "m3_runtime.yaml"
    runtime_path.write_text(yaml.safe_dump(runtime), encoding="utf-8")
    detector = m3_module(config, "detector").PersonDetector(str(runtime_path))
    cropper = m3_module(config, "crop_person").PersonCropper(str(runtime_path))
    vectors, metadata, times = [], [], []
    with torch.inference_mode():
        for source in rows:
            for frame_id, timestamp, bgr in frames(source, config):
                tick = time.perf_counter()
                detections = detector.detect(bgr)
                selected = []
                for det in detections:
                    crop, info = cropper.crop(bgr, det["bbox_xyxy"])
                    if crop is None: continue
                    cid = f"candidate_{len(metadata):08d}"
                    crop_path = f"crops/{cid}.jpg"
                    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    Image.fromarray(rgb).save(out / crop_path, quality=95)
                    selected.append(transform(Image.fromarray(rgb)))
                    metadata.append(dict(candidate_id=cid, session_id="session1", camera_id=source["camera_id"],
                                         source_id=source["source_id"], frame_index=frame_id, timestamp_ms=timestamp,
                                         confidence=det["confidence"], bbox_xyxy=json.dumps(info["original_bbox"]),
                                         padded_bbox=json.dumps(info["padded_bbox"]), crop_path=crop_path))
                for start in range(0, len(selected), 8):
                    batch = torch.stack(selected[start:start + 8]).to(config["device"])
                    vectors.extend(normalized(model.encode_image(batch).float().cpu().numpy()))
                if config["device"] == "cuda": torch.cuda.synchronize()
                times.append({"source_id": source["source_id"], "frame_index": frame_id,
                              "crops": len(selected), "detector_crop_embedding_save_ms": (time.perf_counter()-tick)*1000})
            print(f"Finished {source['source_id']}: {len(metadata)} total crops", flush=True)
    matrix = np.asarray(vectors, dtype=np.float32).reshape(-1, config["embedding_dim"])
    np.save(out / "embeddings.npy", matrix)
    for name, records, fields in (("candidates.csv", metadata, FIELDS),
                                  ("frame_timings.csv", times, ["source_id", "frame_index", "crops", "detector_crop_embedding_save_ms"])):
        with (out / name).open("w", encoding="utf-8-sig", newline="") as f:
            w=csv.DictWriter(f, fieldnames=fields);w.writeheader();w.writerows(records)
    import importlib.metadata
    provenance = {"status": "indexed" if len(matrix) else "no_detections", "config": config,
                  "config_sha256": sha(config_path), "candidates": len(matrix), "processed_frames": len(times),
                  "weights_sha256": sha(resolve(config["weights"])),
                  "sources": [{**r, "sha256": sha(r["resolved_path"])} for r in rows],
                  "m3_sha256": {n: sha(resolve(config["m3_package"])/"src"/n) for n in ("detector.py","crop_person.py")},
                  "embeddings_sha256": sha(out/"embeddings.npy"), "candidates_sha256": sha(out/"candidates.csv"),
                  "implementation_sha256": sha(__file__),
                  "versions": {n: importlib.metadata.version(n) for n in ("torch","ultralytics","open_clip_torch")},
                  "timing_scope": "single-pass diagnostic; excludes video decode/model load, includes saving crops; not benchmark p50/p95",
                  "candidate_unit": "detected crop, NOT track or person identity"}
    dump(out / "index_info.json", provenance)
    print(json.dumps({k:provenance[k] for k in ("status","candidates","processed_frames")}), flush=True)


def search(config, query, output):
    import torch
    out = resolve(config["output"])
    info=json.loads((out/"index_info.json").read_text(encoding="utf-8"))
    if info["config"] != config: raise ValueError("Index config differs; rebuild with a new output path")
    for file, key in (("embeddings.npy","embeddings_sha256"),("candidates.csv","candidates_sha256")):
        if sha(out/file) != info[key]: raise ValueError(f"Index was modified: {file}")
    with (out/"candidates.csv").open(encoding="utf-8-sig",newline="") as f:
        candidates=list(csv.DictReader(f))
    gallery=np.load(out/"embeddings.npy",allow_pickle=False)
    if not candidates or len(gallery)!=len(candidates): raise ValueError("Empty or inconsistent gallery")
    if not query.strip(): raise ValueError("Query cannot be empty")
    destination=resolve(output)
    if destination.exists(): raise ValueError(f"Query output exists: {destination}")
    model, _, tokenizer=encoder(config)
    tick=time.perf_counter()
    with torch.inference_mode():
        feature=model.encode_text(tokenizer([query]).to(config["device"])).float().cpu().numpy()
    ids,scores=ranking(gallery,feature,config["top_k"])
    elapsed=(time.perf_counter()-tick)*1000
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["rank","query","cosine",*FIELDS]);w.writeheader()
        for rank,(i,score) in enumerate(zip(ids,scores),1):
            w.writerow({"rank":rank,"query":query,"cosine":float(score),**candidates[i]})
    dump(destination.with_suffix('.json'),{"query":query,"index_info_sha256":sha(out/'index_info.json'),
         "output_sha256":sha(destination),"single_query_ms":elapsed,"latency_is_benchmark":False,
         "ranking_unit":"crop; repeated people/frames possible; no identity metrics or rejection threshold"})
    print(f"Saved {len(ids)} crop candidates: {destination}")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['check','index','search'])
    p.add_argument('--config',default='configs/LG04-pilot-session1.json')
    query_group=p.add_mutually_exclusive_group()
    query_group.add_argument('--query')
    query_group.add_argument('--query-file',help='UTF-8 text file, recommended for Vietnamese in Windows conda run')
    p.add_argument('--output',default='data/pilot/session1/query_top10.csv')
    args=p.parse_args();config_path=resolve(args.config)
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    if args.stage=='check':
        result=preflight(config);print(json.dumps(result,ensure_ascii=False,indent=2))
        sys.exit(0 if result['ready_for_index'] else 2)
    elif args.stage=='index': index(config,config_path)
    else:
        if args.query is None and args.query_file is None:
            p.error('search requires --query or --query-file')
        query=resolve(args.query_file).read_text(encoding='utf-8-sig').strip() if args.query_file else args.query
        search(config,query,args.output)


if __name__=='__main__':
    main()
