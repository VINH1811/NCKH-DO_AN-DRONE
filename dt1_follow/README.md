# dt1_follow

## Cấu trúc và vai trò

```text
dt1_follow/
├── README.md                 # Lệnh chạy cụ thể của đề tài
├── requirements.txt          # Các thư viện cần cài đặt
├── configs/                  # Mỗi thí nghiệm một file config
├── src/                      # Mã nguồn của đề tài
├── data/splits/              # Chỉ commit split manifest, không commit dữ liệu
├── checkpoints/SHA256SUMS    # Chỉ commit hash, không commit trọng số
├── env/<run_id>/             # Thông tin môi trường từng lần chạy
├── predictions/<run_id>/     # Dự đoán thô của từng lần chạy
├── metrics/                  # CSV theo mẫu chung
└── reports/                  # Báo cáo ngắn, hình và phân tích lỗi
```

`<run_id>` là mã định danh của từng lần chạy, không phải tên thư mục cố định.
Dùng cùng một `run_id` cho thông tin môi trường và dự đoán của cùng lần chạy.

## Lệnh chạy

Sẽ bổ sung lệnh cài đặt và chạy cụ thể khi có mã nguồn và cấu hình thí nghiệm.

## Công việc ngày 04/10/2026

- VT-01: thiết lập Ultralytics (YOLO11/YOLO-World), tải VisDrone DET/MOT và chốt class mapping.
- VT-02: thiết lập PX4 SITL + Gazebo, chạy ví dụ Offboard và lưu log.

Tiến độ và nguồn tài liệu: [báo cáo thiết lập](reports/20261004-setup.md).
Mapping đề xuất: [class_mapping.json](configs/class_mapping.json).

Đã cài distro WSL `Ubuntu-24.04`. Mở từ PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Sau khi thiết lập tài khoản, mở thư mục repo trong môi trường Ubuntu 24.04:

```bash
cd /mnt/f/DoAnTotNghiep/source/NCKH-DO_AN-DRONE
```

## Quy ước lưu trữ

- `data/splits/`: chỉ commit manifest mô tả các split; không commit dữ liệu gốc.
- `checkpoints/SHA256SUMS`: lưu hash SHA-256 của các tệp trọng số; không commit trọng số.
- `metrics/`: lưu kết quả CSV theo mẫu chung, sẽ bổ sung khi mẫu được xác định.
