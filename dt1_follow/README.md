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

## Quy ước lưu trữ

- `data/splits/`: chỉ commit manifest mô tả các split; không commit dữ liệu gốc.
- `checkpoints/SHA256SUMS`: lưu hash SHA-256 của các tệp trọng số; không commit trọng số.
- `metrics/`: lưu kết quả CSV theo mẫu chung, sẽ bổ sung khi mẫu được xác định.
