from pathlib import Path

import cv2
import yaml
from ultralytics import YOLO


class PersonDetector:
    def __init__(self, config_path="configs/vt04_detector.yaml"):
        self.root = Path(__file__).resolve().parents[1]

        config_path = self.root / config_path

        with config_path.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        detector_cfg = self.config["detector"]
        inference_cfg = self.config["inference"]
        target_cfg = self.config["target"]

        self.weights_path = self.root / detector_cfg["weights"]

        self.model = YOLO(str(self.weights_path))

        self.class_id = int(target_cfg["class_id"])
        self.class_name = target_cfg["class_name"]

        self.imgsz = int(inference_cfg["imgsz"])
        self.conf = float(inference_cfg["conf"])
        self.iou = float(inference_cfg["iou"])
        self.device = inference_cfg["device"]

    def detect(self, image):
        """
        Detect person objects in a BGR image.

        Returns:
            list of dict:
            [
                {
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "confidence": float,
                    "class_id": int,
                    "class_name": str,
                }
            ]
        """

        results = self.model.predict(
            source=image,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            classes=[self.class_id],
            device=self.device,
            verbose=False,
        )

        detections = []

        if not results:
            return detections

        result = results[0]

        if result.boxes is None:
            return detections

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            confidence = float(box.conf[0])
            class_id = int(box.cls[0])

            detections.append(
                {
                    "bbox_xyxy": [
                        float(x1),
                        float(y1),
                        float(x2),
                        float(y2),
                    ],
                    "confidence": confidence,
                    "class_id": class_id,
                    "class_name": self.class_name,
                }
            )

        return detections


if __name__ == "__main__":
    detector = PersonDetector()

    test_image = (
        Path(__file__).resolve().parents[1]
        / "data/visdrone/VisDrone2019-DET-val/images/"
          "0000001_02999_d_0000005.jpg"
    )

    image = cv2.imread(str(test_image))

    if image is None:
        raise FileNotFoundError(test_image)

    detections = detector.detect(image)

    print("Image:", test_image)
    print("Detections:", len(detections))

    for i, det in enumerate(detections, start=1):
        print(
            f"{i}: "
            f"bbox={det['bbox_xyxy']} "
            f"conf={det['confidence']:.4f}"
        )
