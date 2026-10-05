from pathlib import Path
import json

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


ROOT = Path(__file__).resolve().parents[1]

GT_FILE = ROOT / "data/splits/VT03-visdrone-det-val-person.json"
PRED_DIR = ROOT / "predictions/VT03-20261005"
OUT_FILE = ROOT / "metrics/VT03-ap-summary.json"


def load_image_map(coco_gt):
    return {
        img["file_name"]: img["id"]
        for img in coco_gt.dataset["images"]
    }


def convert_predictions(pred_file, image_map):
    with pred_file.open("r") as f:
        preds = json.load(f)

    coco_preds = []

    for p in preds:
        image_name = p["image_name"]

        if image_name not in image_map:
            continue

        coco_preds.append({
            "image_id": image_map[image_name],
            "category_id": 1,
            "bbox": p["bbox"],
            "score": p["score"],
        })

    return coco_preds


def evaluate_model(model_name, pred_file):
    print()
    print("=" * 60)
    print("Evaluating:", model_name)
    print("=" * 60)

    coco_gt = COCO(str(GT_FILE))
    image_map = load_image_map(coco_gt)

    coco_preds = convert_predictions(pred_file, image_map)

    if not coco_preds:
        raise RuntimeError(f"No predictions found for {model_name}")

    coco_dt = coco_gt.loadRes(coco_preds)

    evaluator = COCOeval(coco_gt, coco_dt, "bbox")
    evaluator.params.catIds = [1]
    evaluator.evaluate()
    evaluator.accumulate()
    evaluator.summarize()

    stats = evaluator.stats

    return {
        "model": model_name,
        "AP": float(stats[0]),
        "AP50": float(stats[1]),
        "AP75": float(stats[2]),
        "AP_small": float(stats[3]),
        "AP_medium": float(stats[4]),
        "AP_large": float(stats[5]),
        "AR_1": float(stats[6]),
        "AR_10": float(stats[7]),
        "AR_100": float(stats[8]),
        "AR_small": float(stats[9]),
        "AR_medium": float(stats[10]),
        "AR_large": float(stats[11]),
    }


def main():
    results = []

    results.append(
        evaluate_model(
            "yolo11s",
            PRED_DIR / "yolo11s_predictions.json",
        )
    )

    results.append(
        evaluate_model(
            "yolov8s-worldv2",
            PRED_DIR / "yolov8s-worldv2_predictions.json",
        )
    )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 60)
    print("AP SUMMARY")
    print("=" * 60)

    for r in results:
        print()
        print("Model:", r["model"])
        print("AP:", round(r["AP"], 4))
        print("AP50:", round(r["AP50"], 4))
        print("AP75:", round(r["AP75"], 4))
        print("AP small:", round(r["AP_small"], 4))
        print("AP medium:", round(r["AP_medium"], 4))
        print("AP large:", round(r["AP_large"], 4))


if __name__ == "__main__":
    main()
