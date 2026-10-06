from pathlib import Path

import cv2
import yaml


class PersonCropper:
    def __init__(self, config_path="configs/vt04_detector.yaml"):
        self.root = Path(__file__).resolve().parents[1]

        config_path = self.root / config_path

        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        crop_cfg = config["crop"]

        self.padding_ratio = float(crop_cfg["padding_ratio"])
        self.min_width = int(crop_cfg["min_width"])
        self.min_height = int(crop_cfg["min_height"])

    def crop(self, image, bbox_xyxy):
        """
        Crop one person from image using bbox [x1, y1, x2, y2].

        Returns:
            crop_image, crop_info

        crop_info contains:
            original_bbox
            padded_bbox
            width
            height
        """

        height, width = image.shape[:2]

        x1, y1, x2, y2 = bbox_xyxy

        box_w = x2 - x1
        box_h = y2 - y1

        if box_w < self.min_width or box_h < self.min_height:
            return None, None

        pad_x = box_w * self.padding_ratio
        pad_y = box_h * self.padding_ratio

        px1 = max(0, int(x1 - pad_x))
        py1 = max(0, int(y1 - pad_y))

        px2 = min(width, int(x2 + pad_x))
        py2 = min(height, int(y2 + pad_y))

        if px2 <= px1 or py2 <= py1:
            return None, None

        crop_img = image[py1:py2, px1:px2].copy()

        crop_info = {
            "original_bbox": [
                float(x1),
                float(y1),
                float(x2),
                float(y2),
            ],
            "padded_bbox": [
                px1,
                py1,
                px2,
                py2,
            ],
            "width": px2 - px1,
            "height": py2 - py1,
        }

        return crop_img, crop_info


if __name__ == "__main__":
    from detector import PersonDetector

    root = Path(__file__).resolve().parents[1]

    test_image = (
        root
        / "data/visdrone/VisDrone2019-DET-val/images/"
          "0000001_02999_d_0000005.jpg"
    )

    output_dir = root / "predictions/VT04-crop-test"
    output_dir.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(test_image))

    if image is None:
        raise FileNotFoundError(test_image)

    detector = PersonDetector()
    cropper = PersonCropper()

    detections = detector.detect(image)

    print("Detections:", len(detections))

    saved = 0

    for i, det in enumerate(detections, start=1):
        crop_img, crop_info = cropper.crop(
            image,
            det["bbox_xyxy"]
        )

        if crop_img is None:
            continue

        output_file = output_dir / f"person_{i:03d}.jpg"

        cv2.imwrite(
            str(output_file),
            crop_img
        )

        saved += 1

        print(
            f"{output_file.name}: "
            f"{crop_info['width']}x{crop_info['height']} "
            f"conf={det['confidence']:.4f}"
        )

    print("Saved crops:", saved)
    print("Output dir:", output_dir)
