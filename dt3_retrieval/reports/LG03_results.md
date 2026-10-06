# LG-03 — Bảng mô hình × ngôn ngữ × gõ/nói

Đã đánh giá trên cùng 76 câu dev. Tập 174 câu test chưa được mã hóa hoặc đánh giá.

M-CLIP dùng ảnh ViT-L/14 có sẵn trong M1; OpenCLIP dùng ảnh ViT-B/32 mã hóa lại.

## 9 camera cố định

| Mô hình | Truy vấn | n | R@1 | R@5 | R@10 | mAP |
|---|---|---:|---:|---:|---:|---:|
| M-CLIP | Gõ tiếng Việt | 70 | 2.86% | 14.29% | 18.57% | 8.75% |
| M-CLIP | Gõ tiếng Anh đã rà soát | 70 | 5.71% | 14.29% | 21.43% | 10.13% |
| M-CLIP | Nói — ASR Whisper | 70 | 0.00% | 7.14% | 11.43% | 4.55% |
| M-CLIP | Nói — ASR PhoWhisper | 70 | 2.86% | 17.14% | 25.71% | 10.46% |
| OpenCLIP | Gõ tiếng Việt | 70 | 7.14% | 24.29% | 28.57% | 14.04% |
| OpenCLIP | Gõ tiếng Anh đã rà soát | 70 | 4.29% | 18.57% | 30.00% | 12.19% |
| OpenCLIP | Nói — ASR Whisper | 70 | 2.86% | 7.14% | 18.57% | 6.52% |
| OpenCLIP | Nói — ASR PhoWhisper | 70 | 5.71% | 17.14% | 22.86% | 12.00% |

## Video điện thoại

| Mô hình | Truy vấn | n | R@1 | R@5 | R@10 | mAP |
|---|---|---:|---:|---:|---:|---:|
| M-CLIP | Gõ tiếng Việt | 6 | 0.00% | 16.67% | 16.67% | 10.61% |
| M-CLIP | Gõ tiếng Anh đã rà soát | 6 | 16.67% | 33.33% | 50.00% | 28.02% |
| M-CLIP | Nói — ASR Whisper | 6 | 0.00% | 16.67% | 16.67% | 8.73% |
| M-CLIP | Nói — ASR PhoWhisper | 6 | 0.00% | 16.67% | 16.67% | 8.99% |
| OpenCLIP | Gõ tiếng Việt | 6 | 0.00% | 16.67% | 33.33% | 6.82% |
| OpenCLIP | Gõ tiếng Anh đã rà soát | 6 | 0.00% | 0.00% | 16.67% | 4.39% |
| OpenCLIP | Nói — ASR Whisper | 6 | 0.00% | 16.67% | 16.67% | 4.16% |
| OpenCLIP | Nói — ASR PhoWhisper | 6 | 0.00% | 33.33% | 33.33% | 13.31% |

## Cách diễn giải

- CI, latency và chênh lệch cặp đầy đủ nằm trong workbook và CSV.
- CI metric chứa chance: chưa đủ bằng chứng theo CI đã chọn; CI chênh lệch chứa 0: chưa đủ bằng chứng phân biệt hai cấu hình theo CI đó.
- Bản dịch được Codex rà soát; cần người trong nhóm xác nhận nếu yêu cầu human-reviewed.
- Nói ở đây là bản chép ASR tiếng Việt, chưa có ô nói tiếng Anh. Latency không gồm chạy ASR.
- Hai hệ khác backbone ảnh và precision ảnh; đây là so hệ retrieval, không cô lập ảnh hưởng của text encoder.
- Xem [protocol LG-03](LG03_protocol.md) và [bản từng chỉ số xuống dòng](LG03_comparison_readable.txt).
