from pathlib import Path
import csv


import numpy as np
# Compatibility patch for motmetrics + NumPy >= 2.0
if not hasattr(np, "asfarray"):
    np.asfarray = lambda a, dtype=float: np.asarray(a, dtype=dtype)

import motmetrics as mm

ROOT = Path(__file__).resolve().parents[1]

GT_DIR = (
    ROOT
    / "data/visdrone/VisDrone2019-MOT-val/annotations"
)

PRED_DIR = (
    ROOT
    / "predictions/VT05-bytetrack-20261007"
)

OUTPUT_CSV = (
    ROOT
    / "metrics/VT05-tracking-20261007.csv"
)

OUTPUT_CSV.parent.mkdir(
    parents=True,
    exist_ok=True
)


def iou_matrix(gt_boxes, pred_boxes, max_iou_distance=0.5):
    """
    motmetrics expects distance = 1 - IoU.
    Pairs with IoU < 0.5 are invalid.
    """

    if len(gt_boxes) == 0 or len(pred_boxes) == 0:
        return np.empty(
            (len(gt_boxes), len(pred_boxes))
        )

    gt = np.asarray(gt_boxes, dtype=float)
    pred = np.asarray(pred_boxes, dtype=float)

    dist = mm.distances.iou_matrix(
        gt,
        pred,
        max_iou=max_iou_distance
    )

    return dist


def load_gt(path):
    """
    VisDrone MOT format:
    frame,id,x,y,w,h,score,category,truncation,occlusion

    Only category 1 = pedestrian is evaluated.
    """

    frames = {}

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")

            if len(parts) < 10:
                continue

            frame = int(parts[0])
            track_id = int(parts[1])

            x = float(parts[2])
            y = float(parts[3])
            w = float(parts[4])
            h = float(parts[5])

            category = int(parts[7])

            # Person-only policy
            if category != 1:
                continue

            frames.setdefault(frame, []).append(
                (
                    track_id,
                    [x, y, w, h]
                )
            )

    return frames


def load_predictions(path):
    """
    Prediction MOT format:
    frame,id,x,y,w,h,conf,-1,-1,-1
    """

    frames = {}

    if not path.exists():
        return frames

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = line.split(",")

            if len(parts) < 7:
                continue

            frame = int(parts[0])
            track_id = int(parts[1])

            x = float(parts[2])
            y = float(parts[3])
            w = float(parts[4])
            h = float(parts[5])

            frames.setdefault(frame, []).append(
                (
                    track_id,
                    [x, y, w, h]
                )
            )

    return frames


def evaluate_sequence(sequence_name):

    gt_path = GT_DIR / f"{sequence_name}.txt"
    pred_path = PRED_DIR / f"{sequence_name}.txt"

    gt_frames = load_gt(gt_path)
    pred_frames = load_predictions(pred_path)

    accumulator = mm.MOTAccumulator(
        auto_id=True
    )

    all_frames = sorted(
        set(gt_frames.keys())
        | set(pred_frames.keys())
    )

    gt_count = 0
    pred_count = 0

    for frame in all_frames:

        gt_items = gt_frames.get(frame, [])
        pred_items = pred_frames.get(frame, [])

        gt_ids = [
            item[0]
            for item in gt_items
        ]

        gt_boxes = [
            item[1]
            for item in gt_items
        ]

        pred_ids = [
            item[0]
            for item in pred_items
        ]

        pred_boxes = [
            item[1]
            for item in pred_items
        ]

        gt_count += len(gt_ids)
        pred_count += len(pred_ids)

        distances = iou_matrix(
            gt_boxes,
            pred_boxes,
            max_iou_distance=0.5
        )

        accumulator.update(
            gt_ids,
            pred_ids,
            distances
        )

    return accumulator, gt_count, pred_count


sequence_names = sorted([
    p.stem
    for p in GT_DIR.glob("*.txt")
])

print("Sequences:", len(sequence_names))


accumulators = []
names = []
counts = {}


for sequence_name in sequence_names:

    print("Evaluating:", sequence_name)

    acc, gt_count, pred_count = evaluate_sequence(
        sequence_name
    )

    accumulators.append(acc)
    names.append(sequence_name)

    counts[sequence_name] = {
        "gt_count": gt_count,
        "pred_count": pred_count,
    }


mh = mm.metrics.create()

metrics = [
    "idf1",
    "idp",
    "idr",
    "num_switches",
    "mota",
    "precision",
    "recall",
    "num_objects",
    "num_predictions",
]

summary = mh.compute_many(
    accumulators,
    names=names,
    metrics=metrics,
    generate_overall=True
)


rows = []

for name in summary.index:

    row = {
        "sequence": name,
        "idf1": float(summary.loc[name, "idf1"]),
        "idp": float(summary.loc[name, "idp"]),
        "idr": float(summary.loc[name, "idr"]),
        "id_switches": int(
            summary.loc[name, "num_switches"]
        ),
        "mota": float(
            summary.loc[name, "mota"]
        ),
        "precision": float(
            summary.loc[name, "precision"]
        ),
        "recall": float(
            summary.loc[name, "recall"]
        ),
        "num_objects": int(
            summary.loc[name, "num_objects"]
        ),
        "num_predictions": int(
            summary.loc[name, "num_predictions"]
        ),
    }

    rows.append(row)


with OUTPUT_CSV.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "sequence",
            "idf1",
            "idp",
            "idr",
            "id_switches",
            "mota",
            "precision",
            "recall",
            "num_objects",
            "num_predictions",
        ]
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print("===== TRACKING SUMMARY =====")
print(summary)

print()
print("Saved:")
print(OUTPUT_CSV)
