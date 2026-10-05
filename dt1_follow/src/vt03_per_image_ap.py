from pathlib import Path
import contextlib
import io
import json

import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


ROOT = Path(__file__).resolve().parents[1]

GT_FILE = ROOT / "data/splits/VT03-visdrone-det-val-person.json"
PRED_DIR = ROOT / "predictions/VT03-20261005"
OUT_DIR = ROOT / "metrics"

MODELS = {
    "yolo11s": PRED_DIR / "yolo11s_predictions.json",
    "yolov8s-worldv2": PRED_DIR / "yolov8s-worldv2_predictions.json",
}


def load_predictions(pred_file, name_to_id):
    with pred_file.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    result = {}

    for pred in raw:
        image_name = pred["image_name"]

        if image_name not in name_to_id:
            continue

        image_id = name_to_id[image_name]

        result.setdefault(image_id, []).append({
            "image_id": image_id,
            "category_id": 1,
            "bbox": pred["bbox"],
            "score": pred["score"],
        })

    return result


def has_positive_gt(coco_gt, image_id):
    ann_ids = coco_gt.getAnnIds(
        imgIds=[image_id],
        catIds=[1]
    )

    anns = coco_gt.loadAnns(ann_ids)

    for ann in anns:
        # pedestrian GT thật
        if (
            ann.get("iscrowd", 0) == 0
            and ann.get("ignore", 0) == 0
        ):
            return True

    return False


def evaluate_single_image(coco_gt, image_id, detections):
    # Ảnh có pedestrian GT nhưng model không detect gì
    # => AP của ảnh này = 0
    if not detections:
        return 0.0

    # Ẩn log dài của COCOeval
    with contextlib.redirect_stdout(io.StringIO()):
        coco_dt = coco_gt.loadRes(detections)

        evaluator = COCOeval(
            coco_gt,
            coco_dt,
            "bbox"
        )

        evaluator.params.imgIds = [image_id]
        evaluator.params.catIds = [1]

        evaluator.evaluate()
        evaluator.accumulate()

    # precision shape:
    # [IoU, Recall, Category, Area, MaxDets]
    precision = evaluator.eval["precision"]

    # area = all
    # maxDets = 100
    p = precision[:, :, 0, 0, 2]

    valid = p[p > -1]

    if valid.size == 0:
        return 0.0

    return float(valid.mean())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    coco_gt = COCO(str(GT_FILE))

    images = coco_gt.dataset["images"]

    name_to_id = {
        img["file_name"]: img["id"]
        for img in images
    }

    # Chỉ lấy ảnh có pedestrian GT.
    # Đây sẽ là cùng một subset cho cả 2 model,
    # nên có thể paired comparison theo từng ảnh.
    paired_images = [
        img
        for img in images
        if has_positive_gt(coco_gt, img["id"])
    ]

    print("All DET-val images:", len(images))
    print(
        "Images with pedestrian GT:",
        len(paired_images)
    )

    image_names = np.asarray(
        [img["file_name"] for img in paired_images]
    )

    np.save(
        OUT_DIR / "VT03-paired-image-names.npy",
        image_names
    )

    for model_name, pred_file in MODELS.items():
        print()
        print("=" * 60)
        print("MODEL:", model_name)
        print("=" * 60)

        pred_by_image = load_predictions(
            pred_file,
            name_to_id
        )

        scores = []

        for idx, img in enumerate(
            paired_images,
            start=1
        ):
            image_id = img["id"]

            detections = pred_by_image.get(
                image_id,
                []
            )

            ap = evaluate_single_image(
                coco_gt,
                image_id,
                detections
            )

            scores.append(ap)

            if idx % 50 == 0 or idx == len(paired_images):
                print(
                    f"{idx}/{len(paired_images)}"
                )

        scores = np.asarray(
            scores,
            dtype=np.float32
        )

        output = (
            OUT_DIR
            / f"VT03-{model_name}-per-image-ap.npy"
        )

        np.save(output, scores)

        print()
        print("Saved:", output)
        print("Shape:", scores.shape)
        print(
            "Mean per-image AP:",
            round(float(scores.mean()), 6)
        )
        print(
            "Median per-image AP:",
            round(float(np.median(scores)), 6)
        )
        print(
            "Min:",
            round(float(scores.min()), 6)
        )
        print(
            "Max:",
            round(float(scores.max()), 6)
        )


if __name__ == "__main__":
    main()
