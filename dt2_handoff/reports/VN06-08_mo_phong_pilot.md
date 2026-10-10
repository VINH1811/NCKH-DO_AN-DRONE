# VN-06 → VN-08 — Mô phỏng pilot khi chưa thu được dữ liệu phiên mới

Ngày 10/10/2026 · Vinh (TV2) · `run_id` **VN06-mo-phong-dinh-vi-20261010**,
**VN0708-mo-phong-agreid-20261010**

> **Đây là kết quả MÔ PHỎNG.** Hai phiên pilot trong khuôn viên trường (M5, M6)
> chưa quay được. Theo phương án dự phòng ghi ở mốc M6, phần bàn giao được dựng lại
> trên **AG-ReID.v2**, phần định vị được **mô phỏng Monte Carlo** với đầu vào đo từ
> dữ liệu cũ. Không con số nào ở đây là kết quả trên dữ liệu khuôn viên trường, và
> phải được báo cáo riêng như vậy (mục 4.7 README). Khi có pilot thật, chạy lại đúng
> các script này trên dữ liệu mới.

## Tóm tắt

| | Phát hiện | Hệ quả cho pilot thật |
|---|---|---|
| CH1 | **Máy quay trôi là nguồn sai lớn nhất**: sau 2 giờ, p95 lên 1,9–3,2 m; hiệu chuẩn chỉ góp 0,1–0,2 m | Kiểm tra mốc và hiệu chuẩn lại **mỗi 30 phút**, hoặc nắn khung theo nền tĩnh |
| CH1 | Máy đặt cao chịu được sai lệch điểm chân tốt hơn hẳn (p95 0,20 m so với 0,59 m) | Thêm một căn cứ cho việc đặt máy mặt đất cao nhất có thể |
| CH2 | Ngưỡng chọn trên phiên 1 **giữ được an toàn** trên phiên 2: chấp nhận nhầm khi vắng mặt 4,8–7,6%, dưới mục tiêu 10% | Quy trình chọn ngưỡng dùng được cho pilot |
| CH2 | Giới hạn thời gian tăng bàn giao đúng **+9,07 điểm** [+7,18 – +10,95], độ chính xác khi bàn giao giữ ~83% | Luôn lọc ứng viên theo thời gian trước khi so khớp |
| CH2 | Ở mức an toàn này hệ thống **từ chối ~70%** số ca | ReID hiện tại chỉ là bước xác nhận, chưa tự quyết được |
| CH2 | Kính đeo → UAV chỉ đạt **60%** độ chính xác khi bàn giao | Không dùng camera thấp ~1,5 m làm nguồn bàn giao |

## 1. VN-06 (CH1) — Ngân sách sai số định vị

### Cách mô phỏng

Dựng lại đúng quy trình sẽ làm ngoài sân: **hiệu chuẩn homography bằng 4 điểm mốc**,
rồi **đo sai số tại các điểm không dùng để hiệu chuẩn**. 2.000 lần thử × 200 điểm
kiểm tra cho mỗi kịch bản. Script: `src/vn06_mo_phong_dinh_vi.py`.

| Đầu vào | Giá trị | Nguồn |
|---|---|---|
| Rung điểm chân giữa các khung | **0,39%** chiều cao người | **Đo được** — trung vị 4 video, ~2.500 track |
| Độ trôi máy quay | **3 px / 30 phút**, **11,6 px / 2 giờ** (khung 640 px) | **Đo được** — `SanTruong3` |
| Máy quay | 1920×1080, góc ngang 69° | Giả định |
| Sai số thước / bấm điểm | 2 cm / 1,5 px | Giả định |
| Sai lệch có hệ thống của điểm chân | 0 / 3 / 6% chiều cao người | Giả định, chạy cả ba mức |

Hai cấu hình máy: **chân máy nâng 2,5 m** (vùng 6×15 m) và **tầng cao 15 m** như
`SanTruong3` (vùng 20×24 m).

### Kết quả

Sai số định vị (mét), trung vị / p95:

| Kịch bản | Chân máy 2,5 m | Tầng cao 15 m |
|---|---|---|
| 1. Chỉ sai số hiệu chuẩn | 0,04 / 0,16 | 0,04 / 0,11 |
| 2. + rung điểm chân (đo được) | 0,05 / 0,18 | 0,04 / 0,11 |
| 3. + sai lệch điểm chân 3% | 0,17 / 0,59 | 0,07 / 0,20 |
| 4. + sai lệch điểm chân 6% | 0,32 / 1,14 | 0,11 / 0,36 |
| 5. Như 3 + máy trôi 30 phút | 0,27 / 1,02 | 0,24 / 0,54 |
| **6. Như 3 + máy trôi 2 giờ** | **0,92 / 3,23** | **0,91 / 1,92** |
| 7. Như 3, điểm ngoài vùng hiệu chuẩn | 0,35 / 1,04 | 0,13 / 0,37 |

### Đọc bảng

- **Hiệu chuẩn bằng thước gần như không phải vấn đề** — 4 cm trung vị. Rung điểm chân
  do detector cũng vậy.
- **Độ trôi máy quay là nguồn sai lớn nhất.** Sau 2 giờ, p95 lên **3,23 m** với chân
  máy thấp — lớn hơn mọi nguồn khác cộng lại. Đây là con số dựa trên độ trôi **đo
  thật** của `SanTruong3`.
- **Sai lệch có hệ thống của điểm chân** là nguồn thứ hai, và **máy thấp nhạy hơn
  hẳn**: ở mức 6%, p95 là 1,14 m với máy 2,5 m so với 0,36 m với máy 15 m.
- **Ra ngoài vùng hiệu chuẩn** làm sai số tăng gấp đôi với máy thấp.

### Việc phải làm khi quay pilot thật

1. **Chụp lại ảnh mốc mỗi 30 phút**, chồng lên ảnh đầu buổi. Lệch thì hiệu chuẩn lại
   hoặc nắn khung theo nền tĩnh (cách đã làm với `SanTruong3`).
2. **4 điểm mốc phải bao trọn vùng người đi**, không chọn 4 điểm gom ở giữa.
3. **Dùng điểm cổ chân từ pose** thay vì mép dưới khung người khi có thể — dữ liệu
   pose đã có sẵn trong `manifest_moi.db`, giảm được sai lệch có hệ thống.

## 2. VN-07 — Chọn ngưỡng trên phiên 1

### Thiết kế (chốt trước khi chạy)

| | |
|---|---|
| Dữ liệu | AG-ReID.v2, chiều chính **CCTV → UAV**, chiều phụ kính đeo → UAV |
| Phiên | Chia theo **ngày quay**: ngày sớm vào phiên 1 tới khi đủ ~50% truy vấn. Mỗi phiên dùng gallery UAV riêng. Manifest: `predictions/VN0708-.../split_manifest_*.csv` |
| A — ngoại hình | Ứng viên là mọi ảnh UAV trong phiên |
| B — ngoại hình + thời gian | Chỉ ứng viên **cùng buổi quay**. AG-ReID không có toạ độ nên chưa thêm giới hạn vị trí |
| Mục tiêu vắng mặt | Mỗi truy vấn có bản sao đã **xoá người đúng khỏi ứng viên** |
| Người giống áo | Ứng viên có người khác **trùng loại áo, quần, túi và màu tóc** |
| Ngưỡng τ | Nhỏ nhất sao cho **chấp nhận nhầm khi vắng mặt ≤ 10%** trên phiên 1 |

Phiên 1 gồm các ngày 14/02, 21/02, 22/02, 22/03, 24/03, 04/04; phiên 2 gồm 05/04,
06/04, 07/04 (chiều CCTV → UAV).

### Ngưỡng đã chốt

| Chiều | A — ngoại hình | B — ngoại hình + thời gian |
|---|---|---|
| CCTV → UAV | τ = 0,750 | τ = 0,727 |
| Kính đeo → UAV | τ = 0,743 | τ = 0,717 |

Ngưỡng **không chỉnh** sau khi xem phiên 2.

### Kết quả trên phiên 1 (CCTV → UAV, n = 962)

| | Rank-1 không ngưỡng | Bàn giao đúng | Bàn giao sai | Từ chối |
|---|---:|---:|---:|---:|
| A | 26,72% | 9,56% | 9,04% | 81,39% |
| B | 44,80% | 15,38% | 8,52% | 76,09% |

## 3. VN-08 — Test cố định trên phiên 2

### CCTV → UAV (chiều chính), n = 849

| | A — ngoại hình | B — ngoại hình + thời gian |
|---|---|---|
| Rank-1 không ngưỡng | 41,11% | 55,95% |
| **Bàn giao đúng** | 15,55% [13,07 – 17,79] | **24,62%** [21,79 – 27,56] |
| **Bàn giao sai** | 3,42% [2,24 – 4,71] | 4,95% [3,42 – 6,48] |
| Từ chối | 81,04% | 70,44% |
| **Độ chính xác khi bàn giao** | 81,99% (n = 161) | **83,27%** [78,49 – 88,05] (n = 251) |
| Chấp nhận nhầm khi vắng mặt | 4,83% | 7,42% |

**So sánh cặp B − A trên cùng truy vấn:** bàn giao đúng **+9,07** [+7,18 – +10,95],
bàn giao sai +1,53 [+0,12 – +3,06]. Cả hai đều có ý nghĩa.

### Ca người giống áo

49% truy vấn ở điều kiện B (415/849) có người khác trùng loại áo, quần, túi, màu tóc
trong danh sách ứng viên. Ở những ca này, **bàn giao sai tăng từ 4,95% lên 6,75%**
[4,58 – 9,16]. Đây là kiểu lỗi nguy hiểm nhất: drone bám nhầm người mặc giống mục tiêu.

### Kính đeo → UAV (chiều phụ), n = 1.121

| | A | B |
|---|---|---|
| Bàn giao đúng | 4,82% | 10,26% |
| Bàn giao sai | 6,16% | 6,78% |
| Độ chính xác khi bàn giao | **43,90%** | **60,21%** |

Camera thấp ~1,5 m **không đủ tin cậy làm nguồn bàn giao** — ngay cả với giới hạn
thời gian, gần 40% số lần bàn giao là nhầm người.

### Đọc kết quả

1. **Quy trình chọn ngưỡng an toàn:** chấp nhận nhầm khi vắng mặt trên phiên 2 là
   4,8–7,6%, **không vượt** mục tiêu 10% đã đặt trên phiên 1. Ngưỡng không bị khớp
   quá mức vào phiên 1.
2. **Giới hạn thời gian chủ yếu biến ca từ chối thành ca bàn giao đúng** (+9 điểm),
   trong khi độ chính xác khi bàn giao giữ quanh 83%. Đây là thêm một bằng chứng sau
   VN-04 cho thiết kế "thu hẹp ứng viên trước".
3. **Ở mức an toàn đã chọn, hệ thống từ chối khoảng 70% số ca.** Với chất lượng ReID
   hiện tại, bước nhận lại chỉ nên dùng để **xác nhận**, còn quyết định bàn giao cần
   thêm vị trí (CH1) và người duyệt.
4. **Rank-1 giữa hai phiên chênh nhiều** (A: 26,7% so với 41,1%), một phần vì gallery
   phiên 2 nhỏ hơn. Con số của một phiên đơn lẻ dao động mạnh — lý do pilot thật phải
   có ít nhất 2 phiên.

## 4. M9 — Mục tiêu xác minh giao cho Việt

`handoff_M9/muc_tieu_xac_minh.json` — **251 mục tiêu** đã bàn giao ở phiên 2, điều kiện
B, chiều CCTV → UAV. Trong đó 209 đúng (83,3%). Định dạng: xem
`handoff_M9/README.md`.

## 5. M10 — Dự đoán thô cho kiểm tra chéo

`predictions/VN0708-mo-phong-agreid-20261010/` — 8 file CSV (2 chiều × 2 phiên × 2 điều
kiện), mỗi dòng một truy vấn: điểm khi có mặt, điểm khi vắng mặt, ngưỡng, quyết định,
kết quả, cờ giống áo. Tính lại mọi chỉ số trong báo cáo này chỉ từ các file đó, không
cần GPU.

## Giới hạn

- Toàn bộ là **mô phỏng**. CH2 trên AG-ReID.v2, không phải khuôn viên trường; CH1 dùng
  thông số máy quay giả định.
- AG-ReID.v2 không có toạ độ, nên điều kiện B mới có **giới hạn thời gian**, chưa có
  giới hạn vị trí như VN-07 yêu cầu.
- "Giống áo" dựa trên **loại** trang phục; AG-ReID.v2 không có nhãn **màu** áo.
- Khoảng tin cậy bootstrap theo truy vấn; nhiều truy vấn của cùng một người không độc
  lập hoàn toàn nên khoảng thật có thể rộng hơn.
- Chưa nối được chuỗi tìm kiếm → bàn giao vì **M8 của Lương chưa có**.

## Tái lập

```bash
# CH1 — chạy trên CPU, khoảng 1 phút
python dt2_handoff/src/vn06_mo_phong_dinh_vi.py

# CH2 — cần GPU, khoảng 10 phút
python dt2_handoff/src/vn07_vn08_ban_giao.py --goc D:/Data/AG-ReID.v2
```

Kết quả: `metrics/VN06-mo-phong-dinh-vi-20261010.csv` (28 dòng),
`metrics/VN0708-mo-phong-agreid-20261010.csv` (68 dòng), cấu hình ở
`configs/VN0708-mo-phong-agreid-20261010.json`.
