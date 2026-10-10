# Báo cáo nghiệm thu VT-08: Đóng băng đánh giá (Evaluation Freeze) & Bàn giao mốc M10

- **Mã việc:** VT-08
- **Đề tài:** ĐT1 – Drone tự động bám theo người trên PX4
- **Người thực hiện:** Việt (TV1)
- **Ngày thực hiện:** 10/10/2026
- **Run ID môi trường:** `VT08-eval-freeze-20261010`
- **Môi trường thực thi:** Ubuntu 24.04 LTS (WSL2), Python 3.10.22, PyTorch 2.6.0+cu124, NVIDIA RTX 3050 Laptop GPU

---

## 1. Mục tiêu công việc

Theo phân công tiến độ chung của nhóm (Mốc M10):

> *"Đánh giá detector trên split chưa dùng để chỉnh (nếu có GT); chạy lại kịch bản tracking/SITL đã chốt; xuất bảng, video, log; lưu predictions cho kiểm tra chéo"* — Đầu ra: **Predictions + metrics + video (M10)**.

---

## 2. Danh mục sản phẩm bàn giao kiểm tra chéo (Cross-check Artifacts)

### 2.1. Dự đoán thô (Raw Predictions) cho ĐT2 (Vinh) kiểm tra chéo

- **Tệp lưu trữ:** `predictions/VT08-eval-freeze-20261010/uav0000086_00000_v.txt`
- **Định dạng:** Chuẩn VisDrone/MOT (`frame, id, bb_left, bb_top, bb_width, bb_height, conf, x, y, z`).
- **Mục đích:** Vinh (người kiểm tra chéo ĐT1) có thể chạy trực tiếp bộ evaluator tính lại toàn bộ chỉ số MOTA/IDF1 mà không cần nạp lại model hay yêu cầu GPU.

### 2.2. Video kết xuất kiểm thử (Tracking Demo)

- **Tệp video:** `reports/videos/VT08_tracking_demo.mp4`
- **Thông số kỹ thuật:** MP4 (1280x720, 20 FPS, 60 frames demo).
- **Mô tả hành vi:** Trực quan hóa quá trình Visual Servoing, tâm camera căn chỉnh theo BBox của Target ID 1 kèm trạng thái duy trì nhịp Heartbeat Offboard 20 Hz.

### 2.3. Bảng kết quả chuẩn 17 cột (`metrics/VT08-freeze-metrics-20261010.csv`)

Tệp CSV đã được định dạng đúng 17 trường quy chuẩn chung của đề tài để tích hợp vào `docs/metrics_tong_hop.csv`:

| Run ID | Dataset / Task | Model | Metric | Giá trị | 95% CI | n | Ghi chú |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `VT08-eval-freeze-20261010` | VisDrone2019-MOT (val) | YOLO11s + ByteTrack | **IDF1** | 0.2699 | [0.2410, 0.2985] | 2746 | Chốt mốc M10; baseline freeze toàn bộ 7 sequence |
| `VT08-eval-freeze-20261010` | VisDrone2019-MOT (val) | YOLO11s + ByteTrack | **MOTA** | 0.1078 | [0.0820, 0.1340] | 2746 | Chốt mốc M10; 213 ID switches |
| `VT08-eval-freeze-20261010` | PX4-SITL-X500 (sim) | VisualServoing_20Hz | **Offboard_Heartbeat_Hz** | 20.0 | — | 100 | Heartbeat tách luồng, timeout 1.0s chuyển Failsafe Hold OK |

---

## 3. Khóa cấu hình & Checkpoint (Mốc M10)

- **Detector:** YOLO11s (`weights/detectors/yolo11s.pt`)
- **Mã hash SHA-256 trọng số:**
  ```text
  85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5
  ```
- **Cấu hình Tracker ByteTrack:**
  - `track_high_thresh`: 0.25
  - `track_low_thresh`: 0.10
  - `new_track_thresh`: 0.25
  - `track_buffer`: 30
  - `match_thresh`: 0.80

---

## 4. Kế hoạch tiếp theo (M11 - 11/10/2026)

1. Bàn giao gói artifacts M10 cho Vinh (ĐT2) tiến hành kiểm tra chéo rút gọn.
2. Nhận kết quả từ Lương (ĐT3) để thực hiện kiểm tra chéo ngược lại theo phân công.
3. Hoàn thiện báo cáo tổng hợp M11 đóng đợt test chung.
