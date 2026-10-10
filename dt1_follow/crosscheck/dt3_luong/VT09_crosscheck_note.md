# Biên bản kiểm tra chéo rút gọn kết quả ĐT3 (Lương) - Mốc M11

- **Người thực hiện kiểm tra chéo:** Việt (ĐT1)
- **Đối tượng kiểm tra:** Kết quả Text-to-Person Retrieval của Lương (ĐT3)
- **Thời điểm:** 11/10/2026
- **Phạm vi kiểm tra:** Chạy lại evaluator độc lập trên tập predictions bàn giao + Smoke test 5 mẫu ngẫu nhiên.

## 1. Kết quả chạy lại Evaluator độc lập
- **Tổng số truy vấn kiểm tra:** 50
- **Recall@1:** 0.6400 (64.00%)
- **Recall@5:** 0.9600 (96.00%)
- **Khớp với số liệu công bố:** Hợp lệ, sai khác nằm trong phương sai mẫu bootstrap cho phép.

## 2. Kết quả Smoke Test 5 mẫu ngẫu nhiên
| STT | Mã Query | Ground Truth | Dự đoán Top-1 | Kết quả |
| :---: | :---: | :---: | :---: | :---: |
| 1 | Q_43 | `person_042` | `person_041` | **HIT (Top-5)** |
| 2 | Q_35 | `person_034` | `person_029` | **HIT (Top-5)** |
| 3 | Q_01 | `person_000` | `person_000` | **HIT (Top-1)** |
| 4 | Q_13 | `person_012` | `person_012` | **HIT (Top-1)** |
| 5 | Q_12 | `person_011` | `person_021` | **HIT (Top-5)** |

## 3. Nhận xét & Đánh giá của ĐT1
- Format file predictions của ĐT3 chuẩn, cấu trúc ranking rõ ràng.
- Giao diện đầu ra ứng viên tương thích tốt với chuỗi liên kết đề tài (ĐT3 -> ĐT2 -> ĐT1).
- Xác nhận kết quả kiểm tra chéo đạt yêu cầu bàn giao.