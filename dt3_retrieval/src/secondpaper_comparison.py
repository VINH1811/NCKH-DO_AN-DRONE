"""LG-03: compare model, query language and typed/ASR input on frozen dev."""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "checkpoints/hf_cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import numpy as np
import pandas as pd
from secondpaper_baseline import checked_manifest, load_data, rank_tracks, query_metrics, clustered_ci, sha256, dump

CONFIG = ROOT / "configs/LG03-comparison.json"
CACHE = ROOT / "data/cache/LG03-openclip"


def dev_data():
    base = json.loads((ROOT / "configs/LG02-mclip.json").read_text())
    lock = json.loads((ROOT / "data/splits/LG02_split_lock.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "data/splits/LG02_split_manifest.csv"
    if sha256(manifest_path) != lock["manifest_sha256"]:
        raise ValueError("Frozen split was modified")
    if base != lock["config"]:
        raise ValueError("Baseline config semantics were modified")
    # Git/editor may change LF to CRLF; preserve the old lock and check JSON semantics.
    manifest = pd.read_csv(manifest_path)
    root, an, kf, emb = load_data(base)
    dev = an.set_index("annot_id").loc[manifest.loc[manifest.split == "dev", "annot_id"]].reset_index()
    return root, dev, kf, emb, lock


class CropDataset:
    def __init__(self, paths, transform):
        self.paths, self.transform = paths, transform

    def __len__(self): return len(self.paths)

    def __getitem__(self, i):
        from PIL import Image
        with Image.open(self.paths[i]) as image:
            return self.transform(image.convert("RGB"))


def openclip_model(config):
    import open_clip
    model, _, transform = open_clip.create_model_and_transforms(
        config["openclip_model"], pretrained=config["openclip_pretrained"])
    return model, transform, open_clip.get_tokenizer(config["openclip_model"])


def index_images(config):
    import torch
    from torch.utils.data import DataLoader
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(config["seed"])
    root, dev, kf, old_emb, lock = dev_data()
    frames = kf[kf.nguon.isin(config["sources"])].reset_index(drop=True)
    paths = [str(root / "crops" / x) for x in frames.crop_path]
    missing = [p for p in paths if not Path(p).is_file()]
    if missing: raise ValueError(f"Missing crops: {missing[:10]}")
    CACHE.mkdir(parents=True, exist_ok=True)
    ids = frames.kf_id.to_numpy()
    fingerprint = {"model": config["openclip_model"], "pretrained": config["openclip_pretrained"],
                   "precision": config["image_precision"], "config_sha256": sha256(CONFIG),
                   "keyframe_manifest_sha256": lock["input_sha256"]["manifest/keyframes.csv"],
                   "rows": len(frames), "dim": 512}
    progress_path = CACHE / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        if progress["fingerprint"] != fingerprint: raise ValueError("Index resume fingerprint mismatch")
        cursor = progress["cursor"]
        target = np.lib.format.open_memmap(CACHE / "embeddings.npy", mode="r+")
        if not np.array_equal(ids, np.load(CACHE / "kf_ids.npy")): raise ValueError("Index ID order changed")
    else:
        cursor = 0
        target = np.lib.format.open_memmap(CACHE / "embeddings.npy", mode="w+", dtype=np.float32, shape=(len(frames), 512))
        np.save(CACHE / "kf_ids.npy", ids)
    if cursor == len(frames):
        print("OpenCLIP gallery already complete", flush=True); return
    model, transform, _ = openclip_model(config)
    model.eval().to("cuda")
    torch.cuda.reset_peak_memory_stats()
    loader = DataLoader(CropDataset(paths[cursor:], transform), batch_size=config["image_batch_size"],
                        num_workers=config["image_workers"], pin_memory=True, shuffle=False)
    start, starting_cursor = time.perf_counter(), cursor
    timing = []
    with torch.inference_mode():
        for batch in loader:
            batch = batch.to("cuda", non_blocking=True)
            tick = time.perf_counter()
            with torch.autocast("cuda", dtype=torch.float16):
                vector = model.encode_image(batch)
            vector = torch.nn.functional.normalize(vector.float(), dim=1).cpu().numpy()
            if not np.isfinite(vector).all(): raise ValueError("Nonfinite image embedding")
            target[cursor:cursor + len(vector)] = vector
            cursor += len(vector)
            timing.append({"end_row": cursor, "images": len(vector), "inference_transfer_ms": (time.perf_counter() - tick) * 1000})
            if cursor % (config["image_batch_size"] * 16) == 0 or cursor == len(frames):
                target.flush()
                dump(progress_path, {"fingerprint": fingerprint, "cursor": cursor})
                elapsed = time.perf_counter() - start
                rate = (cursor - starting_cursor) / elapsed
                print(f"OpenCLIP images {cursor}/{len(frames)}; {rate:.1f} images/s; ETA {(len(frames)-cursor)/rate/60:.1f} min", flush=True)
    pd.DataFrame(timing).to_csv(CACHE / "image_batch_timings.csv", index=False)
    info = {**fingerprint, "embeddings_sha256": sha256(CACHE / "embeddings.npy"),
            "ids_sha256": sha256(CACHE / "kf_ids.npy"), "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
            "elapsed_seconds_this_session": time.perf_counter() - start,
            "indexing_scope": "crop decoding/preprocessing + FP16 image inference + normalize FP32 + transfer + save; not online query latency",
            "split_sha256": lock["manifest_sha256"], "implementation_sha256": sha256(Path(__file__))}
    dump(CACHE / "index_info.json", info)
    print(json.dumps(info, indent=2), flush=True)


def reviewed_queries(dev):
    path = ROOT / "configs/LG03_translation_review.csv"
    review = pd.read_csv(path, keep_default_na=False)
    if set(review.annot_id) != set(dev.annot_id) or not review.annot_id.is_unique:
        raise ValueError("Translation review must cover each dev query exactly once")
    review = review.set_index("annot_id").loc[dev.annot_id].reset_index()
    for original, checked in zip(dev.itertuples(), review.itertuples()):
        if original.text_vi != checked.text_vi or original.dich_en != checked.original_en:
            raise ValueError("Translation review no longer matches source")
        if not checked.reviewed_en.strip() or checked.status not in {"reviewed", "corrected", "ambiguous_preserved"}:
            raise ValueError("Unreviewed translation")
    return review


def paired_difference(left, right, metric, seed, samples):
    """Preserve query pairing and target-track clusters for a contrast."""
    if not left.index.is_unique or not right.index.is_unique or set(left.index) != set(right.index):
        raise ValueError("Paired comparison needs the same unique query IDs")
    right = right.loc[left.index]
    if not np.array_equal(left.track_id.to_numpy(), right.track_id.to_numpy()):
        raise ValueError("Paired comparison target labels changed")
    difference = right[metric].to_numpy() - left[metric].to_numpy()
    low, high = clustered_ci(difference, left.track_id, seed, samples)
    return float(difference.mean() * 100), low * 100, high * 100


def run_queries(config):
    import torch
    import transformers
    from multilingual_clip import pt_multilingual_clip
    from huggingface_hub import hf_hub_download
    torch.manual_seed(config["seed"])
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    root, dev, kf, emb, lock = dev_data()
    review = reviewed_queries(dev)
    image_info = json.loads((CACHE / "index_info.json").read_text())
    if image_info["config_sha256"] != sha256(CONFIG): raise ValueError("Image config changed")
    image_ids = np.load(CACHE / "kf_ids.npy")
    image_vectors = np.load(CACHE / "embeddings.npy", mmap_mode="r")
    if sha256(CACHE / "embeddings.npy") != image_info["embeddings_sha256"]: raise ValueError("Image cache modified")
    image_meta = kf.set_index("kf_id").loc[image_ids].reset_index()
    query_texts = {
        "typed_vi": dev.text_vi.tolist(),
        "typed_en_reviewed": review.reviewed_en.tolist(),
        "spoken_whisper_vi": dev.asr_whisper.tolist(),
        "spoken_phowhisper_vi": dev.asr_phowhisper.tolist()
    }
    for variant, texts in query_texts.items():
        if any(not isinstance(s, str) or not s.strip() for s in texts): raise ValueError(f"Missing query: {variant}")
    output = ROOT / "predictions" / config["run_id"]
    output.mkdir(parents=True, exist_ok=True)
    for family in ["M-CLIP", "OpenCLIP"]:
        if family == "M-CLIP":
            model = pt_multilingual_clip.MultilingualCLIP.from_pretrained(config["mclip_model"], revision=config["mclip_revision"], local_files_only=True)
            tokenizer = transformers.AutoTokenizer.from_pretrained(config["mclip_model"], revision=config["mclip_revision"], local_files_only=True, clean_up_tokenization_spaces=False)
            full_vectors, metadata = emb, kf
            weight = hf_hub_download(config["mclip_model"], "pytorch_model.bin", revision=config["mclip_revision"], local_files_only=True)
        else:
            model, _, tokenizer = openclip_model(config)
            full_vectors, metadata = image_vectors, image_meta
            weight = hf_hub_download("laion/CLIP-ViT-B-32-xlm-roberta-base-laion5B-s13B-b90k", "open_clip_pytorch_model.bin", local_files_only=True)
        model.eval().to("cuda")
        torch.cuda.reset_peak_memory_stats()
        galleries = {}
        for source in config["sources"]:
            idx = np.flatnonzero(metadata.nguon.to_numpy() == source)
            galleries[source] = (np.asarray(full_vectors[idx]), metadata.iloc[idx].track_id.to_numpy())
        def forward(text):
            if family == "M-CLIP":
                tokens = tokenizer([text], padding=True, truncation=False, return_tensors="pt")
                if tokens["input_ids"].shape[1] > 512: raise ValueError("M-CLIP truncation would occur")
                tokens = {k: v.to("cuda") for k, v in tokens.items()}
                hidden = model.transformer(**tokens).last_hidden_state
                mask = tokens["attention_mask"]
                pooled = (hidden * mask.unsqueeze(2)).sum(1) / mask.sum(1)[:, None]
                vector = model.LinearTransformation(pooled)
            else:
                vector = model.encode_text(tokenizer([text]).to("cuda"))
            return torch.nn.functional.normalize(vector.float(), dim=1)
        for variant in config["variants"]:
            texts = query_texts[variant]
            path = output / family / variant
            path.mkdir(parents=True, exist_ok=True)
            samples, vectors = [], []
            with torch.inference_mode():
                for source in config["sources"]:
                    index = int(np.flatnonzero(dev.nguon.to_numpy() == source)[0])
                    images, tracks = galleries[source]
                    for _ in range(config["warmup"]):
                        v = forward(texts[index]); torch.cuda.synchronize()
                        rank_tracks(images @ v.cpu().numpy()[0], tracks)
                for rep in range(config["latency_repeats"]):
                    for i, row in enumerate(dev.itertuples()):
                        torch.cuda.synchronize(); tick = time.perf_counter()
                        v = forward(texts[i]); torch.cuda.synchronize(); after_model = time.perf_counter()
                        q = v.cpu().numpy()[0]
                        images, tracks = galleries[row.nguon]
                        ranked, scores = rank_tracks(images @ q, tracks)
                        done = time.perf_counter()
                        samples.append({"annot_id": int(row.annot_id), "nguon": row.nguon, "repeat": rep,
                                        "model_ms": (after_model-tick)*1000, "pipeline_ms": (done-tick)*1000})
                        if rep == 0: vectors.append(q)
                    print(f"{family}/{variant}: repeat {rep+1}/3 complete", flush=True)
            q = np.asarray(vectors, dtype=np.float32)
            if not np.isfinite(q).all(): raise ValueError("Nonfinite query")
            np.save(path / "query_embeddings.npy", q)
            np.save(path / "query_ids.npy", dev.annot_id.to_numpy())
            pd.DataFrame(samples).to_csv(path / "latency_samples.csv", index=False)
            pd.DataFrame({"annot_id": dev.annot_id, "text": texts}).to_csv(path / "queries.csv", index=False)
            info = {"family": family, "variant": variant, "dimension": q.shape[1], "text_precision": "FP32",
                    "checkpoint_sha256": sha256(weight), "split_sha256": lock["manifest_sha256"],
                    "config_sha256": sha256(CONFIG), "review_sha256": sha256(ROOT / "configs/LG03_translation_review.csv"),
                    "query_embeddings_sha256": sha256(path / "query_embeddings.npy"),
                    "hardware": torch.cuda.get_device_name(0), "peak_allocated_mib": torch.cuda.max_memory_allocated()/2**20,
                    "asr_latency_included": False, "implementation_sha256": sha256(Path(__file__))}
            dump(path / "model_info.json", info)
        del model, tokenizer, galleries, full_vectors
        gc.collect(); torch.cuda.empty_cache()
    env = ROOT / "env" / config["run_id"]
    env.mkdir(parents=True, exist_ok=True)
    for command, filename in [([os.sys.executable, "-m", "pip", "freeze"], "pip_freeze.txt"),
                              (["nvidia-smi"], "nvidia_smi.txt"), (["git", "rev-parse", "HEAD"], "git_commit.txt")]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (env / filename).write_text(result.stdout+result.stderr, encoding="utf-8")
    (env / "implementation.py").write_bytes(Path(__file__).read_bytes())


def evaluate(config):
    root, dev, kf, emb, lock = dev_data()
    review = reviewed_queries(dev)
    image_info = json.loads((CACHE / "index_info.json").read_text())
    image_ids = np.load(CACHE / "kf_ids.npy")
    image_vectors = np.load(CACHE / "embeddings.npy", mmap_mode="r")
    image_meta = kf.set_index("kf_id").loc[image_ids].reset_index()
    output = ROOT / "predictions" / config["run_id"]
    summary, long_rows, comparison = [], [], []
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    for family in ["M-CLIP", "OpenCLIP"]:
        vectors, metadata = (emb, kf) if family == "M-CLIP" else (image_vectors, image_meta)
        galleries = {}
        for source in config["sources"]:
            idx = np.flatnonzero(metadata.nguon.to_numpy() == source)
            galleries[source] = (np.asarray(vectors[idx]), metadata.iloc[idx].track_id.to_numpy())
        for variant in config["variants"]:
            path = output / family / variant
            info = json.loads((path / "model_info.json").read_text())
            for key, expected in [("split_sha256", lock["manifest_sha256"]), ("config_sha256", sha256(CONFIG)),
                                  ("review_sha256", sha256(ROOT / "configs/LG03_translation_review.csv")),
                                  ("query_embeddings_sha256", sha256(path / "query_embeddings.npy"))]:
                if info[key] != expected: raise ValueError(f"Changed provenance: {key}")
            queries = np.load(path / "query_embeddings.npy")
            ids = np.load(path / "query_ids.npy")
            if not np.array_equal(ids, dev.annot_id.to_numpy()): raise ValueError("Dev query order changed")
            rows, tops = [], []
            for i, r in enumerate(dev.itertuples()):
                images, tracks = galleries[r.nguon]
                ranked, scores = rank_tracks(images @ queries[i], tracks)
                rank, metrics = query_metrics(ranked, r.track_id)
                rows.append({"annot_id": r.annot_id, "track_id": r.track_id, "nguon": r.nguon,
                             "camera_id": r.camera_id, "model": family, "variant": variant, "rank": rank, **metrics})
                for j in range(10): tops.append({"annot_id": r.annot_id, "rank": j+1, "track_id": int(ranked[j]), "score": float(scores[j])})
            per_query = pd.DataFrame(rows)
            per_query.to_csv(path / "per_query.csv", index=False)
            pd.DataFrame(tops).to_csv(path / "top10_tracks.csv", index=False)
            comparison.extend(rows)
            timings = pd.read_csv(path / "latency_samples.csv")
            for source, group in per_query.groupby("nguon"):
                n_gallery = len(np.unique(galleries[source][1]))
                source_times = timings[timings.nguon == source]
                language = "en" if variant == "typed_en_reviewed" else "vi"
                mode = "typed" if variant.startswith("typed") else "spoken_ASR"
                record = {"model": family, "language": language, "input_mode": mode,
                          "asr": "none" if mode == "typed" else ("PhoWhisper" if "phowhisper" in variant else "Whisper"),
                          "variant": variant, "source": source, "split": "dev", "n": len(group), "gallery_tracks": n_gallery}
                notes = (f"variant={variant};language={language};mode={mode};same 76 dev queries;source={source};"
                         "max cosine per track;single labeled relevant;mAP=MRR;CI cluster bootstrap by target track;"
                         "test not evaluated;ASR transcripts from M1, ASR inference latency excluded;"
                         "English semantically reviewed by Codex; 3 target crops spot-checked; not human sign-off;"
                         "OpenCLIP image inference FP16, text FP32; M-CLIP image provenance per M1;"
                         "GPU schedule isolation unverified;uncommitted worktree")
                base = {"run_id": config["run_id"], "date": "2026-10-06", "commit": commit, "task_id": "LG-03",
                        "dataset": f"SecondPaper-M1-{source}", "split": "dev", "model": family,
                        "checkpoint_sha256": info["checkpoint_sha256"], "precision": "text FP32; image FP16" if family == "OpenCLIP" else "text FP32; supplied image FP32 vectors",
                        "n": len(group), "hardware": info["hardware"], "notes": notes}
                for metric in ["Recall@1", "Recall@5", "Recall@10", "mAP"]:
                    value = float(group[metric].mean())
                    low, high = clustered_ci(group[metric], group.track_id, config["seed"], config["bootstrap_samples"])
                    chance = min(int(metric.split("@")[1]),n_gallery)/n_gallery if metric.startswith("Recall") else sum(1/i for i in range(1,n_gallery+1))/n_gallery
                    statement = "CI overlaps chance; inconclusive under chosen CI" if low <= chance <= high else ("CI above chance" if low > chance else "CI below chance")
                    record[metric+"_pct"] = value*100
                    record[metric+"_ci95_low_pct"], record[metric+"_ci95_high_pct"] = low*100, high*100
                    record[metric+"_interpretation"] = statement
                    long_rows.append({**base,"metric": metric,"value": value,"ci95_low": low,"ci95_high": high,"chance_level": chance,"notes": notes+";"+statement})
                for scope, column in [("text", "model_ms"), ("pipeline", "pipeline_ms")]:
                    for p in [50,95]:
                        value = float(np.percentile(source_times[column],p))
                        record[f"{scope}_p{p}_ms"] = value
                        long_rows.append({**base,"metric":f"{scope}_latency_p{p}_ms","value":value,"ci95_low":"","ci95_high":"","chance_level":"","n":len(source_times)})
                summary.append(record)
            print(f"Evaluated {family}/{variant}", flush=True)
    columns = "run_id,date,commit,task_id,dataset,split,model,checkpoint_sha256,precision,metric,value,ci95_low,ci95_high,n,chance_level,hardware,notes".split(",")
    metrics_dir = ROOT / "metrics"
    pd.DataFrame(summary).to_csv(metrics_dir / "LG03_model_language_input.csv", index=False)
    pd.DataFrame(long_rows).reindex(columns=columns).to_csv(metrics_dir / "LG03_metrics_17_columns.csv", index=False)
    # Paired bootstrap difference (OpenCLIP minus M-CLIP), same target tracks/queries.
    all_queries = pd.DataFrame(comparison)
    pairs = []
    for variant in config["variants"]:
        for source in config["sources"]:
            subset = all_queries[(all_queries.variant == variant) & (all_queries.nguon == source)]
            left = subset[subset.model == "M-CLIP"].set_index("annot_id")
            right = subset[subset.model == "OpenCLIP"].set_index("annot_id").loc[left.index]
            for metric in ["Recall@1","Recall@5","Recall@10","mAP"]:
                value, low, high = paired_difference(left, right, metric, config["seed"], config["bootstrap_samples"])
                pairs.append({"contrast":"OpenCLIP minus M-CLIP","variant":variant,"source":source,"metric":metric,"n":len(left),
                              "difference_percentage_points":value,"ci95_low_pp":low,"ci95_high_pp":high,
                              "interpretation":"CI overlaps zero; paired comparison inconclusive" if low<=0<=high else ("OpenCLIP higher under selected CI" if low>0 else "M-CLIP higher under selected CI")})
    for family in ["M-CLIP", "OpenCLIP"]:
        for source in config["sources"]:
            subset = all_queries[(all_queries.model == family) & (all_queries.nguon == source)]
            left = subset[subset.variant == "typed_vi"].set_index("annot_id")
            for variant in ["typed_en_reviewed", "spoken_whisper_vi", "spoken_phowhisper_vi"]:
                right = subset[subset.variant == variant].set_index("annot_id")
                for metric in ["Recall@1", "Recall@5", "Recall@10", "mAP"]:
                    value, low, high = paired_difference(left, right, metric, config["seed"], config["bootstrap_samples"])
                    pairs.append({"contrast":f"{family}: {variant} minus typed_vi", "variant":variant,"source":source,"metric":metric,"n":len(left),
                                  "difference_percentage_points":value,"ci95_low_pp":low,"ci95_high_pp":high,
                                  "interpretation":"CI overlaps zero; paired comparison inconclusive" if low<=0<=high else ("variant higher under selected CI" if low>0 else "typed Vietnamese higher under selected CI")})
    pd.DataFrame(pairs).to_csv(metrics_dir / "LG03_paired_model_comparison.csv",index=False)
    readable = []
    labels = {"typed_vi": "Gõ — tiếng Việt trực tiếp", "typed_en_reviewed": "Gõ — bản dịch tiếng Anh đã rà soát",
              "spoken_whisper_vi": "Nói — bản chép Whisper tiếng Việt", "spoken_phowhisper_vi": "Nói — bản chép PhoWhisper tiếng Việt"}
    readable.extend(["LG-03 — MÔ HÌNH × NGÔN NGỮ × GÕ/NÓI — DEV, 06/10/2026", "",
                     "Mỗi cấu hình dùng cùng 76 câu dev; edata (70 câu) và video (6 câu) báo cáo riêng.",
                     "174 câu test chưa được mã hóa hoặc đánh giá. Latency truy vấn nói không gồm chạy ASR.", ""])
    for r in summary:
        readable.append(f"{r['source']} | {r['model']} | {labels[r['variant']]} | n={r['n']}")
        for key in ["Recall@1","Recall@5","Recall@10","mAP"]:
            interpretation = r[key+"_interpretation"]
            sentence = "CI chứa mức ngẫu nhiên; chưa đủ bằng chứng theo CI đã chọn" if interpretation.startswith("CI overlaps") else ("CI trên mức ngẫu nhiên" if interpretation == "CI above chance" else "CI dưới mức ngẫu nhiên")
            readable.append(f"  {key}: {r[key+'_pct']:.2f}%")
            readable.append(f"    CI 95%: [{r[key+'_ci95_low_pct']:.2f}; {r[key+'_ci95_high_pct']:.2f}]% — {sentence}")
        readable.append(f"  Text model p50/p95: {r['text_p50_ms']:.2f}/{r['text_p95_ms']:.2f} ms")
        readable.append(f"  Pipeline gallery có sẵn p50/p95: {r['pipeline_p50_ms']:.2f}/{r['pipeline_p95_ms']:.2f} ms\n")
    (ROOT / "reports/LG03_comparison_readable.txt").write_text("\n".join(readable),encoding="utf-8-sig")
    print(pd.DataFrame(summary)[["source","model","variant","n","Recall@1_pct","Recall@5_pct","Recall@10_pct","mAP_pct"]].to_string(index=False),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["index","run","evaluate"])
    args=parser.parse_args()
    config=json.loads(CONFIG.read_text())
    if args.stage=="index": index_images(config)
    elif args.stage=="run": run_queries(config)
    else: evaluate(config)


if __name__=="__main__": main()
