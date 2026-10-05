from pathlib import Path
import csv
import json


ROOT = Path(__file__).resolve().parents[1]

AP_FILE = ROOT / "metrics/VT03-ap-summary.json"
BENCH_FILE = ROOT / "metrics/VT03-benchmark-summary.json"
BOOT_FILE = ROOT / "metrics/VT03-paired-bootstrap.json"

OUT_FILE = ROOT / "metrics/VT03-detector-comparison-20261005.csv"


RUN_IDS = {
    "yolo11s": "VT03-yolo11s-visdrone-20261005",
    "yolov8s-worldv2": "VT03-yoloworld-visdrone-20261005",
}


def main():
    with AP_FILE.open("r", encoding="utf-8") as f:
        ap_results = json.load(f)

    with BENCH_FILE.open("r", encoding="utf-8") as f:
        bench_results = json.load(f)

    with BOOT_FILE.open("r", encoding="utf-8") as f:
        boot = json.load(f)

    ap_map = {x["model"]: x for x in ap_results}
    bench_map = {x["model"]: x for x in bench_results}

    rows = []

    for model in ["yolo11s", "yolov8s-worldv2"]:
        ap = ap_map[model]
        bench = bench_map[model]
        boot_model = boot[model]

        base = {
            "run_id": RUN_IDS[model],
            "model": model,
            "dataset": "VisDrone2019-DET-val",
            "target": "pedestrian",
            "n_images": 548,
            "paired_n_images": 520,
            "imgsz": bench["imgsz"],
            "conf": bench["conf"],
            "gpu": bench["gpu"],
        }

        # Dataset-level COCO metrics
        metric_values = {
            "AP": ap["AP"],
            "AP50": ap["AP50"],
            "AP75": ap["AP75"],
            "AP_small": ap["AP_small"],
            "AP_medium": ap["AP_medium"],
            "AP_large": ap["AP_large"],
            "latency_p50_ms": bench["latency_p50_ms"],
            "latency_p95_ms": bench["latency_p95_ms"],
            "latency_mean_ms": bench["latency_mean_ms"],
            "peak_vram_mb": bench["peak_vram_mb"],
        }

        for metric, value in metric_values.items():
            row = dict(base)
            row.update({
                "metric": metric,
                "value": value,
                "ci95_low": "",
                "ci95_high": "",
                "chance_level": 0.0 if metric.startswith("AP") else "",
            })
            rows.append(row)

        # Mean per-image AP with bootstrap CI
        row = dict(base)
        row.update({
            "metric": "mean_per_image_AP",
            "value": boot_model["mean_per_image_ap"],
            "ci95_low": boot_model["ci95_low"],
            "ci95_high": boot_model["ci95_high"],
            "chance_level": boot_model["chance_level"],
        })
        rows.append(row)

    fieldnames = [
        "run_id",
        "model",
        "dataset",
        "target",
        "metric",
        "value",
        "ci95_low",
        "ci95_high",
        "chance_level",
        "n_images",
        "paired_n_images",
        "imgsz",
        "conf",
        "gpu",
    ]

    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Created:")
    print(OUT_FILE)
    print()
    print("Rows:", len(rows))


if __name__ == "__main__":
    main()
