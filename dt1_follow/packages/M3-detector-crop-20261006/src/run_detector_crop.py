from pathlib import Path
import argparse
import json

import cv2

from detector import PersonDetector
from crop_person import PersonCropper


def process_image(image_path, output_dir, detector, cropper):
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"WARNING: cannot read {image_path}")
        return

    detections = detector.detect(image)

    image_output_dir = output_dir / image_path.stem
    image_output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "image": image_path.name,
        "detections": [],
    }

    saved = 0

    for i, det in enumerate(detections, start=1):
        crop_img, crop_info = cropper.crop(
            image,
            det["bbox_xyxy"]
        )

        if crop_img is None:
            continue

        crop_name = f"person_{i:03d}.jpg"
        crop_path = image_output_dir / crop_name

        cv2.imwrite(str(crop_path), crop_img)

        metadata["detections"].append({
            "crop_file": crop_name,
            "confidence": det["confidence"],
            "class_id": det["class_id"],
            "class_name": det["class_name"],
            "bbox_xyxy": det["bbox_xyxy"],
            "crop_info": crop_info,
        })

        saved += 1

    metadata_path = image_output_dir / "metadata.json"

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(
            metadata,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"{image_path.name}: "
        f"detections={len(detections)}, "
        f"saved_crops={saved}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run YOLO11 person detector and crop detected persons."
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Input image or directory"
    )

    parser.add_argument(
        "--output",
        default="predictions/VT04-detector-crop",
        help="Output directory"
    )

    args = parser.parse_args()

    source = Path(args.source)
    output_dir = Path(args.output)

    detector = PersonDetector()
    cropper = PersonCropper()

    if source.is_file():
        process_image(
            source,
            output_dir,
            detector,
            cropper
        )

    elif source.is_dir():
        images = sorted([
            p for p in source.iterdir()
            if p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png"
            }
        ])

        print("Images:", len(images))

        for image_path in images:
            process_image(
                image_path,
                output_dir,
                detector,
                cropper
            )

    else:
        raise FileNotFoundError(source)


if __name__ == "__main__":
    main()
