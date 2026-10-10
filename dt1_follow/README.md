# ĐT1: Drone Tự Động Bám Theo Người Trên PX4

- **Thành viên phụ trách:** Nguyễn Quốc Việt (TV1)
- **Mã bàn giao:** M11 (Hoàn thành đợt test chính 04/10 - 11/10/2026)
- **Môi trường:** Ubuntu 24.04 LTS (WSL2), Python 3.10.22, PyTorch 2.6.0+cu124, Ultralytics 8.4.174, GPU NVIDIA RTX 3050 Laptop.

## 1. Cấu trúc thư mục bàn giao
- `configs/vt09_config.yaml`: Cấu hình cố định Detector, Tracker và Offboard SITL.
- `metrics/VT09-summary-m11-20261011.csv`: Bảng tổng hợp số liệu chuẩn 17 cột (AP, IDF1, MOTA, Heartbeat).
- `crosscheck/dt3_luong/`: Kết quả và biên bản kiểm tra chéo rút gọn của ĐT3 (Lương).
- `reports/VT09-report-m11-20261011.md`: Báo cáo nghiệm thu kỹ thuật M11.
- `predictions/VT08-eval-freeze-20261010/`: Dự đoán thô lưu trữ cho người kiểm tra chéo (Vinh ĐT2).

## 2. Hướng dẫn chạy lại đánh giá (Reproducibility)
1. Kích hoạt môi trường:
   ```bash
   conda activate dt1
   ```
2. Kiểm tra trọng số chuẩn:
   ```bash
   sha256sum -c weights/SHA256SUMS
   # Hash yolo11s.pt: 85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5
   ```
3. Chạy kiểm tra chéo kết quả ĐT3:
   ```bash
   python3 src/vt09_crosscheck_dt3.py
   ```
