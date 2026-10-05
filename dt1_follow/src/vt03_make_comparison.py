from pathlib import Path
import json
import csv


ROOT = Path(__file__).resolve().parents[1]

AP_FILE = ROOT / "metrics/VT03-ap-summary.json"
BENCH_FILE = ROOT / "metrics/VT03-benchmark-summary.json"

OUT_FILE = ROOT / "metrics/VT03-detector-comparison-20261005.csv"


def main():
    with AP_FILE.open("r", encoding="utf-8") as f:
        ap_results = json.load(f)

    with BENCH_FILE.open("r", encoding="utf-8") as f:
        benchmark_results = json.load(f)

    ap_map = {r["model"]: r for r in ap_results}
    benchmark_map = {r["model"]: r for r in benchmark_results}

    models = [
        "yolo11s",
        "yolov8s-worldv2",
    ]

    rows = []

    for model in models:
        ap = ap_map[model]
        bench = benchmark_map[model]

        rows.append({
            "model": model,
            "dataset": "VisDrone2019-DET-val",
            "target": "pedestrian",
            "images": bench["images"],

            "AP": round(ap["AP"], 4),
            "AP50": round(ap["AP50"], 4),
            "AP75": round(ap["AP75"], 4),

            "AP_small": round(ap["AP_small"], 4),
            "AP_medium": round(ap["AP_medium"], 4),
            "AP_large": round(ap["AP_large"], 4),

            "latency_p50_ms": round(bench["latency_p50_ms"], 2),
            "latency_p95_ms": round(bench["latency_p95_ms"], 2),
            "latency_mean_ms": round(bench["latency_mean_ms"], 2),

            "peak_vram_mb": round(bench["peak_vram_mb"], 2),

            "imgsz": bench["imgsz"],
            "conf": bench["conf"],
            "gpu": bench["gpu"],
        })

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Created:")
    print(OUT_FILE)
    print()

    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
