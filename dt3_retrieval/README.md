# ĐT3 — LG-02: baseline M-CLIP trên gói SecondPaper M1

Đã chạy baseline **dev** ngày 05/10/2026. Đầu ra chính:

- `metrics/LG02_baseline_summary.csv`: bảng rộng, metric tìm kiếm tính theo phần trăm.
- `metrics/LG02-mclip-secondpaper-20261005-dev.csv`: CSV dài theo mẫu nhóm; metric tìm kiếm dùng thang 0–1, latency dùng ms.
- `data/splits/LG02_split_manifest.csv`: đủ 250 truy vấn, khóa split theo camera và track.
- `data/splits/LG02_split_lock.json`: SHA256 dữ liệu, cấu hình và manifest.
- `predictions/LG02-mclip-secondpaper-20261005/dev/`: embedding câu, rank đích, top-10 track, mẫu latency và thông tin mô hình.
- `reports/LG02_baseline.md`: protocol, kết quả và giới hạn.

## Dữ liệu và checkpoint

Gói gốc: `C:\Users\acer\Downloads\SecondPaper_M1.tar`.
Các manifest, embedding và cơ sở dữ liệu đã được giải nén vào `data/SecondPaper_M1`.
Ảnh/audio vẫn nằm trong TAR; LG-02 dùng embedding ảnh đã có nên không cần giải nén chúng.
SHA256 của metadata và embedding đã được kiểm tra với `SHA256SUMS.txt` trong gói.

**Không dùng checkpoint M-CLIP ViT-B/32 đã thử ngày 04/10:** nó cho vector 512 chiều.
Gói M1 dùng embedding ảnh `open_clip ViT-L-14, pretrained=openai`, 768 chiều.
Checkpoint văn bản tương ứng là `M-CLIP/XLM-Roberta-Large-Vit-L-14`, revision
`40afa80a85e8efa990384a24bbe5a1f6f1cc81b5`.
SHA256 trọng số: `0ad09a3a1ccf35d93c95c08686506fc59c966d77ac1f5833413366c4d327cb2d`.
Model card: https://huggingface.co/M-CLIP/XLM-Roberta-Large-Vit-L-14

## Split và protocol

| Nguồn | Gallery | Truy vấn dev | Truy vấn test |
|---|---|---:|---:|
| `edata` | 9 camera, 23.436 keyframe, 4.272 track | 70 | 158 |
| `video` | 8 video điện thoại, 71.214 keyframe, 32.404 track | 6 | 16 |

Tổng: 76 dev, 174 test; không trùng camera hoặc track giữa **các nhóm truy vấn**.
Danh sách camera dev được chọn trước khi đánh giá, lưu trong config.
Đây là split theo camera có bảo đảm nhóm track; không phải lấy ngẫu nhiên từng câu/frame.
`seed` dùng cho bootstrap; danh sách camera cố định không được sinh ngẫu nhiên từ seed.

Theo thông tin người phụ trách, camera được thu vào ngày/thời điểm khác nhau và không có liên kết danh tính.
Do đó dùng `track_id` làm danh tính cục bộ trong dataset. Gói không có ánh xạ `person_id`;
không thể khẳng định tuyệt đối rằng một người thật không xuất hiện ở nhiều track/camera.

Gallery cố định được dùng chung cho truy vấn dev/test, phân tách theo nguồn.
Không dùng nhãn test để chọn cấu hình; **chưa encode hoặc đánh giá truy vấn test**.
Không gộp điện thoại/drone vào baseline 9 camera.
Giữ toàn bộ keyframe trong manifest chính thức, kể cả mục có cờ deleted trong DB.
Điều này là protocol snapshot M1, không phải một filter suy đoán từ paper cũ.

Điểm track = cosine cao nhất trong các keyframe của track đó.
Sắp xếp điểm giảm dần, track_id tăng dần nếu bằng điểm.
Mỗi câu chỉ có một track được gán nhãn relevant:
Recall@k = tỷ lệ câu có track đích trong top-k; AP = 1/rank đích; mAP bằng MRR trong thiết lập này.
Không coi các frame của cùng track là những ứng viên độc lập.
Chưa có evaluator/mã nguồn paper gốc để xác nhận protocol này hoàn toàn trùng bài báo.

## Chạy lại trên máy hiện tại — PowerShell

Đứng trong `dt3_retrieval`; dùng môi trường `dt3_py310`.

```powershell
$env:HF_HOME = Join-Path (Get-Location).Path 'checkpoints\hf_cache'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'

conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_baseline.py prepare
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_baseline.py encode --split dev --device cuda
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_baseline.py evaluate --split dev
```

`prepare` từ chối ghi đè một split khác. Các bước sau kiểm tra hash split/config.
Không sửa split sau khi đã xem test. Trước khi dùng test cần chốt config cuối, lưu config/hash mới riêng,
và giữ nguyên assignment của manifest hiện tại.

Chạy lại evaluator từ predictions đã lưu (không nạp mô hình/GPU):

```powershell
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_baseline.py evaluate --split dev
```

Kiểm tra cách đếm track, ties, relevant bị thiếu và bootstrap theo nhóm:

```powershell
conda run --no-capture-output -n dt3_py310 python -m unittest discover -s src -p test_secondpaper_baseline.py -v
```

## Thống kê và tốc độ

CI 95%: 1.000 bootstrap, resample theo track đích để các câu của cùng track đi cùng nhau.
Đây là CI có điều kiện trên camera đã chọn, không phải CI khái quát hóa qua camera.
Mức ngẫu nhiên với N track và một relevant: Recall@k = min(k,N)/N; mAP = H_N/N.

FP32, batch 1, RTX 3050 Laptop GPU, CUDA runtime 12.4, Torch 2.6.0+cu124.
Warm-up 5 truy vấn mỗi nguồn; đo mọi truy vấn 3 lần, đồng bộ CUDA khi tính thời gian.
Model latency gồm tokenizer, text encoder và chuẩn hóa.
Pipeline latency gồm thêm copy GPU→CPU, exact cosine, max theo track và xếp hạng;
gallery đã nạp sẵn. Không gồm đọc video, detector/crop, nhúng ảnh, tải model hoặc IO.
Chưa xác minh lịch GPU riêng; các số tốc độ hiện là đo trên máy trong phiên này.

Môi trường tại `env/LG02-mclip-secondpaper-20261005/`.
Do các file chưa commit, hash Git là commit nền, không đủ tái lập mã mới.
`measured_implementation.py` lưu đúng phiên bản dùng đo inference/latency, đối chiếu hash trong model_info.
Script hiện tại bổ sung kiểm tra config; không thay đổi công thức inference hoặc xếp hạng.

## Checklist LG-02

- [x] Kiểm tra toàn vẹn metadata và embedding M1
- [x] Nạp đúng checkpoint M-CLIP 768 chiều và lưu hash/revision
- [x] Khóa assignment 250 truy vấn; không trùng camera/track giữa dev/test
- [x] Baseline dev theo track, Recall@1/5/10, mAP, n, chance level, CI 95%
- [x] Latency p50/p95, 3 lần đo sau warm-up; lưu mẫu thô
- [x] Predictions và môi trường đã lưu
- [x] Bốn kiểm thử tính toán metric đã đạt
- [ ] Xác minh protocol với evaluator paper gốc
- [ ] Xác minh danh tính thật qua track/camera (không có person_id)
- [ ] Đo tốc độ trong lịch GPU riêng được nhóm xác nhận
- [ ] Commit mã/config/split/kết quả và ghi link vào bảng tiến độ
- [ ] Test cố định ngày 10/10; giữ lại 174 truy vấn hiện chưa đánh giá
