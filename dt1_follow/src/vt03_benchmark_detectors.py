from pathlib import Path
import json
import time
import statistics

import torch
from ultralytics import YOLO, YOLOWorld


ROOT = Path(__file__).resolve().parents[1]

IMAGE_DIR = ROOT / "data/visdrone/VisDrone2019-DET-val/images"
PRED_DIR = ROOT / "predictions/VT03-20261005"
METRIC_DIR = ROOT / "metrics"

IMG_SIZE = 640
CONF = 0.001
DEVICE = 0


def percentile(values, p):
    if not values:
        return 0.0

    values = sorted(values)
    k = (len(values) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(values) - 1)

    if f == c:
        return values[f]

    return values[f] + (values[c] - values[f]) * (k - f)


def run_model(name, model, images, class_filter=None):
    print()
    print("=" * 60)
    print("MODEL:", name)
    print("=" * 60)

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    # Warm-up
    print("Warm-up...")
    for img in images[:10]:
        model.predict(
            source=str(img),
            imgsz=IMG_SIZE,
            conf=CONF,
            classes=class_filter,
            device=DEVICE,
            verbose=False,
        )

    torch.cuda.synchronize()

    predictions = []
    latencies = []

    print("Benchmarking", len(images), "images...")

    for i, img in enumerate(images, start=1):
        torch.cuda.synchronize()
        start = time.perf_counter()

        result = model.predict(
            source=str(img),
            imgsz=IMG_SIZE,
            conf=CONF,
            classes=class_filter,
            device=DEVICE,
            verbose=False,
        )[0]

        torch.cuda.synchronize()
        elapsed_ms = (time.perf_counter() - start) * 1000

        latencies.append(elapsed_ms)

        boxes = result.boxes

        if boxes is not None:
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1

                predictions.append({
                    "image_name": img.name,
                    "bbox": [x1, y1, w, h],
                    "score": conf,
                    "class_id": cls,
                })

        if i % 50 == 0 or i == len(images):
            print(f"{i}/{len(images)}")

    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)

    result_summary = {
        "model": name,
        "images": len(images),
        "detections": len(predictions),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "latency_mean_ms": statistics.mean(latencies),
        "peak_vram_mb": peak_vram_mb,
        "imgsz": IMG_SIZE,
        "conf": CONF,
        "gpu": torch.cuda.get_device_name(0),
    }

    return predictions, result_summary


def main():
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    METRIC_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in IMAGE_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    print("Images:", len(images))
    print("GPU:", torch.cuda.get_device_name(0))
    print("Image size:", IMG_SIZE)
    print("Confidence threshold:", CONF)

    # YOLO11
    yolo11 = YOLO(ROOT / "weights/detectors/yolo11s.pt")

    pred11, summary11 = run_model(
        "yolo11s",
        yolo11,
        images,
        class_filter=[0],
    )

    with (PRED_DIR / "yolo11s_predictions.json").open("w") as f:
        json.dump(pred11, f)

    del yolo11
    torch.cuda.empty_cache()

    # YOLO-World
    world = YOLOWorld(ROOT / "weights/detectors/yolov8s-worldv2.pt")
    world.set_classes(["person"])

    pred_world, summary_world = run_model(
        "yolov8s-worldv2",
        world,
        images,
        class_filter=None,
    )

    with (PRED_DIR / "yolov8s-worldv2_predictions.json").open("w") as f:
        json.dump(pred_world, f)

    summaries = [summary11, summary_world]

    with (METRIC_DIR / "VT03-benchmark-summary.json").open("w") as f:
        json.dump(summaries, f, indent=2)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for s in summaries:
        print()
        print("Model:", s["model"])
        print("Images:", s["images"])
        print("Detections:", s["detections"])
        print("Latency p50:", round(s["latency_p50_ms"], 2), "ms")
        print("Latency p95:", round(s["latency_p95_ms"], 2), "ms")
        print("Latency mean:", round(s["latency_mean_ms"], 2), "ms")
        print("Peak VRAM:", round(s["peak_vram_mb"], 2), "MB")


if __name__ == "__main__":
    main()
