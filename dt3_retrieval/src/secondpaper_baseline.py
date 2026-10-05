"""LG-02: frozen query split, M-CLIP text + supplied image embeddings.

Run prepare, encode and evaluate separately so metrics can be checked without GPU.
The image index is fixed and shared. Source-specific galleries never mix edata/video.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "checkpoints/hf_cache"))
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import numpy as np
import pandas as pd


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_data(config):
    root = ROOT / config["dataset_root"]
    an = pd.read_csv(root / "manifest/annotations_250.csv")
    kf = pd.read_csv(root / "manifest/keyframes.csv")
    emb = np.load(root / "emb/emb_f32.npy", mmap_mode="r")
    ids = np.load(root / "emb/emb_kf_id.npy")
    if emb.shape != (len(ids), config["embedding_dim"]):
        raise ValueError(f"Embedding shape mismatch: {emb.shape}")
    if len(set(ids.tolist())) != len(ids) or not kf.kf_id.is_unique:
        raise ValueError("Duplicate keyframe IDs")
    if set(ids.tolist()) != set(kf.kf_id.tolist()):
        raise ValueError("Embedding IDs do not match keyframe manifest")
    # Explicit ID join, never assume CSV order equals embedding order.
    kf = kf.set_index("kf_id").loc[ids].reset_index()
    return root, an, kf, emb


def prepare(config):
    root, an, kf, emb = load_data(config)
    hashes = {}
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        expected, name = line.split(maxsplit=1)
        name = name.strip().removeprefix("*")
        if name.startswith(("manifest/", "emb/")) or name in {"README.md", "index.db"}:
            actual = sha256(root / name)
            if actual != expected:
                raise ValueError(f"SHA256 mismatch: {name}")
            hashes[name] = actual
    if len(an) != 250 or not an.annot_id.is_unique or an.text_vi.isna().any():
        raise ValueError("Expected 250 unique, nonempty annotations")
    if not an.track_id.isin(kf.track_id).all():
        raise ValueError("Query target missing from gallery")
    if kf.groupby("track_id").camera_id.nunique().max() != 1:
        raise ValueError("Track spans cameras: need a different grouping policy")
    meta = kf.drop_duplicates("track_id").set_index("track_id")
    for r in an.itertuples():
        if r.camera_id != meta.loc[r.track_id, "camera_id"] or r.nguon != meta.loc[r.track_id, "nguon"]:
            raise ValueError(f"Annotation metadata mismatch: {r.annot_id}")
    norms = np.linalg.norm(emb, axis=1)
    if not np.isfinite(emb).all() or not np.allclose(norms, 1, atol=1e-4):
        raise ValueError("Provided embeddings must be finite and L2-normalized")
    manifest = an[["annot_id", "track_id", "camera_id", "nguon"]].copy()
    manifest["split"] = np.where(manifest.camera_id.isin(config["dev_cameras"]), "dev", "test")
    manifest["identity_key"] = manifest.track_id.map(lambda t: f"track:{t}")
    manifest["identity_scope"] = "dataset-local track; cross-camera identity unverified"
    manifest["seed"] = config["seed"]
    manifest = manifest.sort_values("annot_id").reset_index(drop=True)
    dev, test = [manifest[manifest.split == s] for s in ("dev", "test")]
    if set(dev.track_id) & set(test.track_id) or set(dev.camera_id) & set(test.camera_id):
        raise ValueError("Split leakage")
    path = ROOT / "data/splits/LG02_split_manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = manifest.to_csv(index=False, lineterminator="\n")
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise ValueError("Split is locked; refusing to overwrite a different manifest")
    path.write_text(content, encoding="utf-8")
    lock = {"manifest_sha256": sha256(path), "input_sha256": hashes,
            "config_sha256": sha256(ROOT / "configs/LG02-mclip.json"),
            "config": config,
            "split_unit": config["split_unit"], "dev_cameras": config["dev_cameras"],
            "counts": manifest.groupby(["nguon", "split"]).size().to_dict()}
    lock["counts"] = {f"{a}/{b}": int(n) for (a, b), n in lock["counts"].items()}
    dump(ROOT / "data/splits/LG02_split_lock.json", lock)
    audit = {"annotations": len(an), "annotated_tracks": int(an.track_id.nunique()),
             "keyframes": len(kf), "embedding_shape": list(emb.shape),
             "norm_range": [float(norms.min()), float(norms.max())],
             "sources": kf.groupby("nguon").agg(keyframes=("kf_id", "size"), tracks=("track_id", "nunique"), cameras=("camera_id", "nunique")).to_dict("index"),
             "annotation_cameras": an.groupby(["nguon", "camera_id"]).size().to_string(),
             "split_counts": lock["counts"], "integrity": "passed for extracted metadata and embeddings",
             "physical_identity_disjoint": "not verifiable; no person_id mapping",
             "original_evaluator": "not supplied; max-cosine track ranking is explicit local protocol"}
    dump(ROOT / "reports/LG02_data_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)


def checked_manifest(config):
    path = ROOT / "data/splits/LG02_split_manifest.csv"
    lock = json.loads((ROOT / "data/splits/LG02_split_lock.json").read_text(encoding="utf-8"))
    if sha256(path) != lock["manifest_sha256"]:
        raise ValueError("Locked split was modified")
    if lock["config_sha256"] != sha256(ROOT / "configs/LG02-mclip.json"):
        raise ValueError("Locked experiment config was modified; prepare again only before test exposure")
    if lock.get("config", config) != config:
        raise ValueError("Supplied experiment config differs from frozen config")
    return pd.read_csv(path), lock


def encode(config, split, device):
    import torch
    from huggingface_hub import hf_hub_download
    from multilingual_clip import pt_multilingual_clip
    import transformers

    manifest, lock = checked_manifest(config)
    if split not in {"dev", "test"}: raise ValueError(split)
    root, an, kf, emb = load_data(config)
    selected = an.set_index("annot_id").loc[manifest.loc[manifest.split == split, "annot_id"]].reset_index()
    out = ROOT / "predictions" / config["run_id"] / split
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config["seed"])
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    model = pt_multilingual_clip.MultilingualCLIP.from_pretrained(config["model"], revision=config["model_revision"], local_files_only=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(config["model"], revision=config["model_revision"], local_files_only=True, clean_up_tokenization_spaces=False)
    model.eval().to(device)
    if device == "cuda": torch.cuda.reset_peak_memory_stats()
    def sync():
        if device == "cuda": torch.cuda.synchronize()
    def forward(text):
        # M-CLIP.forward leaves tokenizer tensors on CPU. Move inputs explicitly.
        batch = tokenizer([text], padding=True, truncation=False, return_tensors="pt")
        if batch["input_ids"].shape[1] > config["max_tokens"]:
            raise ValueError("Query too long; refuse silent truncation")
        batch = {k: v.to(device) for k, v in batch.items()}
        states = model.transformer(**batch).last_hidden_state
        att = batch["attention_mask"]
        pooled = (states * att.unsqueeze(2)).sum(1) / att.sum(1)[:, None]
        return torch.nn.functional.normalize(model.LinearTransformation(pooled), dim=1)
    galleries = {}
    for source in selected.nguon.unique():
        idx = np.flatnonzero(kf.nguon.to_numpy() == source)
        galleries[source] = (np.asarray(emb[idx]), kf.iloc[idx].track_id.to_numpy())
    latencies, vectors = [], []
    with torch.inference_mode():
        for source in selected.nguon.unique():
            text = str(selected[selected.nguon == source].iloc[0].text_vi)
            e, tracks = galleries[source]
            for _ in range(config["warmup"]):
                warm = forward(text); sync()
                rank_tracks(e @ warm.cpu().numpy()[0], tracks)
        for rep in range(config["latency_repeats"]):
            for i, r in enumerate(selected.itertuples()):
                sync(); start = time.perf_counter()
                v = forward(r.text_vi)
                sync(); model_done = time.perf_counter()
                vector = v.cpu().numpy()[0]
                search_start = time.perf_counter()
                e, tracks = galleries[r.nguon]
                rank_tracks(e @ vector, tracks)
                done = time.perf_counter()
                latencies.append({"repeat": rep, "annot_id": int(r.annot_id),
                                  "model_ms": (model_done - start) * 1000,
                                  "search_ms": (done - search_start) * 1000,
                                  "pipeline_ms": (done - start) * 1000})
                if rep == 0: vectors.append(vector)
            print(f"Text inference repeat {rep + 1}/{config['latency_repeats']} done ({len(selected)} queries)", flush=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.shape != (len(selected), config["embedding_dim"]) or not np.isfinite(vectors).all():
        raise ValueError("Invalid query embeddings")
    np.save(out / "query_embeddings.npy", vectors)
    np.save(out / "query_ids.npy", selected.annot_id.to_numpy())
    pd.DataFrame(latencies).to_csv(out / "text_latency_samples.csv", index=False)
    checkpoint = hf_hub_download(config["model"], "pytorch_model.bin", revision=config["model_revision"], local_files_only=True)
    info = {"model": config["model"], "checkpoint_sha256": sha256(checkpoint),
            "device": device, "precision": "FP32", "batch_size": 1, "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda, "hardware": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
            "model_latency_scope": "tokenization + M-CLIP text inference + normalization; excludes loading and D2H",
            "pipeline_latency_scope": "tokenization + text inference + normalization + D2H + exact cosine + max per track + full ranking; cached gallery; excludes image indexing, model loading and IO",
            "implementation_sha256": sha256(Path(__file__)),
            "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20 if device == "cuda" else None,
            "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20 if device == "cuda" else None,
            "split_sha256": lock["manifest_sha256"], "query_embeddings_sha256": sha256(out / "query_embeddings.npy")}
    dump(out / "model_info.json", info)
    env = ROOT / "env" / config["run_id"]
    env.mkdir(parents=True, exist_ok=True)
    for command, name in [([os.sys.executable, "-m", "pip", "freeze"], "pip_freeze.txt"),
                          (["nvidia-smi"], "nvidia_smi.txt"), (["git", "rev-parse", "HEAD"], "git_commit.txt")]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (env / name).write_text(result.stdout + result.stderr, encoding="utf-8")
    print(json.dumps(info, indent=2), flush=True)


def rank_tracks(scores, track_ids):
    tracks, inverse = np.unique(track_ids, return_inverse=True)
    track_scores = np.full(len(tracks), -np.inf, dtype=np.float32)
    np.maximum.at(track_scores, inverse, scores)
    # Secondary key is stable track_id, for exact score ties.
    order = np.lexsort((tracks, -track_scores))
    return tracks[order], track_scores[order]


def query_metrics(ranked, target):
    hit = np.flatnonzero(ranked == target)
    if len(hit) != 1: raise ValueError("Exactly one labeled target track is required")
    rank = int(hit[0]) + 1
    return rank, {"Recall@1": float(rank <= 1), "Recall@5": float(rank <= 5),
                  "Recall@10": float(rank <= 10), "mAP": 1.0 / rank}


def clustered_ci(values, groups, seed, n_boot):
    values, groups = np.asarray(values), np.asarray(groups)
    unique = np.unique(groups)
    clusters = [values[groups == g] for g in unique]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        sample = rng.integers(0, len(clusters), len(clusters))
        sums = sum(clusters[i].sum() for i in sample)
        counts = sum(len(clusters[i]) for i in sample)
        draws.append(sums / counts)
    return np.quantile(draws, [0.025, 0.975]).tolist()


def evaluate(config, split):
    manifest, lock = checked_manifest(config)
    root, an, kf, emb = load_data(config)
    out = ROOT / "predictions" / config["run_id"] / split
    qids = np.load(out / "query_ids.npy")
    queries = np.load(out / "query_embeddings.npy")
    if set(qids.tolist()) != set(manifest.loc[manifest.split == split, "annot_id"].tolist()):
        raise ValueError("Query embeddings do not match split")
    info = json.loads((out / "model_info.json").read_text(encoding="utf-8"))
    if info["split_sha256"] != lock["manifest_sha256"] or info["query_embeddings_sha256"] != sha256(out / "query_embeddings.npy"):
        raise ValueError("Embedding provenance changed")
    times = pd.read_csv(out / "text_latency_samples.csv")
    query_rows, ranking_rows, search_times, gallery_stats = [], [], [], {}
    lookup = an.set_index("annot_id")
    for source in sorted(lookup.loc[qids, "nguon"].unique()):
        idx = np.flatnonzero(kf.nguon.to_numpy() == source)
        image_vectors = np.asarray(emb[idx])
        track_ids = kf.iloc[idx].track_id.to_numpy()
        gallery_stats[source] = {"keyframes": len(idx), "tracks": len(set(track_ids)), "cameras": int(kf.iloc[idx].camera_id.nunique())}
        positions = [i for i, qid in enumerate(qids) if lookup.loc[qid, "nguon"] == source]
        for _ in range(config["warmup"]): rank_tracks(image_vectors @ queries[positions[0]], track_ids)
        for rep in range(config["latency_repeats"]):
            for i in positions:
                qid = int(qids[i]); r = lookup.loc[qid]
                start = time.perf_counter()
                ranked, scores = rank_tracks(image_vectors @ queries[i], track_ids)
                ms = (time.perf_counter() - start) * 1000
                search_times.append({"repeat": rep, "annot_id": qid, "search_replay_ms": ms})
                if rep == 0:
                    rank, metric = query_metrics(ranked, int(r.track_id))
                    query_rows.append({"annot_id": qid, "track_id": int(r.track_id), "camera_id": r.camera_id,
                                       "nguon": source, "split": split, "target_rank": rank,
                                       "gallery_tracks": len(ranked), **metric})
                    for j in range(min(10, len(ranked))):
                        ranking_rows.append({"annot_id": qid, "rank": j + 1, "track_id": int(ranked[j]), "score": float(scores[j]), "relevant": bool(ranked[j] == r.track_id)})
        print(f"Evaluated {source}: {len(positions)} queries, {gallery_stats[source]}", flush=True)
    per_query = pd.DataFrame(query_rows).sort_values("annot_id")
    per_query.to_csv(out / "per_query.csv", index=False)
    pd.DataFrame(ranking_rows).to_csv(out / "top10_tracks.csv", index=False)
    search = pd.DataFrame(search_times)
    latency = times.merge(search, on=["repeat", "annot_id"], validate="one_to_one")
    latency = latency.merge(an[["annot_id", "nguon"]], on="annot_id", validate="many_to_one")
    latency.to_csv(out / "latency_samples.csv", index=False)
    result = []
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    for source, rows in per_query.groupby("nguon"):
        n_gallery = int(rows.gallery_tracks.iloc[0])
        notes = (f"source={source}; gallery={n_gallery} tracks; max cosine per track; single labeled relevant track; "
                 "mAP=MRR under this labeling; 95% CI bootstrap clustered by target track, conditional on selected cameras; "
                 "fixed M1 gallery; original paper evaluator unavailable; worktree has uncommitted implementation")
        base = dict(run_id=config["run_id"], date="2026-10-05", commit=commit, task_id="LG-02",
                    dataset=f"SecondPaper-M1-{source}", split=split, model=config["model"],
                    checkpoint_sha256=info["checkpoint_sha256"], precision=info["precision"],
                    n=len(rows), hardware=info["hardware"], notes=notes)
        for metric in ["Recall@1", "Recall@5", "Recall@10", "mAP"]:
            low, high = clustered_ci(rows[metric], rows.track_id, config["seed"], config["bootstrap_samples"])
            chance = min(int(metric.split("@")[1]), n_gallery) / n_gallery if metric.startswith("Recall") else sum(1/i for i in range(1, n_gallery + 1)) / n_gallery
            result.append({**base, "metric": metric, "value": rows[metric].mean(), "ci95_low": low, "ci95_high": high, "chance_level": chance})
        l = latency[latency.nguon == source]
        for scope, samples in [("text_model", l.model_ms), ("search", l.search_ms),
                               ("cached_gallery_pipeline", l.pipeline_ms)]:
            for p in [50, 95]:
                result.append({**base, "metric": f"{scope}_latency_p{p}_ms", "value": np.percentile(samples, p),
                               "ci95_low": "", "ci95_high": "", "chance_level": "", "n": len(samples),
                               "notes": notes + "; warmup=5 per source; repeats=3; batch=1; gallery preloaded; pipeline includes D2H; excludes image indexing, model loading and IO; shared-GPU isolation not verified"})
        if info["peak_allocated_mib"] is not None:
            result.append({**base, "metric": "peak_model_allocated_vram_mib", "value": info["peak_allocated_mib"],
                           "ci95_low": "", "ci95_high": "", "chance_level": "", "n": 1,
                           "notes": "PyTorch peak allocated during text inference across both source subsets; excludes other processes"})
    columns = "run_id,date,commit,task_id,dataset,split,model,checkpoint_sha256,precision,metric,value,ci95_low,ci95_high,n,chance_level,hardware,notes".split(",")
    dest = ROOT / "metrics" / f"{config['run_id']}-{split}.csv"
    dest.parent.mkdir(exist_ok=True)
    pd.DataFrame(result).reindex(columns=columns).to_csv(dest, index=False)
    dump(out / "evaluation_info.json", {"gallery": gallery_stats, "config": config, "split_sha256": lock["manifest_sha256"], "test_evaluated": split == "test"})
    print(pd.DataFrame(result)[["dataset", "metric", "value", "n"]].to_string(index=False), flush=True)
    print(f"CSV: {dest}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "encode", "evaluate"])
    parser.add_argument("--config", default="configs/LG02-mclip.json")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = parser.parse_args()
    config = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    if args.stage == "prepare": prepare(config)
    elif args.stage == "encode": encode(config, args.split, args.device)
    else: evaluate(config, args.split)


if __name__ == "__main__": main()
