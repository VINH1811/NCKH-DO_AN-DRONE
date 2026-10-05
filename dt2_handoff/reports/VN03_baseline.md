# VN-03 — Baseline OSNet trên AG-ReID.v2

Ngày 04/10/2026 · Vinh (TV2) · `run_id` **VN03-ain-20261004**, **VN03-msmt17-20261004**

Bốn protocol chính thức của tác giả, không chỉnh sửa. Mỗi con số kèm **n**,
**mức ngẫu nhiên** và **khoảng tin cậy 95%** bootstrap 1.000 lần lấy mẫu lại
theo query, đúng quy ước thống nhất ở C-03.

## Kết quả

Rank-1 (%), khoảng tin cậy 95% trong ngoặc vuông:

| Chiều | n query | OSNet-AIN đa nguồn | OSNet MSMT17 | Ngẫu nhiên |
|---|---:|---|---|---:|
| UAV → CCTV | 2.356 | **33,62** [31,79–35,61] | 9,55 [8,45–10,78] | 0,170 |
| CCTV → UAV | 1.811 | **27,89** [25,73–30,09] | 9,00 [7,68–10,33] | 0,110 |
| UAV → kính đeo | 2.209 | **26,53** [24,72–28,48] | 8,78 [7,70–9,91] | 0,190 |
| kính đeo → UAV | 2.340 | **20,13** [18,46–21,67] | 8,72 [7,61–9,87] | 0,145 |

mAP (%):

| Chiều | OSNet-AIN đa nguồn | OSNet MSMT17 | Ngẫu nhiên |
|---|---|---|---:|
| UAV → CCTV | **22,22** [21,08–23,29] | 5,62 [5,07–6,18] | 0,308 |
| CCTV → UAV | **19,44** [18,18–20,70] | 5,05 [4,40–5,67] | 0,238 |
| UAV → kính đeo | **15,64** [14,73–16,55] | 4,66 [4,20–5,15] | 0,243 |
| kính đeo → UAV | **13,42** [12,48–14,28] | 4,43 [3,97–4,91] | 0,254 |

## Ba điều rút ra

**1. Huấn luyện khái quát miền quan trọng hơn hẳn quy mô dữ liệu nguồn.**

OSNet-AIN đa nguồn hơn OSNet MSMT17 **2,3 đến 3,5 lần** ở cả bốn chiều. Hai mô
hình cùng kiến trúc, cùng cỡ, chỉ khác cách huấn luyện.

**So sánh cặp trên cùng truy vấn** (quy ước C-03, mục 4.2 README gốc) — hiệu
Rank-1 theo từng truy vấn, bootstrap 1.000 lần:

| Chiều | Hiệu Rank-1 | Khoảng tin cậy 95% | AIN thắng ở |
|---|---:|---|---:|
| UAV → CCTV | +24,07 | [+22,28 – +25,89] | 87,0% truy vấn |
| CCTV → UAV | +18,88 | [+16,84 – +20,98] | — |
| UAV → kính đeo | +17,75 | [+15,80 – +19,69] | — |
| kính đeo → UAV | +11,41 | [+9,87 – +12,99] | — |

Cả tám phép so (bốn chiều × Rank-1 và mAP) đều có khoảng tin cậy của hiệu **không
chứa 0**, nên khác biệt có ý nghĩa ở mọi chiều. Với bài toán mặt đất ↔ trên cao,
cơ chế khái quát miền đóng góp lớn hơn nhiều so với tăng dữ liệu cùng miền.

> Ở lần nộp đầu tôi lập luận bằng "hai khoảng tin cậy không chồng nhau". Cách đó
> đúng nhưng yếu hơn; quy ước C-03 chốt dùng so sánh cặp. Ở đây hai cách cho cùng
> kết luận vì chênh lệch quá lớn, nhưng khi so hai cấu hình sát nhau thì chúng sẽ
> khác nhau — số liệu chuẩn nằm ở `metrics/ket_qua_chuan.csv`.

**2. CCTV bắt cặp với UAV tốt hơn kính đeo, ở cả hai chiều.**

UAV→CCTV đạt 33,62% còn UAV→kính đeo chỉ 26,53%; chiều ngược lại là 27,89% so
với 20,13%. Giải thích hợp lý nhất là hình học: CCTV treo ~3 m, kính đeo ở ~1,5 m,
nên góc nhìn CCTV gần với UAV (15–45 m) hơn. Khoảng cách độ cao càng lớn thì
biến dạng dáng người càng mạnh.

> Liên quan trực tiếp tới ĐT2: **camera mặt đất nên treo cao nhất có thể** trong
> giới hạn cho phép. Đây là một căn cứ đo được cho việc chọn vị trí lắp camera ở
> phần thu pilot.

**3. Trên cao → mặt đất dễ hơn mặt đất → trên cao.**

Cả hai cặp đều lệch cùng chiều (33,62 so với 27,89; 26,53 so với 20,13). Trong
kịch bản bàn giao của ĐT2, hướng thực tế là **mặt đất → trên cao** — tức là
hướng khó hơn. Con số cần dùng để đặt kỳ vọng là **27,89%** (CCTV→UAV), không
phải con số đẹp hơn ở chiều ngược lại.

## Tốc độ

RTX 3060 Laptop 6 GB, fp32, batch 64, đo 3 vòng sau khi làm nóng:

| | p50 | p95 |
|---|---|---|
| Riêng mô hình | 1,16 ms/ảnh | 1,17 ms/ảnh |
| Cả pipeline (đọc ảnh + biến đổi + suy luận) | 1,90 ms/ảnh | — |

Ba vòng lệch nhau dưới 1%. Đọc và biến đổi ảnh chiếm khoảng 39% thời gian — nếu
cần tăng tốc thì tối ưu chỗ đó trước, không phải tối ưu mô hình.

## Mốc dưới để đối chiếu

Chạy cùng đường ống với trọng số **ImageNet** (chưa huấn luyện ReID) trên
UAV→CCTV cho Rank-1 **6,41%**, mAP **2,90%**. So với 33,62% của AIN đa nguồn,
huấn luyện ReID đóng góp hơn 5 lần. Con số này xác nhận đường ống đánh giá chạy
đúng chứ không phải ăn may.

## Tái lập

```bash
P=D:/Data/AG-ReID.v2
python dt2_handoff/src/eval_agreid.py --goc $P/AG-ReID.v2 \
  --protocol $P/exp1_aerial_to_cctv.txt --protocol $P/exp2_aerial_to_wearable.txt \
  --protocol $P/exp4_cctv_to_aerial.txt --protocol $P/exp5_wearable_to_aerial.txt \
  --model osnet_ain_x1_0 --ckpt models/osnet_ain_x1_0_dangguon_msdc.pth \
  --ra <thư-mục-ra>
```

| | |
|---|---|
| Checkpoint AIN | SHA256 `2f38acc25e28cb29…` — xem `checkpoints/SHA256SUMS` |
| Checkpoint MSMT17 | SHA256 `b7d73dc67c016fd0…` |
| Môi trường | `env/VN02-setup-20261004/` |
| Config từng lần chạy | `configs/VN03-*.json` |
| Dự đoán thô | `predictions/VN03-*/` — tính lại metric không cần GPU |
| Số liệu theo mẫu chung | `metrics/ket_qua_chuan.csv` — 24 dòng, gồm cả so sánh cặp |

Ngưỡng và lựa chọn mô hình **chưa** đụng tới tập test nào của pilot; đây là chạy
trực tiếp trọng số công bố trên benchmark gốc, giữ nguyên protocol của tác giả.

## Việc tiếp theo

- **VN-04** (06/10): phân tích lỗi theo góc nhìn. Dữ liệu đã có sẵn trong
  `predictions/` — tách theo trường `A` (độ cao 0/1/2) trong tên ảnh để xem sai
  số tăng thế nào theo độ cao bay.
- Cân nhắc RemoteCLIP làm đối chứng trên cùng ảnh cắt (tuỳ chọn).
- Kết quả trên dữ liệu pilot tự thu phải **báo cáo riêng**, không gộp với bảng
  này: khác miền, khác protocol.
