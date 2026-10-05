from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]

BOOT_FILE = ROOT / "metrics/VT03-paired-bootstrap.json"
OUT_FILE = ROOT / "metrics/VT03-paired-comparison-20261005.csv"


def main():
    with BOOT_FILE.open("r", encoding="utf-8") as f:
        boot = json.load(f)

    paired = boot["paired_comparison"]

    row = {
        "run_id": "VT03-paired-visdrone-20261005",
        "comparison": "yolo11s_minus_yolov8s-worldv2",
        "dataset": "VisDrone2019-DET-val",
        "target": "pedestrian",
        "metric": paired["metric"],
        "value": paired["difference_yolo11_minus_world"],
        "ci95_low": paired["ci95_low"],
        "ci95_high": paired["ci95_high"],
        "chance_level": 0.0,
        "n_images": boot["n_images"],
        "bootstrap_samples": boot["n_bootstrap"],
        "bootstrap_prob_difference_le_0": paired[
            "bootstrap_prob_difference_le_0"
        ],
    }

    fieldnames = list(row.keys())

    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    print("Created:")
    print(OUT_FILE)


if __name__ == "__main__":
    main()
