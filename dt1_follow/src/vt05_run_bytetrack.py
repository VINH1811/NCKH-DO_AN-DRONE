from pathlib import Path
import csv

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "weights/detectors/yolo11s.pt"

MOT_ROOT = (
    ROOT
    / "data/visdrone/VisDrone2019-MOT-val"
)

SEQUENCES_DIR = MOT_ROOT / "sequences"

TRACKER_CFG = (
    ROOT
    / "configs/vt05_bytetrack_ultralytics.yaml"
)

OUTPUT_DIR = (
    ROOT
    / "predictions/VT05-bytetrack-20261007"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


model = YOLO(str(MODEL_PATH))


sequence_dirs = sorted([
    p
    for p in SEQUENCES_DIR.iterdir()
    if p.is_dir()
])

print("Sequences:", len(sequence_dirs))


for sequence_dir in sequence_dirs:

    sequence_name = sequence_dir.name

    print()
    print("=" * 60)
    print("Sequence:", sequence_name)

    output_file = OUTPUT_DIR / f"{sequence_name}.txt"

    results = model.track(
        source=str(sequence_dir),
        tracker=str(TRACKER_CFG),
        classes=[0],
        imgsz=640,
        conf=0.10,
        iou=0.7,
        device=0,
        persist=True,
        stream=True,
        verbose=False,
    )

    rows = []

    frame_id = 0
    track_count = 0

    for result in results:

        frame_id += 1

        if (
            result.boxes is None
            or result.boxes.id is None
        ):
            continue

        boxes = (
            result.boxes.xyxy
            .cpu()
            .numpy()
        )

        ids = (
            result.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        confs = (
            result.boxes.conf
            .cpu()
            .tolist()
        )

        for box, track_id, conf in zip(
            boxes,
            ids,
            confs
        ):

            x1, y1, x2, y2 = box

            width = x2 - x1
            height = y2 - y1

            rows.append([
                frame_id,
                int(track_id),
                float(x1),
                float(y1),
                float(width),
                float(height),
                float(conf),
                -1,
                -1,
                -1,
            ])

            track_count += 1

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerows(rows)

    print("Frames:", frame_id)
    print("Track detections:", track_count)
    print("Saved:", output_file)


print()
print("DONE")
print("Output:", OUTPUT_DIR)

