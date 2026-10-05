# VT-03 - So sánh YOLO11 và YOLO-World trên VisDrone DET-val

**Ngày thực hiện:** 05/10/2026  
**Thành viên:** Nguyễn Quốc Việt  
**Đề tài:** ĐT1 - Drone tự động bám theo người trên PX4

---

## 1. Mục tiêu

VT-03 thực hiện so sánh hai detector:

- YOLO11s
- YOLO-World v2 Small

trên tập dữ liệu `VisDrone2019-DET-val`.

Mục tiêu là đánh giá khả năng phát hiện người, tốc độ xử lý và mức sử dụng VRAM để lựa chọn detector phù hợp cho VT-04.

---

## 2. Dữ liệu đánh giá

Dataset: `VisDrone2019-DET-val`

Số lượng ảnh: **548**

Tổng số annotation: **40169**

Phân bố các class quan trọng:

    pedestrian      : 8844
    people          : 5125
    ignored_regions : 1378

Trong VT-03, đối tượng đánh giá chính:

    VisDrone category 1 = pedestrian

Quy ước:

- `pedestrian`: Ground Truth chính.
- `people`: giữ riêng, không gộp vào pedestrian.
- `ignored_regions`: vùng bỏ qua.
- Các class còn lại không thuộc phạm vi đánh giá person-only.

Ground Truth sử dụng:

    data/splits/VT03-visdrone-det-val-person.json

---

## 3. Môi trường thử nghiệm

    Python      : 3.10.22
    PyTorch     : 2.11.0+cu128
    CUDA        : 12.8
    Ultralytics : 8.4.172
    GPU         : NVIDIA GeForce RTX 3050 Laptop GPU
    VRAM GPU    : 4 GB

Model:

    YOLO11      : weights/detectors/yolo11s.pt
    YOLO-World  : weights/detectors/yolov8s-worldv2.pt

YOLO-World sử dụng prompt:

    person

Thông số inference:

    imgsz  = 640
    conf   = 0.001
    device = CUDA GPU

---

## 4. Kết quả so sánh

| Chỉ số | YOLO11s | YOLO-World v2 |
|---|---:|---:|
| AP | **0.1001** | 0.0848 |
| AP50 | **0.2354** | 0.2029 |
| AP75 | **0.0721** | 0.0576 |
| AP small | **0.0653** | 0.0521 |
| AP medium | **0.3175** | 0.2767 |
| AP large | **0.8616** | 0.8272 |
| Latency p50 | **25.37 ms** | 26.71 ms |
| Latency p95 | 45.55 ms | **43.14 ms** |
| Latency mean | 28.90 ms | **28.29 ms** |
| Peak VRAM | **93.97 MB** | 688.45 MB |
| Detections | 54296 | 62503 |

File CSV:

    metrics/VT03-detector-comparison-20261005.csv

---

## 5. Phân tích độ chính xác

YOLO11s đạt kết quả tốt hơn YOLO-World ở tất cả các chỉ số AP.

AP:

    YOLO11s      : 0.1001
    YOLO-World   : 0.0848

AP50:

    YOLO11s      : 0.2354
    YOLO-World   : 0.2029

AP75:

    YOLO11s      : 0.0721
    YOLO-World   : 0.0576

Đối với các đối tượng nhỏ:

    YOLO11s AP small      : 0.0653
    YOLO-World AP small   : 0.0521

YOLO11s có kết quả tốt hơn đối với người có kích thước nhỏ. Đây là yếu tố quan trọng đối với VisDrone vì người trong ảnh drone thường có kích thước nhỏ.

---

## 6. Phân tích tốc độ

Latency p50:

    YOLO11s      : 25.37 ms
    YOLO-World   : 26.71 ms

Latency p95:

    YOLO11s      : 45.55 ms
    YOLO-World   : 43.14 ms

Latency trung bình:

    YOLO11s      : 28.90 ms
    YOLO-World   : 28.29 ms

Hai model có tốc độ khá tương đương.

YOLO11s tốt hơn một chút ở p50, trong khi YOLO-World tốt hơn một chút ở p95 và latency trung bình.

---

## 7. Phân tích VRAM

Peak VRAM:

    YOLO11s      : 93.97 MB
    YOLO-World   : 688.45 MB

YOLO-World sử dụng VRAM cao hơn đáng kể.

Việc YOLO11s sử dụng ít VRAM hơn có lợi cho hệ thống drone vì GPU còn phải xử lý các thành phần khác như:

- ByteTrack.
- Xử lý hình ảnh.
- Logic bám theo mục tiêu.
- ROS 2.
- Điều khiển PX4.

---

## 8. Lựa chọn detector

Detector được lựa chọn:

    YOLO11s

Lý do:

1. AP cao hơn YOLO-World.
2. AP50 và AP75 cao hơn.
3. AP small cao hơn.
4. Tốc độ xử lý gần tương đương.
5. Sử dụng VRAM thấp hơn đáng kể.
6. Phù hợp hơn cho hệ thống drone có tài nguyên GPU hạn chế.

---

## 9. Các file kết quả

CSV so sánh detector:

    metrics/VT03-detector-comparison-20261005.csv

Kết quả AP:

    metrics/VT03-ap-summary.json

Kết quả latency và VRAM:

    metrics/VT03-benchmark-summary.json

Prediction YOLO11s:

    predictions/VT03-20261005/yolo11s_predictions.json

Prediction YOLO-World:

    predictions/VT03-20261005/yolov8s-worldv2_predictions.json

Ground Truth person-only:

    data/splits/VT03-visdrone-det-val-person.json

---

## 10. Đầu ra VT-03

### YOLO11s

    AP            : 0.1001
    AP50          : 0.2354
    AP75          : 0.0721
    AP small      : 0.0653
    AP medium     : 0.3175
    AP large      : 0.8616
    Latency p50   : 25.37 ms
    Latency p95   : 45.55 ms
    Peak VRAM     : 93.97 MB

### YOLO-World v2

    AP            : 0.0848
    AP50          : 0.2029
    AP75          : 0.0576
    AP small      : 0.0521
    AP medium     : 0.2767
    AP large      : 0.8272
    Latency p50   : 26.71 ms
    Latency p95   : 43.14 ms
    Peak VRAM     : 688.45 MB

Detector được lựa chọn cho VT-04:

    YOLO11s

---

## 11. Kết luận

VT-03 đã hoàn thành việc so sánh YOLO11s và YOLO-World v2 trên tập VisDrone2019-DET-val cho bài toán person-only.

YOLO11s đạt độ chính xác cao hơn ở tất cả các chỉ số AP và sử dụng VRAM thấp hơn đáng kể.

Tốc độ xử lý của hai model gần tương đương.

Do đó, **YOLO11s được lựa chọn làm detector chính cho VT-04**.
## So sánh cặp theo từng ảnh

Để phục vụ công cụ đánh giá chung của nhóm, AP được tính riêng trên từng ảnh có ít nhất một pedestrian ground truth.

Số ảnh dùng để so sánh cặp:

    520

Các file AP theo từng ảnh:

    metrics/VT03-yolo11s-per-image-ap.npy
    metrics/VT03-yolov8s-worldv2-per-image-ap.npy
    metrics/VT03-paired-image-names.npy

Mean per-image AP:

    YOLO11s      : 0.150037
    YOLO-World   : 0.134274

Paired difference:

    YOLO11s - YOLO-World = 0.015763

Bootstrap 95% CI:

    0.010102 -> 0.021693

Số bootstrap sample:

    10000

Trong 10000 bootstrap sample, không có sample nào có chênh lệch <= 0.

Kết quả này cho thấy YOLO11s có mean per-image AP cao hơn YOLO-World trên tập ảnh được ghép cặp.

File kết quả paired comparison:

    metrics/VT03-paired-comparison-20261005.csv
