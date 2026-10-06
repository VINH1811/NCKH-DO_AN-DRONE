# M3 - Detector + Crop Package

**Đề tài:** ĐT1 - Drone tự động bám theo người trên PX4  
**Task:** VT-04  
**Ngày:** 06/10/2026  
**Người thực hiện:** Nguyễn Quốc Việt  

---

## 1. Mục đích

Gói M3 cung cấp module phát hiện người bằng YOLO11s và crop từng người ra ảnh riêng để các thành viên khác có thể dùng trực tiếp trong các bước tiếp theo như:

- ByteTrack.
- Theo dõi danh tính người.
- Matching / Re-identification.
- Tích hợp pipeline bám người.
- Tích hợp ROS 2 / PX4 ở các bước sau.

Pipeline của gói:

```text
Ảnh đầu vào
    ↓
YOLO11s
    ↓
Phát hiện person
    ↓
Bounding box
    ↓
Crop person
    ↓
Ảnh crop + metadata.json
```

---

## 2. Detector sử dụng

Model:

```text
YOLO11s
```

Weight:

```text
yolo11s.pt
```

SHA256:

```text
85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5
```

Detector được lựa chọn từ kết quả VT-03 trên `VisDrone2019-DET-val`.

Một số kết quả chính:

```text
AP            : 0.1001
AP50          : 0.2354
AP75          : 0.0721
AP small      : 0.0653
Latency p50   : 25.37 ms
Latency p95   : 45.55 ms
Peak VRAM     : 93.97 MB
```

---

## 3. Cấu trúc thư mục

```text
M3-detector-crop-20261006/
├── README.md
├── requirements.txt
├── configs/
│   └── vt04_detector.yaml
├── src/
│   ├── detector.py
│   ├── crop_person.py
│   └── run_detector_crop.py
└── checkpoints/
    └── SHA256SUMS
```

Weight `yolo11s.pt` không bắt buộc lưu trực tiếp trong Git repository.

Khi chạy, cần đặt weight tại:

```text
weights/detectors/yolo11s.pt
```

hoặc điều chỉnh lại đường dẫn `weights` trong file config.

---

## 4. Yêu cầu môi trường

Khuyến nghị:

```text
Python      : 3.10
PyTorch     : 2.11.0
CUDA        : 12.8
Ultralytics : 8.4.172
```

Cài dependency:

```bash
pip install -r requirements.txt
```

Nếu môi trường đã được tạo trước đó:

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dt1
```

---

## 5. Cấu hình detector

File:

```text
configs/vt04_detector.yaml
```

Cấu hình hiện tại:

```yaml
detector:
  name: yolo11s
  framework: ultralytics
  weights: weights/detectors/yolo11s.pt

target:
  class_name: person
  class_id: 0

inference:
  imgsz: 640
  conf: 0.25
  iou: 0.7
  device: 0

crop:
  enabled: true
  padding_ratio: 0.10
  min_width: 10
  min_height: 20
```

---

## 6. Cách chạy nhanh

### 6.1. Chạy với một ảnh

Từ thư mục `dt1_follow`:

```bash
python src/run_detector_crop.py \
  --source <duong_dan_anh> \
  --output predictions/VT04-detector-crop
```

Ví dụ:

```bash
python src/run_detector_crop.py \
  --source data/visdrone/VisDrone2019-DET-val/images/0000001_02999_d_0000005.jpg \
  --output predictions/VT04-detector-crop
```

### 6.2. Chạy với một thư mục ảnh

```bash
python src/run_detector_crop.py \
  --source <duong_dan_thu_muc_anh> \
  --output predictions/VT04-detector-crop
```

---

## 7. Kết quả đầu ra

Với mỗi ảnh đầu vào, script tạo một thư mục riêng.

Ví dụ:

```text
predictions/VT04-detector-crop/
└── 0000001_02999_d_0000005/
    ├── metadata.json
    ├── person_001.jpg
    ├── person_002.jpg
    └── person_003.jpg
```

Trong lần test VT-04:

```text
detections=3
saved_crops=3
```

Các crop tạo được:

```text
person_001.jpg : 20x50
person_002.jpg : 25x66
person_003.jpg : 18x41
```

---

## 8. Metadata

Mỗi ảnh đầu vào có một file:

```text
metadata.json
```

Metadata chứa:

- Tên ảnh đầu vào.
- Tên file crop.
- Confidence.
- Class ID.
- Class name.
- Bounding box.
- Bounding box sau khi thêm padding.
- Kích thước crop.

---

## 9. Sử dụng trực tiếp trong Python

Detector:

```python
from src.detector import PersonDetector

detector = PersonDetector()
detections = detector.detect(image)
```

Cropper:

```python
from src.crop_person import PersonCropper

cropper = PersonCropper()

crop_img, crop_info = cropper.crop(
    image,
    detection["bbox_xyxy"]
)
```

---

## 10. Kiểm tra weight

Sau khi nhận file `yolo11s.pt`, kiểm tra:

```bash
sha256sum weights/detectors/yolo11s.pt
```

SHA256 đúng:

```text
85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5
```

---

## 11. Ghi chú khi tích hợp

- Detector hiện chỉ lấy class `person`.
- Output bbox dùng format `[x1, y1, x2, y2]`.
- Ảnh dùng trong code là BGR của OpenCV.
- Crop có padding 10%.
- Có thể thay đổi `conf`, `iou`, `imgsz` trong `configs/vt04_detector.yaml`.
- Khi tích hợp ByteTrack, nên dùng trực tiếp bbox + confidence từ `PersonDetector`.
- Không cần chạy crop nếu module sau chỉ cần bbox để tracking.

---

## 12. Kết quả VT-04 / M3

```text
YOLO11s detector : PASS
Person detection : PASS
Person crop      : PASS
Metadata output  : PASS
Single image run : PASS
```

Gói M3 đã sẵn sàng để dùng cho các bước tiếp theo của ĐT1.
