from pathlib import Path
import json
import cv2


ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = ROOT / "data/visdrone/VisDrone2019-DET-val"
IMAGE_DIR = DATASET_DIR / "images"
ANNOTATION_DIR = DATASET_DIR / "annotations"

OUTPUT_FILE = ROOT / "data/splits/VT03-visdrone-det-val-person.json"


def main():
    coco = {
        "info": {
            "description": "VT-03 VisDrone2019 DET-val person-only evaluation",
            "target": "pedestrian",
            "visdrone_category_id": 1,
        },
        "images": [],
        "annotations": [],
        "categories": [
            {
                "id": 1,
                "name": "person",
            }
        ],
    }

    annotation_id = 1

    pedestrian_count = 0
    people_ignore_count = 0
    region_ignore_count = 0

    image_files = sorted(IMAGE_DIR.glob("*"))

    for image_id, image_path in enumerate(image_files, start=1):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            print(f"WARNING: cannot read {image_path}")
            continue

        height, width = image.shape[:2]

        coco["images"].append(
            {
                "id": image_id,
                "file_name": image_path.name,
                "width": width,
                "height": height,
            }
        )

        annotation_path = ANNOTATION_DIR / f"{image_path.stem}.txt"

        if not annotation_path.exists():
            continue

        with annotation_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                values = line.split(",")

                if len(values) < 8:
                    continue

                x = float(values[0])
                y = float(values[1])
                w = float(values[2])
                h = float(values[3])

                score = int(values[4])
                category_id = int(values[5])

                # Invalid / zero-area box
                if w <= 0 or h <= 0:
                    continue

                # -------------------------------------------------
                # VisDrone category 1: pedestrian
                # Actual person GT used for evaluation
                # -------------------------------------------------
                if category_id == 1 and score == 1:
                    coco["annotations"].append(
                        {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": 1,
                            "bbox": [x, y, w, h],
                            "area": w * h,
                            "iscrowd": 0,
                            "ignore": 0,
                        }
                    )

                    annotation_id += 1
                    pedestrian_count += 1

                # -------------------------------------------------
                # VisDrone category 0: ignored region
                #
                # VisDrone category 2: people/group
                #
                # For VT-03 person-only evaluation these regions
                # are kept as ignored/crowd GT so person detections
                # inside them are not treated as normal pedestrian GT.
                # -------------------------------------------------
                elif category_id in (0, 2):
                    coco["annotations"].append(
                        {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": 1,
                            "bbox": [x, y, w, h],
                            "area": w * h,
                            "iscrowd": 1,
                            "ignore": 1,
                        }
                    )

                    annotation_id += 1

                    if category_id == 0:
                        region_ignore_count += 1
                    else:
                        people_ignore_count += 1

                # Other VisDrone categories are outside
                # the person-only evaluation.
                else:
                    continue

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(coco, f, ensure_ascii=False)

    print()
    print("===== VT-03 PERSON GT =====")
    print("Images:", len(coco["images"]))
    print("Pedestrian GT:", pedestrian_count)
    print("People ignore:", people_ignore_count)
    print("Ignored regions:", region_ignore_count)
    print("COCO annotations:", len(coco["annotations"]))
    print()
    print("Output:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
