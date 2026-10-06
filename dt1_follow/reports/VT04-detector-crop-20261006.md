# VT-04 - Đóng gói Detector + Crop cho ĐT1

**Ngày thực hiện:** 06/10/2026  
**Thành viên:** Nguyễn Quốc Việt  
**Đề tài:** ĐT1 - Drone tự động bám theo người trên PX4

---

## 1. Mục tiêu

VT-04 thực hiện lựa chọn cấu hình detector dựa trên kết quả VT-03 và đóng gói thành module có thể tái sử dụng.

Detector được lựa chọn:

    YOLO11s

Gói VT-04 gồm:

- Cấu hình detector.
- Module phát hiện người.
- Module crop người.
- Script chạy detector + crop bằng một lệnh.
- Metadata cho từng ảnh đầu vào.
- SHA256 của weight YOLO11s.

---

## 2. Detector được lựa chọn

Detector:

    YOLO11s

Weight:

    weights/detectors/yolo11s.pt

SHA256:

    85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5

Detector được lựa chọn dựa trên kết quả VT-03.

Các chỉ số chính:

    AP            : 0.1001
    AP50          : 0.2354
    AP75          : 0.0721
    AP small      : 0.0653
    latency p50   : 25.37 ms
    latency p95   : 45.55 ms
    peak VRAM     : 93.97 MB

YOLO11s có độ chính xác cao hơn YOLO-World trong VT-03 và sử dụng ít VRAM hơn đáng kể.

---

## 3. Cấu hình detector

File cấu hình:

    configs/vt04_detector.yaml

Thông số chính:

    model  : yolo11s
    imgsz  : 640
    conf   : 0.25
    iou    : 0.7
    device : 0

Target:

    class_name : person
    class_id   : 0

Crop:

    padding_ratio : 0.10
    min_width     : 10
    min_height    : 20

---

## 4. Module detector

File:

    src/detector.py

Chức năng:

- Load YOLO11s.
- Chỉ detect class `person`.
- Nhận ảnh BGR từ OpenCV.
- Trả về danh sách detection.

Mỗi detection có dạng:

    bbox_xyxy
    confidence
    class_id
    class_name

Test thực tế trên một ảnh VisDrone:

    Detections: 3

Ví dụ:

    bbox=[864.89, 405.89, 881.55, 447.73]
    conf=0.4166

---

## 5. Module crop

File:

    src/crop_person.py

Chức năng:

- Nhận ảnh gốc.
- Nhận bbox từ detector.
- Thêm padding.
- Giới hạn crop trong kích thước ảnh.
- Loại bbox quá nhỏ.
- Trả về ảnh crop và thông tin bbox.

Test thực tế:

    Detections: 3
    Saved crops: 3

Kích thước crop:

    person_001.jpg : 20x50
    person_002.jpg : 25x66
    person_003.jpg : 18x41

---

## 6. Script detector + crop

File:

    src/run_detector_crop.py

Script cho phép chạy detector và crop bằng một lệnh.

Ví dụ:

    python src/run_detector_crop.py \
      --source data/visdrone/VisDrone2019-DET-val/images/0000001_02999_d_0000005.jpg \
      --output predictions/VT04-package-test

Kết quả:

    detections=3
    saved_crops=3

Output:

    predictions/VT04-package-test/
    └── 0000001_02999_d_0000005/
        ├── metadata.json
        ├── person_001.jpg
        ├── person_002.jpg
        └── person_003.jpg

---

## 7. Metadata

Mỗi ảnh đầu vào có file:

    metadata.json

Metadata chứa:

- Tên ảnh đầu vào.
- Tên file crop.
- Confidence.
- Class ID.
- Class name.
- Bounding box.
- Bounding box sau khi thêm padding.
- Kích thước crop.

Metadata có thể được sử dụng cho các bước tracking và tích hợp pipeline sau này.

---

## 8. Cấu trúc gói VT-04

Các file chính:

    configs/vt04_detector.yaml

    src/detector.py
    src/crop_person.py
    src/run_detector_crop.py

    reports/VT04-detector-crop-20261006.md

Weight:

    weights/detectors/yolo11s.pt

SHA256:

    85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5

---

## 9. Cách chạy lại

Kích hoạt môi trường:

    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate dt1

Đi vào thư mục:

    cd /mnt/f/DoAnTotNghiep/source/NCKH-DO_AN-DRONE/dt1_follow

Chạy một ảnh:

    python src/run_detector_crop.py \
      --source <duong_dan_anh> \
      --output predictions/VT04-detector-crop

Chạy cả thư mục ảnh:

    python src/run_detector_crop.py \
      --source <duong_dan_thu_muc_anh> \
      --output predictions/VT04-detector-crop

---

## 10. Đầu ra VT-04

Đầu ra yêu cầu:

    Gói detector/crop (M3)

Kết quả:

    YOLO11s detector : PASS
    Person detection : PASS
    Person crop      : PASS
    Metadata output  : PASS
    Single-image run : PASS

Gói hiện tại đã sẵn sàng để giao cho các thành viên khác sử dụng.

---

## 11. Kết luận

VT-04 đã hoàn thành việc lựa chọn cấu hình detector từ kết quả VT-03 và đóng gói YOLO11s thành module detector + crop.

Gói này có thể được dùng làm đầu vào cho các bước tiếp theo như:

- ByteTrack.
- Theo dõi danh tính người.
- Trích xuất crop phục vụ matching.
- Tích hợp pipeline điều khiển drone bám người.
