from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]

model_path = ROOT / "weights/detectors/yolo11s.pt"

sequence = (
    ROOT
    / "data/visdrone/VisDrone2019-MOT-val/sequences/uav0000086_00000_v"
)

tracker_cfg = ROOT / "configs/vt05_bytetrack_ultralytics.yaml"

model = YOLO(str(model_path))

results = model.track(
    source=str(sequence),
    tracker=str(tracker_cfg),
    classes=[0],
    imgsz=640,
    conf=0.10,
    iou=0.7,
    device=0,
    persist=True,
    stream=True,
    verbose=False,
)

frame_count = 0
track_detections = 0
unique_ids = set()

for result in results:
    frame_count += 1

    if result.boxes is None or result.boxes.id is None:
        continue

    ids = result.boxes.id.int().cpu().tolist()

    track_detections += len(ids)
    unique_ids.update(ids)

    if frame_count <= 5:
        print(
            f"frame={frame_count}, "
            f"tracks={len(ids)}, "
            f"ids={ids}"
        )

print()
print("Frames:", frame_count)
print("Track detections:", track_detections)
print("Unique track IDs:", len(unique_ids))
print("First IDs:", sorted(unique_ids)[:20])
