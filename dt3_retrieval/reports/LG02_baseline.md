# LG-02 — Baseline M-CLIP trên SecondPaper M1, 05/10/2026

Đã chạy bộ mã hóa văn bản M-CLIP L/14, FP32, trên GPU RTX 3050 Laptop 4 GB.
Tái sử dụng embedding ảnh 768 chiều trong gói M1. Không dùng embedding/checkpoint B/32.

## Kết quả chính: 9 camera cố định (`edata`), dev

Gallery: **23.436 keyframe → 4.272 track**, tìm trên cả 9 camera, không lọc trước theo camera của truy vấn.
70 câu dev thuộc 3 camera; 158 câu test vẫn giữ kín.

| Metric | Kết quả | CI 95% bootstrap | Mức ngẫu nhiên |
|---|---:|---:|---:|
| Recall@1 | 2,86% (2/70) | 0,00–7,35% | 0,0234% |
| Recall@5 | 14,29% (10/70) | 4,41–24,32% | 0,1170% |
| Recall@10 | 18,57% (13/70) | 8,82–29,17% | 0,2341% |
| mAP | 8,75% | 4,55–13,94% | 0,2092% |

CI resample theo track đích, 1.000 lần, seed 20261005; camera được giữ cố định.
Kết quả là baseline của snapshot M1 theo protocol bên dưới, không phải khẳng định tái lập số liệu paper cũ.

**Diễn giải Recall@1:** CI bootstrap hiện bao gồm mức ngẫu nhiên nên chưa đủ bằng chứng vượt chance theo CI này.
Cận 0 với chỉ 2 lần trúng cũng có thể phản ánh giới hạn bootstrap percentile; không có nghĩa “không thể kết luận gì”.
Đối chiếu Wilson/exact chỉ phù hợp dưới giả định truy vấn độc lập, không thay thế tự động CI theo nhóm đang dùng.
Xem [quy ước thống kê đề xuất](LG02_statistical_reporting.md) về cách diễn giải, cỡ mẫu và báo cáo đủ 250 câu sau khi khóa cấu hình.

## Latency

Warm-up 5 lần mỗi nguồn, 3 repeat × 70 query = 210 mẫu cho `edata`.

| Phạm vi | p50 | p95 |
|---|---:|---:|
| Tokenizer + text encoder + chuẩn hóa | 23,57 ms | 32,91 ms |
| Exact search + gộp track + xếp hạng | 4,54 ms | 7,21 ms |
| Pipeline online với gallery có sẵn | 28,09 ms | 38,68 ms |

Pipeline có đo trực tiếp cùng lần chạy, gồm chuyển vector GPU→CPU.
Không bao gồm detector, nhúng ảnh, đọc video hoặc tải mô hình.
VRAM model peak allocated: **2.149 MiB**; reserved **2.172 MiB**.
Lịch GPU độc lập chưa được xác minh, nên cần đo lại tốc độ nếu nhóm yêu cầu số benchmark trong khung riêng.

## Phần video điện thoại, báo cáo riêng

Gallery: 71.214 keyframe, 32.404 track, 8 video; dev chỉ có **6 câu**, test 16 câu.
Recall@1 = 0%; Recall@5 = 16,67%; Recall@10 = 16,67%; mAP = 10,61%.
Text latency p50/p95: 27,11/30,79 ms; pipeline p50/p95: 44,12/52,08 ms.
Đây là mẫu rất nhỏ: CI bootstrap khi không có lần đúng top-1 sẽ suy biến về [0,0],
không chứng minh xác suất đúng thật bằng 0. Không gộp phần này vào kết luận về 9 camera.

## Split manifest

250 câu thuộc 245 track cục bộ. Cùng track/camera được giữ nguyên về một phía.

| Nguồn | Dev | Test |
|---|---:|---:|
| 9 camera cố định | 70 | 158 |
| Video điện thoại | 6 | 16 |
| Tổng | 76 | 174 |

Assignment SHA256: `36741170d67087ac169cc5f2021edc7855aaceeb0a229ecb74d2a6493e373d2b`.
Danh sách camera dev chọn trước khi chạy; gallery nguồn được cố định dùng chung cho hai nhóm truy vấn.
Không chia ngẫu nhiên frame, không chia các câu cùng track sang hai phía.
Theo người phụ trách, camera được thu vào các ngày/thời điểm khác nhau và không có liên kết người.
`track_id` là danh tính trong phạm vi dataset; không có bảng person_id để xác minh danh tính vật lý qua track.

## Protocol và giới hạn

1. Join embedding với metadata bằng `emb_kf_id.npy`, không dùng thứ tự CSV để suy đoán.
2. Gallery chỉ dùng cùng nguồn với truy vấn; bỏ nguồn drone vì không có truy vấn gán nhãn.
3. Giữ toàn bộ mục trong manifest chính thức M1, không dùng cờ deleted từ SQLite để lọc tùy ý.
4. Chuẩn hóa vector câu; embedding ảnh được kiểm tra đã L2-normalized.
5. Track score là max cosine trong các keyframe. Xếp hạng track một lần; nếu bằng điểm, tie-break bằng track_id.
6. Relevant là track_id được gán nhãn của câu. Vì chỉ có một relevant, AP = reciprocal rank và mAP = MRR.
7. Nhãn không bao gồm tất cả người có trang phục phù hợp; người khác có thể cũng đúng về nội dung nhưng chưa được gán nhãn relevant.
8. Gói không có evaluator/bài báo gốc; chưa xác nhận cách gộp track hoặc filter này trùng protocol paper.
9. Chưa đánh giá test, chưa chọn ngưỡng từ chối, chưa dùng bản dịch/ASR để điều chỉnh baseline.

Trọng số M-CLIP L/14 đã khóa revision và SHA256 trong config/model_info.
Model chính thức tương ứng với ảnh ViT-L/14: https://huggingface.co/M-CLIP/XLM-Roberta-Large-Vit-L-14

## Đầu ra để kiểm tra chéo

- `metrics/LG02_baseline_summary.csv`: bảng dễ đọc, tỷ lệ phần trăm.
- `metrics/LG02-mclip-secondpaper-20261005-dev.csv`: format chuẩn nhóm, tỷ lệ 0–1.
- `data/splits/LG02_split_manifest.csv`, `LG02_split_lock.json`.
- `predictions/LG02-mclip-secondpaper-20261005/dev/per_query.csv`: rank đích và metric của từng câu.
- `top10_tracks.csv`, `query_embeddings.npy`, `query_ids.npy`: kết quả thô.
- `latency_samples.csv`: mẫu thô theo query/repeat.
- `model_info.json`, `evaluation_info.json`, `env/`: provenance và môi trường.

Chạy lại evaluator từ predictions không cần tải mô hình; xem lệnh trong README ĐT3.
