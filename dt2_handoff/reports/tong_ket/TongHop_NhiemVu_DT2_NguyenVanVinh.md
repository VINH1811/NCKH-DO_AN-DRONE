---
title: "TỔNG HỢP NHIỆM VỤ VÀ KẾT QUẢ ĐỢT TEST — ĐỀ TÀI CON 2"
---

**Đề tài NCKH cấp Trường 2026–2027:** *Nghiên cứu và phát triển drone có khả năng
theo dõi người thông qua mô tả bằng lời nói*

**Đề tài con 2 (ĐT2):** Bàn giao mục tiêu từ camera mặt đất sang drone

**Người thực hiện:** Nguyễn Văn Vinh (TV2) · **Chủ nhiệm:** ThS. Lê Thị Thùy Trang

**Đợt test:** 04/10 – 11/10/2026 · **Kho mã nguồn:**
[github.com/VINH1811/NCKH-DO_AN-DRONE](https://github.com/VINH1811/NCKH-DO_AN-DRONE)

# Phần A. Tổng quan

## A.1. ĐT2 giải quyết bài toán gì

Trong hệ thống của đề tài, camera giám sát mặt đất phát hiện người cần tìm, sau đó
**giao người đó cho drone** để drone bay tới và bám theo. ĐT2 phụ trách đúng khâu
giao nhận này. Muốn giao được thì phải trả lời ba câu hỏi:

| Câu hỏi | Nói đơn giản |
|---|---|
| **CH1 — Định vị** | Camera thấy người ở pixel nào thì người đó đang đứng ở **vị trí nào trên mặt đất**, sai bao nhiêu mét? |
| **CH2 — Nhận lại** | Khi drone tới nơi, nhìn từ **trên cao**, nó có **nhận ra đúng người** camera mặt đất đã thấy không? |
| **CH3 — Bàn giao** | Khi nào thì **được phép** giao, khi nào phải **từ chối** để không cho drone bám nhầm người? |

## A.2. Các nhiệm vụ và trạng thái

![Hình 0. Chuỗi nhiệm vụ của ĐT2. Xanh dương: đã xong. Xanh lá: làm bằng mô phỏng. Xám: chưa làm được.](hinh/h0_chuoi_nhiem_vu.png)

| Mã | Nhiệm vụ | Phục vụ | Trạng thái | Kết quả một dòng |
|---|---|---|---|---|
| VN-01 · M1 | Giao gói dữ liệu cho Lương | ĐT3 | Xong | 98.549 ảnh, 250 mô tả, 500 ghi âm; toàn vẹn 510/510 |
| VN-03 | Đo mức nhận lại người ban đầu | CH2 | Xong | Tốt nhất 33,62%; cách huấn luyện quan trọng hơn cỡ dữ liệu |
| C-03 | Quy ước thống kê cả nhóm | Cả nhóm | Xong | Hai trường hợp cách cũ kết luận sai |
| M4 | Hồ sơ xin quay pilot | CH1, CH2 | Xong, đã duyệt | 5 tài liệu PDF |
| VN-04 | Phân tích vì sao nhận lại thất bại | CH2, CH3 | Xong | Thu hẹp ứng viên làm kết quả tăng gần gấp đôi |
| — | Đánh giá video cũ | CH1, CH2 | Xong | Dùng được cho CH1, không cho CH2 |
| VN-05 · M5 | Quay pilot | CH1, CH2 | **Chưa làm được** | — |
| VN-06 | Sai số định vị | CH1 | **Mô phỏng** | Máy quay bị trôi là nguồn sai lớn nhất |
| VN-07, VN-08 | Chọn ngưỡng, test bàn giao | CH2, CH3 | **Mô phỏng** | Đúng 83% trong số lần bàn giao |
| VN-09 | Kiểm tra chéo kết quả ĐT1 | Cả nhóm | Xong | Số chính đúng; 4 chỗ cần sửa |

## A.3. Giải thích thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| **Truy vấn / gallery** | Truy vấn là ảnh người cần tìm (từ camera mặt đất). Gallery là kho ảnh để tìm trong đó (từ drone). |
| **Rank-1** | Tỉ lệ truy vấn mà ảnh hệ thống xếp **hạng nhất** đúng là người cần tìm. 33% nghĩa là 1/3 số lần đoán đúng ngay lần đầu. |
| **mAP** | Điểm tổng hợp xét cả thứ hạng của **mọi** ảnh đúng, không chỉ ảnh đầu tiên. |
| **Protocol** | Cách chia truy vấn và gallery do tác giả bộ dữ liệu quy định. Dùng nguyên protocol thì số mới so được với bài báo. |
| **Mức ngẫu nhiên** | Điểm nếu hệ thống đoán bừa. Để biết con số có ý nghĩa hay không. |
| **Khoảng tin cậy 95%** | Khoảng mà con số nhiều khả năng rơi vào nếu đo lại trên bộ truy vấn khác. Viết trong ngoặc vuông, ví dụ 33,62% [31,79 – 35,61]. |
| **So sánh cặp** | So hai cách làm trên **cùng từng truy vấn**, lấy hiệu từng truy vấn rồi mới tính khoảng tin cậy. Khoảng của hiệu không chứa 0 thì hai cách khác nhau thật. |
| **Homography** | Phép biến đổi quy toạ độ pixel trên ảnh về toạ độ mét trên mặt đất, tính từ 4 điểm mốc đã đo. |
| **Trung vị, p95** | Trung vị: một nửa số lần sai ít hơn mức này. p95: 95% số lần sai ít hơn mức này — dùng để nói về **trường hợp xấu**. |
| **Ngưỡng bàn giao** | Mức giống nhau tối thiểu để được phép giao. Thấp hơn ngưỡng thì từ chối. |
| **Mô phỏng** | Dựng lại quy trình trên dữ liệu có sẵn hoặc trên máy tính, khi chưa có dữ liệu thực địa. |
| **Giả định** | Con số điền tạm vào mô phỏng khi chưa đo được. Khác với **giả thuyết** — nhận định đem đi kiểm chứng. |

## A.4. Cách đọc kho mã nguồn

Phần của ĐT2 nằm trong thư mục `dt2_handoff/`:

| Thư mục | Chứa gì | Đọc thế nào |
|---|---|---|
| `reports/` | Báo cáo từng nhiệm vụ | Mở trực tiếp trên GitHub |
| `metrics/` | Bảng số liệu `.csv` | Mở bằng Excel; mỗi dòng là **một chỉ số** |
| `predictions/` | Kết quả thô từng truy vấn | Để người khác tính lại mà không cần chạy lại mô hình |
| `src/` | Mã nguồn | Lệnh chạy ghi cuối mỗi báo cáo |
| `handoff_M1/`, `handoff_M9/` | Bằng chứng giao cho Lương, Việt | Mỗi thư mục có README riêng |

Trong file `metrics/*.csv`, các cột cần nhìn: **`split`** (dữ liệu hay điều kiện nào),
**`metric`** và **`value`** (chỉ số và giá trị), **`ci95_low`**, **`ci95_high`** (khoảng tin
cậy), **`n`** (số truy vấn), **`chance_level`** (mức ngẫu nhiên), **`notes`** (ghi chú).

# Phần B. Các nhiệm vụ đã hoàn thành

## B.1. VN-01 — Giao gói dữ liệu cho Lương (mốc M1)

**Mục đích.** Giao cho Lương (ĐT3) dữ liệu cần để chạy thử tìm người theo mô tả tiếng
Việt.

**Vì sao cần.** Đây là mốc đầu chuỗi. Không có gói này thì ĐT3 không bắt đầu được.

**Cách làm.** Viết script tự đóng gói: chép ảnh, xuất danh sách ảnh và đặc trưng ra file
dễ đọc, tính mã băm cho từng file để kiểm tra không hỏng khi chép, và tự sinh hướng dẫn
sử dụng. Giao trực tiếp qua USB vì gói chứa ảnh người thật.

**Kết quả.**

- Gói 1,49 GB: 98.549 ảnh người, 250 mô tả tiếng Việt có ghi âm, 500 file ghi âm.
- Kiểm tra toàn vẹn sau khi chép: **510/510 file** đúng.
- Trong lúc đóng gói, phát hiện **3 vấn đề trong dữ liệu cũ** và ghi cảnh báo: con số
  93.548 ảnh trong bảng tiến độ không tái lập được; đặc trưng có sẵn không dùng chung
  được với mô hình Lương định dùng; bảng mô tả có 409 dòng nhưng chỉ 250 dòng có nội dung.
- Lương đã dùng gói này chạy xong LG-02 và LG-03.

**Đọc kết quả thế nào.** Mở `README_goi_M1.md` để xem số liệu và ba cảnh báo. Muốn chắc
gói của Lương không bị hỏng, đối chiếu mã băm với `SHA256SUMS.txt`.

**Dẫn chứng trên git.**

| File | Nội dung |
|---|---|
| [handoff_M1/README_goi_M1.md](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/handoff_M1/README_goi_M1.md) | Hướng dẫn kèm gói, có số liệu và cảnh báo |
| [handoff_M1/SHA256SUMS.txt](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/handoff_M1/SHA256SUMS.txt) | Mã băm 510 file |
| [src/dong_goi_m1.py](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/src/dong_goi_m1.py) | Script đóng gói |

## B.2. VN-03 — Đo mức nhận lại người ban đầu

**Mục đích.** Biết một mô hình có sẵn **nhận lại người giữa camera mặt đất và drone**
được tới đâu, trước khi cải tiến gì (CH2).

**Vì sao cần.** Không có mốc ban đầu thì không biết cải tiến sau này có tác dụng hay
không. Đo trên bộ dữ liệu chuẩn quốc tế thì kết quả so được với các nghiên cứu khác.

**Cách làm.** Dùng bộ dữ liệu **AG-ReID.v2** (100.502 ảnh, 1.615 người, quay bằng UAV ở
độ cao 15–45 m, camera giám sát ~3 m và kính đeo ~1,5 m). Chạy hai phiên bản mô hình
OSNet trên đúng **4 protocol của tác giả**, không chỉnh sửa gì.

**Kết quả.**

![Hình 1. Rank-1 của hai phiên bản mô hình trên bốn chiều. Thanh đen là khoảng tin cậy 95%.](hinh/h1_baseline_vn03.png)

| Chiều | n | Bản khái quát miền | Bản thường | Chênh lệch |
|---|---:|---|---|---|
| UAV → CCTV | 2.356 | **33,62%** | 9,55% | +24,07 [+22,28 – +25,89] |
| CCTV → UAV | 1.811 | **27,89%** | 9,00% | +18,88 [+16,84 – +20,98] |
| UAV → kính đeo | 2.209 | **26,53%** | 8,78% | +17,75 [+15,80 – +19,69] |
| Kính đeo → UAV | 2.340 | **20,13%** | 8,72% | +11,41 [+9,87 – +12,99] |

**Đọc kết quả thế nào.**

- Mức đoán bừa chỉ 0,11–0,19%, nên mọi con số trên đều có ý nghĩa thật.
- Hai mô hình cùng kiến trúc, chỉ khác **cách huấn luyện**: bản được huấn luyện để khái
  quát sang môi trường lạ tốt hơn **2,3–3,5 lần**. Khoảng tin cậy của chênh lệch đều xa 0.
- Camera giám sát (~3 m) khớp với drone tốt hơn kính đeo (~1,5 m): camera càng cao, góc
  nhìn càng gần drone.
- Chiều **mặt đất → trên cao** khó hơn chiều ngược lại. Đây đúng là chiều của bài toán
  bàn giao, nên con số để đặt kỳ vọng là **27,89%**, không phải 33,62%.

**Dẫn chứng trên git.**

| File | Nội dung |
|---|---|
| [reports/VN03_baseline.md](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/reports/VN03_baseline.md) | Báo cáo đầy đủ |
| [metrics/ket_qua_chuan.csv](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/metrics/ket_qua_chuan.csv) | Lọc cột `metric` = `Rank1` hoặc `mAP`; dòng có `_hieu_cap` là chênh lệch |
| [src/eval_agreid.py](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/src/eval_agreid.py) | Script đánh giá |

## B.3. C-03 — Quy ước thống kê chung cho cả nhóm

**Mục đích.** Thống nhất cách báo cáo con số để số liệu ba đề tài so được với nhau.

**Vì sao cần.** Nói "cách A tốt hơn cách B" mà không có quy tắc chung thì mỗi người kết
luận một kiểu, và có thể kết luận sai.

**Cách làm.** Soạn quy ước, gộp với đề xuất của Lương, viết công cụ dùng chung cho cả ba
đề tài, rồi thử trên số liệu thật của Việt và Lương. Cả nhóm đã đồng ý.

**Kết quả.** Ba quy tắc chính:

1. Mỗi con số phải kèm **số truy vấn n**, **mức ngẫu nhiên** và **khoảng tin cậy**.
2. So hai cách làm bằng **so sánh cặp trên cùng truy vấn**, không nhìn hai khoảng tin cậy
   có chồng nhau hay không.
3. Với chỉ số rất ít lần đúng, kết luận "vượt ngẫu nhiên" dựa vào **kiểm định hoán vị**.

![Hình 2. Cùng một bộ số của ĐT1. Trái: hai khoảng tin cậy chồng nhau nên không kết luận được. Phải: so sánh cặp cho thấy khác nhau thật.](hinh/h2_c03_so_sanh_cap.png)

**Đọc kết quả thế nào.** Quy ước được chứng minh cần thiết bằng hai trường hợp thật, ở
cả hai cách cũ đều kết luận sai:

| Trường hợp | Cách cũ kết luận | Theo quy ước mới |
|---|---|---|
| Việt so hai detector YOLO11s và YOLO-World | Hai khoảng chồng nhau → **không chọn được** | Hiệu +1,58 [+1,05 – +2,15] → YOLO11s **tốt hơn thật**, hơn ở 59% số ảnh |
| Lương: Recall@1 = 2/70 | Khoảng chứa mức ngẫu nhiên → **chưa đủ bằng chứng** | Kiểm định p = 0,000135 → **vượt ngẫu nhiên thật** |

Kèm theo, tôi viết 3 công cụ dùng chung: chuẩn hoá file số liệu về một mẫu, gộp số liệu
ba đề tài thành một bảng, và xuất tài liệu ra PDF.

**Dẫn chứng trên git.**

| File | Nội dung |
|---|---|
| [README.md, mục 4](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/README.md) | Toàn văn quy ước |
| [common/bootstrap_ci.py](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/common/bootstrap_ci.py) | Công cụ khoảng tin cậy, so sánh cặp, kiểm định |
| [docs/metrics_tong_hop.csv](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/docs/metrics_tong_hop.csv) | Bảng gộp số liệu ba đề tài; lọc theo cột `de_tai` |

## B.4. M4 — Hồ sơ xin quay pilot

**Mục đích.** Xin phép quay dữ liệu thật trong khuôn viên trường.

**Vì sao cần.** Quay người thật phải có đồng ý của họ và phê duyệt của Nhà trường.

**Cách làm.** Soạn cùng Lương 5 tài liệu: tờ trình, phiếu đồng ý cho người tham gia, kế
hoạch vị trí đặt máy, kịch bản 2 buổi quay, hướng dẫn viết mô tả. Vị trí đặt máy chọn
dựa trên kết quả VN-03 (camera càng cao càng tốt).

**Kết quả.** Không bay drone ở buổi pilot mà đặt điện thoại trên tầng 4–6 để có góc nhìn
từ trên cao. Cam kết không nhận diện khuôn mặt, gán mã số thay tên, xoá video sau 90
ngày. **Chủ nhiệm đã duyệt.**

**Dẫn chứng trên git:** [docs/pilot/](https://github.com/VINH1811/NCKH-DO_AN-DRONE/tree/main/docs/pilot) — 5 file PDF.

## B.5. VN-04 — Phân tích vì sao nhận lại thất bại

**Mục đích.** Hiểu **khi nào** và **vì sao** mô hình nhận nhầm người.

**Vì sao cần.** Con số 27,89% chưa nói cho ta phải thiết kế drone thế nào. Biết nguyên
nhân lỗi thì mới biết nên bay ở độ cao nào, lọc ứng viên ra sao.

**Cách làm.** Đọc lại kết quả thô của VN-03, không chạy lại mô hình. Tách theo độ cao bay,
theo cỡ người trong ảnh, phân loại từng lỗi, và thử chỉ so với người quay cùng buổi.

**Kết quả.**

![Hình 3. Rank-1 theo độ cao bay. Bay càng cao càng kém, ở cả bốn chiều.](hinh/h3_do_cao_vn04.png)

![Hình 5. Khi chỉ so với người quay cùng buổi, Rank-1 tăng gần gấp đôi.](hinh/h5_cung_phien_vn04.png)

**Đọc kết quả thế nào.**

- **Bay càng cao, nhận lại càng kém**, mạnh nhất ở đúng chiều bàn giao: CCTV → UAV từ
  40,00% (bay thấp) xuống 17,31% (bay cao).
- Ở độ cao lớn, người to hơn trong ảnh cũng không khớp tốt hơn. Nghĩa là vấn đề nằm ở
  **góc nhìn** (từ trên xuống chỉ thấy đầu và vai), không phải ảnh nhỏ. → Drone muốn xác
  nhận người thì **phải hạ thấp**, phóng to ảnh không thay được.
- 84–88% lỗi là **nhầm với người ở buổi quay khác hẳn**.
- **Kết quả quan trọng nhất:** chỉ so với người cùng buổi quay thì Rank-1 tăng gần gấp
  đôi (27,89% lên ít nhất 49,75%). → **Biết người đang ở đâu, lúc nào trước, rồi mới so
  ngoại hình**. Định vị (CH1) không chỉ để dẫn đường mà còn làm nhận lại chính xác hơn.

**Dẫn chứng trên git.**

| File | Nội dung |
|---|---|
| [reports/VN04_phan_tich_loi.md](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/reports/VN04_phan_tich_loi.md) | Báo cáo đầy đủ |
| [metrics/VN04-phan-tich-loi-20261007.csv](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/metrics/VN04-phan-tich-loi-20261007.csv) | `metric` bắt đầu bằng `Rank1_docao_` là theo độ cao; `loi_` là loại lỗi |

## B.6. Đánh giá video cũ thay cho buổi quay pilot

**Mục đích.** Xem video đã quay trước đó có thay được buổi pilot không.

**Vì sao cần.** Pilot chưa quay được; nếu video cũ dùng được thì không phải chờ.

**Cách làm.** Xem khung hình mẫu của cả 9 nguồn quay để biết góc quay, đối chiếu giờ quay
giữa các nguồn, và đo xem máy quay có bị xê dịch trong lúc quay không.

**Kết quả.**

![Hình 6. Trái: video SanTruong3 quay từ tầng cao. Phải: máy quay trôi dần trong buổi quay.](hinh/h6_santruong3_do_troi.png)

**Đọc kết quả thế nào.**

- Chỉ có **SanTruong3** quay từ trên cao. Không có hai nguồn nào quay **cùng lúc** ở
  cùng chỗ.
- Máy SanTruong3 trôi dần, lệch tới 11,6 điểm ảnh sau gần 2 giờ.
- → **Dùng được cho CH1** (định vị chỉ cần một máy cố định). **Không dùng được cho CH2**
  (phải thấy cùng một người từ mặt đất và từ trên cao cùng một lúc).

# Phần C. Vì sao VN-06 → VN-08 phải mô phỏng

## C.1. Nguyên nhân: pilot chưa quay được

Theo kế hoạch, VN-05 quay pilot ngày 07/10, rồi VN-06, VN-07, VN-08 chạy trên dữ liệu
đó. Pilot chưa quay được nên ba việc sau **không có dữ liệu thật để chạy**. Mốc M6 đã ghi
sẵn phương án dự phòng: báo cáo trên dữ liệu có sẵn. Tôi theo phương án đó nhưng làm
thêm một bước: **dựng lại đúng quy trình pilot** trên dữ liệu có sẵn, để khi có pilot
thật chỉ cần đổi dữ liệu đầu vào và chạy lại.

## C.2. Có đo thực tế được không — được, và chỉ một phần cần pilot

Mô phỏng VN-06 dùng một số **giả định** — con số điền tạm khi chưa có số đo. Chúng được
dùng **không phải vì không đo được**, mà vì hạn chót tới trước buổi quay:

| Thông số | Trong mô phỏng | Đo thực tế được không | Đo bằng cách nào |
|---|---|---|---|
| Rung của điểm chân người | **Đã đo:** 0,39% chiều cao | — | Từ khoảng 2.500 người trong video cũ |
| Độ trôi của máy quay | **Đã đo:** SanTruong3 | — | So khung hình theo thời gian |
| Góc nhìn, tiêu cự máy quay | Giả định 69° | **Được, không cần pilot** | Chụp bàn cờ in sẵn 15–20 tấm, tính bằng OpenCV, mất 15 phút |
| Sai số khi bấm điểm trên ảnh | Giả định 1,5 điểm ảnh | **Được, không cần pilot** | Hai người bấm cùng 5 mốc, mỗi người 3 lần, lấy độ lệch |
| Sai số thước dây | Giả định 2 cm | **Được, không cần pilot** | Đo một đoạn 3 lần bởi 2 người |
| Độ cao, góc chúc của máy | Giả định 2,5 m và 15 m | **Được** | Đo trực tiếp lúc dựng máy |
| Lệch có hệ thống của điểm chân | Giả định 0, 3, 6% | **Chỉ đo được ở pilot** | Cho người đứng lên điểm đã đánh dấu, so vị trí hệ thống báo với vị trí thật |
| **Sai số định vị cuối cùng (CH1)** | — | **Chỉ đo được ở pilot** | Đo tại điểm mốc không dùng để hiệu chuẩn |

Như vậy **3 thông số đo được ngay mà không cần pilot**, chỉ có lệch điểm chân và con số
CH1 cuối cùng mới thật sự phải chờ buổi quay.

## C.3. Vì sao VN-07, VN-08 dùng bộ dữ liệu AG-ReID.v2

Bàn giao cần thấy **cùng một người từ camera mặt đất và từ drone cùng lúc** (mục B.6).
Video cũ của nhóm không có điều đó. AG-ReID.v2 có đúng cấu trúc này: nhiều buổi quay
khác ngày, cùng người được quay từ mặt đất và từ UAV. Nên tôi dựng lại cả thiết kế pilot
trên đó: chia buổi quay thành phiên 1 và phiên 2 theo ngày, chọn ngưỡng trên phiên 1 rồi
khoá lại, test trên phiên 2.

## C.4. Mô phỏng có giá trị gì, không có giá trị gì

| Có giá trị | Không có giá trị |
|---|---|
| Biết trước nguồn sai nào đáng lo để buổi quay thật tránh | **Không phải** sai số thật trong khuôn viên trường |
| Kiểm tra quy trình chọn ngưỡng có an toàn không | **Không** thay được con số CH1, CH2 cuối cùng |
| Script đã sẵn sàng, có pilot thì chạy lại ngay | Không được trộn với số liệu thực địa khi báo cáo |

## C.5. VN-06 — Sai số định vị (mô phỏng)

**Mục đích.** Ước lượng định vị người trên mặt đất sẽ sai bao nhiêu mét, và sai do đâu.

**Cách làm.** Mô phỏng 2.000 lần quy trình sẽ làm ngoài sân: hiệu chuẩn bằng 4 điểm mốc,
rồi đo sai ở các điểm khác. Thêm dần từng nguồn sai để xem nguồn nào lớn nhất. Thử với
máy đặt thấp (chân máy 2,5 m) và máy đặt cao (tầng cao 15 m).

![Hình 7. Sai số định vị p95 khi thêm dần từng nguồn sai. Mô phỏng.](hinh/h7_dinh_vi_vn06.png)

**Đọc kết quả thế nào** (p95 — trường hợp xấu):

- Chỉ sai do đo thước và bấm điểm: **0,11–0,16 m** — gần như không đáng kể.
- Thêm lệch điểm chân 6%: máy thấp **1,14 m**, máy cao **0,36 m** → **máy cao chịu
  sai tốt hơn hẳn**.
- Thêm máy trôi sau 2 giờ: lên **1,92–3,23 m** → **máy quay bị trôi là nguồn sai lớn
  nhất**, lớn hơn mọi nguồn khác cộng lại.
- → Khi quay thật: **kiểm tra lại mốc mỗi 30 phút**, chọn 4 điểm mốc bao hết vùng người
  đi, đặt máy càng cao càng tốt.

## C.6. VN-07, VN-08 — Chọn ngưỡng và test bàn giao (mô phỏng)

**Mục đích.** Dựng quy trình bàn giao hoàn chỉnh và đếm số lần giao đúng, giao sai, từ chối.

**Cách làm.**

- Hai điều kiện: **A** — chỉ so ngoại hình; **B** — so ngoại hình và chỉ xét người cùng
  buổi quay (giới hạn thời gian).
- Thêm ca **mục tiêu vắng mặt**: xoá người đúng khỏi danh sách, xem hệ thống có biết từ
  chối không.
- Thêm ca **người mặc giống**: có người khác cùng loại áo, quần, túi, màu tóc.
- **Chọn ngưỡng trên phiên 1** sao cho khi mục tiêu vắng mặt, hệ thống nhận nhầm không
  quá 10%. Khoá ngưỡng, rồi mới test trên phiên 2.

![Hình 8. Kết quả bàn giao trên phiên 2, chiều CCTV → UAV. Mô phỏng.](hinh/h8_ban_giao_vn08.png)

| Phiên 2, CCTV → UAV, 849 truy vấn | A: ngoại hình | B: + thời gian |
|---|---|---|
| Bàn giao đúng | 15,55% | **24,62%** |
| Bàn giao sai | 3,42% | 4,95% |
| Từ chối | 81,04% | 70,44% |
| Đúng trong số lần đã bàn giao | 81,99% | **83,27%** |
| Nhận nhầm khi mục tiêu vắng mặt | 4,83% | 7,42% |

**Đọc kết quả thế nào.**

- **Ngưỡng chọn trên phiên 1 vẫn an toàn trên phiên 2**: nhận nhầm khi vắng mặt dưới
  mức 10% đã đặt ra. Nghĩa là quy trình chọn ngưỡng dùng được cho pilot thật.
- Thêm giới hạn thời gian thì bàn giao đúng tăng **+9,07 điểm** [+7,18 – +10,95] — thêm
  một bằng chứng cho kết luận "biết vị trí, thời gian trước" ở VN-04.
- Khi giao, hệ thống **đúng khoảng 5/6 lần**. Lần sai còn lại nguy hiểm vì drone bám
  nhầm người, và tăng lên 6,75% khi có người mặc giống mục tiêu.
- Để giữ mức an toàn đó, hệ thống **từ chối khoảng 70% số ca**. → Bước nhận lại hiện
  chỉ nên dùng để **xác nhận**, cần thêm vị trí và người duyệt mới quyết định giao.
- Camera thấp (kính đeo) chỉ đúng 60% trong số lần giao → không dùng làm nguồn bàn giao.

**Đã giao:** **M9** — 251 mục tiêu đã xác minh cho Việt, kèm ảnh mẫu để drone khoá lại
khi mất dấu. **M10** — kết quả thô từng truy vấn cho người kiểm tra chéo.

**Dẫn chứng trên git (VN-06 → VN-08).**

| File | Nội dung |
|---|---|
| [reports/VN06-08_mo_phong_pilot.md](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/reports/VN06-08_mo_phong_pilot.md) | Báo cáo đầy đủ, có thiết kế chốt trước khi chạy |
| [metrics/VN06-mo-phong-dinh-vi-20261010.csv](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/metrics/VN06-mo-phong-dinh-vi-20261010.csv) | Cột `split` = cấu hình máy và kịch bản; giá trị tính bằng mét |
| [metrics/VN0708-mo-phong-agreid-20261010.csv](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/dt2_handoff/metrics/VN0708-mo-phong-agreid-20261010.csv) | `split` dạng `exp4_..._phien2_B` = chiều, phiên, điều kiện |
| [predictions/VN0708-mo-phong-agreid-20261010/](https://github.com/VINH1811/NCKH-DO_AN-DRONE/tree/main/dt2_handoff/predictions/VN0708-mo-phong-agreid-20261010) | Mỗi dòng một truy vấn: điểm, ngưỡng, quyết định, đúng/sai |
| [handoff_M9/](https://github.com/VINH1811/NCKH-DO_AN-DRONE/tree/main/dt2_handoff/handoff_M9) | Danh sách mục tiêu giao Việt; ý nghĩa từng trường ở README |

# Phần D. VN-09 — Kiểm tra chéo kết quả của Việt (ĐT1)

**Mục đích.** Kiểm tra độc lập rằng số liệu ĐT1 nộp lên là đúng và làm lại được.

**Vì sao cần.** Là điều kiện nghiệm thu đợt test: không ai tự chấm kết quả của mình.

**Cách làm.** Đếm và đối chiếu file kết quả Việt lưu, tự tính lại các chỉ số tổng từ số
liệu từng đoạn video, tính lại khoảng tin cậy, kiểm tra mã băm của mô hình, và chạy thử
bộ phát hiện người của Việt trên vài khung hình.

![Hình 9. Cùng giá trị, nhưng khoảng tin cậy Việt khai hẹp hơn nhiều so với tính lại.](hinh/h9_kiem_cheo_vn09.png)

**Đọc kết quả thế nào.**

- **Đúng:** IDF1 0,2699, MOTA 0,1078 và 213 lần đổi ID — tính lại khớp chính xác. Mô
  hình đúng phiên bản, bộ phát hiện chạy được. *(IDF1, MOTA là chỉ số đo độ bám theo:
  giữ đúng người qua các khung hình, càng gần 1 càng tốt.)*
- **Cần sửa:** khoảng tin cậy được ghi tay, không có mã nào tính ra, và hẹp hơn 4–8 lần
  so với tính lại (Hình 9); con số n = 2.746 không rõ nguồn; "heartbeat 20 Hz" là số
  cài đặt chứ chưa phải số đo; video demo được vẽ lại chứ không phải ghi hình; gói chỉ
  có kết quả của 1/7 đoạn video.

**Dẫn chứng trên git.**

| File | Nội dung |
|---|---|
| [docs/crosscheck/dt1_follow.md](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/docs/crosscheck/dt1_follow.md) | Biên bản: mục 1 đã khớp, mục 2–3 cần sửa |
| [docs/crosscheck/kiem_cheo_dt1.py](https://github.com/VINH1811/NCKH-DO_AN-DRONE/blob/main/docs/crosscheck/kiem_cheo_dt1.py) | Chạy lại mọi phép kiểm, không cần GPU |

# Phần E. Việc tiếp theo

| Việc | Cần pilot không | Ghi chú |
|---|---|---|
| Đo góc nhìn máy quay, sai số bấm điểm, sai số thước | **Không** | Thay 3 giả định ở mục C.2 bằng số đo; làm được ngay |
| Quay 2 phiên pilot | — | Hai ngày khác nhau, cùng khung giờ; kiểm tra mốc mỗi 30 phút |
| Chạy lại VN-06 → VN-08 trên pilot | Có | Cùng script, chỉ đổi dữ liệu |
| Thêm giới hạn vị trí vào bàn giao | Có | Cần toạ độ từ hiệu chuẩn pilot |
| Nối chuỗi tìm kiếm → bàn giao → bám theo | Không | Cần mốc M8 từ Lương |
| Kiểm tra chéo đầy đủ ĐT1 (12–13/10) | Không | Cần Việt đưa đủ kết quả 7 đoạn video |

**Giới hạn cần nói rõ khi báo cáo:** VN-06 → VN-08 là mô phỏng; ca "người mặc giống" so
theo loại trang phục, chưa có màu; mọi kết quả nhận lại người mới thử trên một mô hình.

# Phụ lục. Danh sách commit chính

| Commit | Nội dung |
|---|---|
| `de6903b` | VN-03 |
| `298f470`, `9d3752b`, `74183e5` | C-03 |
| `005ee99` | Công cụ chuẩn hoá và gộp số liệu |
| `7d15a3c` | Hồ sơ pilot M4 |
| `6a92e3c` | VN-04 |
| `e5c3682`, `8427083` | VN-06 → VN-08, M9, M10 |
| `bd8a7d1` | VN-09 kiểm tra chéo ĐT1 |
