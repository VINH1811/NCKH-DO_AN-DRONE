# LG-03 — so mô hình × ngôn ngữ × gõ/nói trên dev

Ngày thực hiện: 06/10/2026. Giữ split LG-02: 76 dev, 174 test.
Giữ nguyên gallery theo nguồn: 9 camera `edata` và 8 video điện thoại báo cáo riêng.
Không xem hoặc mã hóa truy vấn test. Ảnh trong gallery được mã hóa không dùng nhãn truy vấn test.

## Các cấu hình

Hai hệ mô hình:

- M-CLIP: bộ mã hóa chữ `M-CLIP/XLM-Roberta-Large-Vit-L-14`, 768 chiều,
  ghép embedding ảnh ViT-L/14 OpenAI có trong M1.
- OpenCLIP đa ngôn ngữ: `xlm-roberta-base-ViT-B-32`, `laion5b_s13b_b90k`, 512 chiều,
  mã hóa lại toàn bộ 94.650 ảnh của `edata` và `video` bằng bộ mã hóa ảnh tương ứng.

Mỗi hệ nhận 4 loại truy vấn:

1. Gõ, tiếng Việt: `text_vi` nguyên gốc.
2. Gõ, tiếng Anh: bản dịch dev được Codex rà soát và sửa theo tiếng Việt, trước khi xem kết quả LG-03.
3. Nói, tiếng Việt: `asr_whisper` nguyên gốc trong M1.
4. Nói, tiếng Việt: `asr_phowhisper` nguyên gốc trong M1, là đối chứng ASR riêng.

Có 8 cấu hình × 2 nguồn = 16 dòng bảng tổng hợp. Không có dòng “nói tiếng Anh” vì gói không có ASR tiếng Anh;
không dựng ô đó bằng cách thay transcript nói bằng câu gõ.

## Rà soát bản dịch

`configs/LG03_translation_review.csv` có đúng 76 câu dev: tiếng Việt, tiếng Anh gốc,
tiếng Anh đã rà soát, trạng thái, người rà soát và ghi chú.
42 câu được chuẩn hóa cách diễn đạt, 32 câu sửa nghĩa, 2 câu giữ lại mơ hồ xanh=blue/green.
Không sửa `annotations_250.csv`. Không sửa tiếng Việt hoặc ASR để cải thiện điểm.

Ví dụ lỗi được sửa:

- Áo hồng + ô vàng không phải “pink umbrella”.
- Tóc đen không phải màu da “black girl/boy”.
- Áo đen + quần trắng không phải “black and white pants”.
- Áo phao trong 2 câu dev là puffer jacket, không phải life vest; đã xem crop đích tương ứng.
- Áo dài được giữ là ao dai; có xem crop đích để kiểm tra.

Đây là rà soát của Codex, **chưa có xác nhận của người trong nhóm**.
Chỉ 3 crop đích được kiểm tra để giải nghĩa từ vựng; không khẳng định đã kiểm tra ảnh của toàn bộ 76 câu.
Không dùng điểm truy hồi để chọn cách dịch.

## Truy vấn nói

76 file ghi âm dev đã kiểm tra SHA256 từ M1, khớp cột `audio`.
Dùng bản chép ASR đi kèm file trong manifest, không chạy lại recognizer.
Gói không đủ thông tin để xác minh chính xác checkpoint/decoding config của các recognizer gốc.
Mọi lỗi nhận dạng được giữ nguyên nhằm đo ảnh hưởng của ASR lên retrieval.

Latency nói ở đây chỉ đo **transcript → text embedding → tìm kiếm**, không gồm audio decoding hoặc inference ASR.
Không gọi đây là tốc độ đầu-cuối từ micro đến kết quả.

## Protocol so sánh

- Cùng query IDs, nhãn, gallery và số track theo từng nguồn cho mọi cấu hình.
- Join embedding theo kf_id, không dựa vào thứ tự CSV.
- Điểm track = max cosine giữa câu và các keyframe của track.
- Mỗi câu có một track gán nhãn relevant; Recall@k theo track, mAP=MRR trong thiết lập này.
- CI 95% bootstrap theo track đích, 1.000 lần, seed 20261005.
- So sánh cặp dùng cùng truy vấn/track; CI của chênh lệch so với 0, không suy từ việc hai CI riêng chồng lấp.
- Nếu CI metric chứa chance, ghi rõ chưa đủ bằng chứng theo CI đã chọn; xem quy ước LG-02.
- Các contrast là thăm dò trên dev, không phải khẳng định có ý nghĩa thống kê sau đa kiểm định.
- `n=6` video có độ bất định rất lớn; bootstrap có thể suy biến khi không có lần trúng.

## Precision, tốc độ và khả năng tái lập

Text inference FP32 cho cả hai hệ, batch 1.
OpenCLIP mã hóa ảnh theo batch 64 với autocast FP16, chuẩn hóa và lưu vector FP32.
M-CLIP dùng vector FP32 được cung cấp; precision khi sinh ảnh gốc chưa xác minh.
Vì backbone ảnh L/14 và B/32 khác nhau và precision ảnh khác nguồn, so sánh là giữa **hai hệ retrieval**,
không cô lập tác động riêng của bộ mã hóa chữ. Chênh lệch nhỏ cần kiểm tra lại precision đồng nhất trước khi kết luận.

OpenCLIP tokenizer context 77 token; kiểm tra cả 4 loại truy vấn dev, dài nhất 40 token, không có câu bị cắt.
Model p50/p95 bao gồm tokenizer và mã hóa chữ; pipeline thêm transfer và tìm kiếm với gallery đã có sẵn.
Warm-up 5 lần mỗi nguồn/cấu hình, 3 lần đo mỗi query; GPU đồng bộ khi tính thời gian.
Lịch GPU riêng chưa được xác minh. Khi cần benchmark chính thức, đo lại trong khung nhóm chốt.

Index có checkpoint tiến độ, có thể tiếp tục nếu bị ngắt. Chỉ dùng index khi toàn bộ rows đã hoàn thành.
Hash config, split, bản dịch, checkpoint, image/query embedding được lưu để đối chiếu.
CSV chuẩn vẫn giữ 17 cột; model/language/input/ASR ghi trong notes, bảng rộng có cột riêng.

Nguồn mô hình:

- https://huggingface.co/M-CLIP/XLM-Roberta-Large-Vit-L-14
- https://huggingface.co/laion/CLIP-ViT-B-32-xlm-roberta-base-laion5B-s13B-b90k

## Lệnh chạy — PowerShell, trong dt3_retrieval

```powershell
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_comparison.py index
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_comparison.py run
conda run --no-capture-output -n dt3_py310 python -X utf8 src/secondpaper_comparison.py evaluate
```

Máy hiện tại có crop và checkpoint đã tải. Script dùng cache offline.
`evaluate` tính lại bảng từ query/image embeddings đã lưu, không cần inference GPU.
Không thay config hoặc bản dịch khi đang chạy; khi sửa phải tạo run mới và mã hóa lại truy vấn tương ứng.

Đầu ra:

- `metrics/LG03_model_language_input.csv`: bảng mô hình × ngôn ngữ × gõ/nói.
- `metrics/LG03_model_language_input.xlsx`: bản Excel, tách nguồn và có sheet CI/so sánh cặp/bản dịch.
- `metrics/LG03_metrics_17_columns.csv`: CSV chuẩn nhóm.
- `metrics/LG03_paired_model_comparison.csv`: chênh lệch cặp giữa mô hình và giữa các loại truy vấn.
- `reports/LG03_comparison_readable.txt`: từng chỉ số xuống dòng.
- `predictions/LG03-model-language-input-20261006/`: queries, embedding, per-query metrics, top-10 track, latency và provenance.
- `reports/LG03_input_audit.json`: audio, transcript và tokenizer audit.

Kiểm tra kết quả: 8 unit tests đạt; đối chiếu độc lập thứ hạng của đủ 608 lượt query × cấu hình;
M-CLIP tiếng Việt gõ giữ nguyên thứ hạng LG-02; CSV chuẩn có 128 dòng dữ liệu và đúng 17 cột.
Split không đổi, query test chưa được mã hóa.

Workbook và Markdown được render từ CSV bằng `src/render_LG03_report.py`.
Script trình bày cần `openpyxl`; đã dùng Python base trên máy hiện tại (môi trường inference dt3_py310 không có openpyxl).
