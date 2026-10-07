# VN-04 — Phân tích lỗi ReID theo góc nhìn

Ngày 07/10/2026 · Vinh (TV2) · `run_id` **VN04-phan-tich-loi-20261007**

Phân tích lại dự đoán thô của VN-03 (OSNet-AIN đa nguồn, bốn protocol chính thức
của AG-ReID.v2). **Không chạy lại GPU**, không đổi protocol. Mọi con số kèm n và
khoảng tin cậy 95% bootstrap theo mục 4 README.

So sánh giữa các nhóm độ cao dùng **bootstrap không cặp**, vì "bay thấp" và "bay
cao" là hai tập truy vấn khác nhau — khác với so sánh cặp ở mục 4.2, nơi hai cấu
hình chạy trên cùng truy vấn.

## Tóm tắt

| | Phát hiện | Hệ quả cho ĐT2 |
|---|---|---|
| 1 | Bay càng cao khớp càng kém, **nhất quán cả 4 protocol**. Mạnh nhất đúng ở chiều bàn giao thật: CCTV→UAV giảm **22,7 điểm** từ thấp lên cao | Xác nhận người nên làm ở **độ cao thấp** |
| 2 | Ở độ cao thấp, **cỡ người trong ảnh** ảnh hưởng thật (+11 đến +13 điểm). Ở độ cao lớn **chưa thấy** ảnh hưởng — góc nhìn dốc mới là nút thắt | **Hạ độ cao**, phóng to ảnh không thay được |
| 3 | 84–88% lỗi là nhầm với người **ở phiên khác hẳn**. Gần như **không có** lỗi "đúng người nhưng protocol tính sai" | Protocol không tính oan |
| 4 | Chỉ so với người **cùng phiên**, Rank-1 tăng **gần gấp đôi** (CCTV→UAV: 27,89% → ≥49,75%) | **Định vị trước để thu hẹp ứng viên, rồi mới nhận lại** |

## 1. Độ cao bay

Trường `A` trong tên ảnh: 0 thấp · 1 vừa · 2 cao, trong dải 15–45 m của UAV.

Rank-1 (%):

| Chiều | Thấp | Vừa | Cao | Thấp − cao | |
|---|---|---|---|---|---|
| UAV → CCTV | 36,84 | 33,26 | 30,15 | **+6,69** [+1,90 – +11,34] | có ý nghĩa |
| UAV → kính đeo | 33,58 | 26,44 | 19,47 | **+14,11** [+9,26 – +18,50] | có ý nghĩa |
| **CCTV → UAV** | **40,00** | 25,00 | **17,31** | **+22,69** [+17,43 – +27,97] | có ý nghĩa |
| kính đeo → UAV | 31,84 | 16,59 | 13,00 | **+18,84** [+14,77 – +23,16] | có ý nghĩa |

n mỗi ô: 520–904. Giảm **đơn điệu** theo độ cao ở cả bốn protocol, không có ngoại lệ.

**Điều đáng chú ý nhất:** độ cao tác động mạnh hơn hẳn ở chiều **mặt đất → trên
cao** (−22,7 và −18,8 điểm) so với chiều ngược lại (−6,7 và −14,1). Mà chiều mặt
đất → trên cao **chính là chiều của bài toán bàn giao** — camera thấy người trước,
drone phải nhận lại sau. Ở độ cao lớn, con số thực tế để đặt kỳ vọng chỉ còn
**17,31%**.

## 2. Vì sao bay cao lại kém: cỡ người hay góc nhìn

Chiều cao trung vị của người trong ảnh UAV (exp1) giảm đều theo độ cao:
**thấp 232 px → vừa 190 px → cao 154 px**. Câu hỏi là: độ cao làm hại *vì* người
nhỏ đi, hay vì lý do khác?

Để tách hai yếu tố, so người to với người nhỏ **trong cùng một độ cao** (tách ở
trung vị):

| Chiều | Thấp | Vừa | Cao |
|---|---|---|---|
| UAV → CCTV | **+11,01** [+4,44 – +17,56] | −1,84 [−8,52 – +4,39] | +0,65 [−6,20 – +7,46] |
| UAV → kính đeo | **+13,33** [+6,03 – +20,66] | **+11,14** [+5,00 – +17,40] | +1,58 [−4,22 – +7,75] |

Đọc bảng:

- **Ở độ cao thấp**, người to hơn trong ảnh dễ khớp hơn rõ rệt, có ý nghĩa ở cả
  hai protocol. Độ phân giải là yếu tố thật.
- **Ở độ cao lớn**, chưa thấy cỡ người tạo khác biệt ở cả hai protocol. Khi nhìn
  gần như thẳng từ trên xuống, ảnh chủ yếu thấy đầu và vai — phần trang phục mặt
  trước, thứ OSNet dựa vào nhiều nhất, không còn trong khung. Ảnh có to hơn thì
  thông tin đó vẫn không có.

> Diễn giải thận trọng: ở độ cao lớn, khoảng tin cậy **rộng** (khoảng ±7 điểm), nên
> đây là *chưa đủ bằng chứng có ảnh hưởng*, không phải *bằng chứng không có ảnh
> hưởng* (mục 4.3 README).

**Hệ quả cho drone:** ở độ cao lớn, **phóng to hay tăng độ phân giải camera không
thay được việc hạ độ cao**. Muốn xác nhận đúng người thì phải đổi góc nhìn, không
phải đổi số điểm ảnh.

## 3. Khi sai thì sai kiểu gì

Phân loại ảnh xếp hạng 1 của mọi truy vấn trả lời sai:

| Chiều | Số truy vấn sai | Nhầm hẳn *(khác người, khác phiên)* | Nhầm người cùng cảnh *(khác người, cùng phiên)* | Đúng người, protocol tính sai |
|---|---:|---:|---:|---:|
| UAV → CCTV | 1.564 | 87,3% | 12,7% | 0,1% |
| UAV → kính đeo | 1.623 | 87,8% | 12,1% | 0,1% |
| CCTV → UAV | 1.306 | 84,2% | 15,8% | 0,1% |
| kính đeo → UAV | 1.869 | 86,0% | 13,9% | 0,1% |

### Giả thuyết ban đầu đã bị bác bỏ

Protocol định nghĩa danh tính là bộ ba **(người, thời điểm, độ cao)**, và khoảng
**22% truy vấn** có ảnh của *cùng người* nhưng khác thời điểm hoặc độ cao nằm trong
gallery. Giả thuyết ban đầu: mô hình hay tìm đúng người nhưng bị protocol tính sai.

**Số liệu cho thấy không phải vậy.** Chỉ 1 trường hợp trên mỗi protocol (0,1%).
Rank-1 tính lại theo *người* chỉ tăng **+0,04 đến +0,06 điểm**:

| Chiều | Chính thức | Tính theo người *(thí nghiệm phụ)* |
|---|---|---|
| UAV → CCTV | 33,62% | 33,66% |
| UAV → kính đeo | 26,53% | 26,57% |
| CCTV → UAV | 27,89% | 27,94% |
| kính đeo → UAV | 20,13% | 20,17% |

Nên **con số chính thức không bị protocol làm méo**, dùng được trực tiếp.

## 4. Thu hẹp ứng viên: kết quả quan trọng nhất cho ĐT2

Gallery của benchmark **trộn người từ mọi ngày quay** — trung bình gần 10.000 ảnh.
Bàn giao thật thì khác: drone chỉ cần phân biệt **những người đang có mặt ở hiện
trường lúc đó**.

Xấp xỉ gần nhất có thể: chỉ giữ ứng viên **cùng phiên quay** (cùng trường `T`,
tức cùng ngày và cùng buổi).

| Chiều | Gallery đầy đủ | Rank-1 | Gallery cùng phiên | Rank-1 cùng phiên *(cận dưới)* |
|---|---:|---:|---:|---:|
| UAV → CCTV | 6.347 | 33,62% | ~778 | **≥ 55,65%** [53,61 – 57,68] |
| UAV → kính đeo | 12.912 | 26,53% | ~1.474 | **≥ 50,02%** [47,94 – 52,11] |
| **CCTV → UAV** | 14.362 | **27,89%** | ~1.653 | **≥ 49,75%** [47,49 – 52,13] |
| kính đeo → UAV | 12.568 | 20,13% | ~1.456 | **≥ 40,51%** [38,50 – 42,44] |

**Thu hẹp ứng viên khoảng 9 lần thì Rank-1 tăng gần gấp đôi**, ở cả bốn protocol.

Vì sao là **cận dưới**: dự đoán thô chỉ lưu top-100. Truy vấn nào không có ứng viên
cùng phiên trong top-100 (21–38 truy vấn mỗi protocol) bị tính là trượt.

Và gallery "cùng phiên" ở đây vẫn có **khoảng 800–1.600 ảnh** — một buổi quay cả
tiếng đồng hồ. Ứng viên thật trong một lần bàn giao chỉ là những người có mặt ở
đúng chỗ, đúng lúc: **vài người đến vài chục người**. Nên con số thực địa nhiều
khả năng còn cao hơn — nhưng **không được ngoại suy** sang dữ liệu khuôn viên
trường khi chưa đo trên pilot.

### Vì sao đây là kết quả quan trọng nhất

Nó cho căn cứ định lượng cho **thiết kế của chính ĐT2**: dùng camera mặt đất
**định vị người trên bản đồ** (CH1), rồi drone chỉ tìm **trong vùng quanh vị trí
đó, trong khoảng thời gian đó** — sau đó mới so khớp ngoại hình.

Nói cách khác, **định vị không chỉ để dẫn đường cho drone. Nó trực tiếp làm tăng
độ chính xác nhận lại người**, bằng cách loại phần lớn người không liên quan ra
khỏi danh sách so sánh. 84–88% lỗi ở mục 3 là nhầm với người ở phiên khác — đúng
loại lỗi mà bước thu hẹp này loại bỏ.

## 5. Một nguyên lý chung

Ghép VN-03 với VN-04 ra một nguyên lý nhất quán:

| Phát hiện | Nguồn |
|---|---|
| Camera mặt đất **cao hơn** (CCTV 3 m) khớp với UAV tốt hơn camera **thấp hơn** (kính 1,5 m) | VN-03 |
| UAV bay **thấp hơn** khớp với camera mặt đất tốt hơn UAV bay **cao hơn** | VN-04 |

> **Điều quyết định là khoảng cách góc nhìn giữa hai camera.** Nâng camera mặt đất
> lên và hạ drone xuống đều thu hẹp khoảng cách đó từ hai phía.

## 6. Khuyến nghị

**Cho thiết kế bàn giao của ĐT2:**

1. **Thu hẹp ứng viên bằng vị trí và thời gian trước khi so khớp ngoại hình.** Đây
   là đòn bẩy lớn nhất đo được — lớn hơn cả việc đổi mô hình.
2. **Tìm ở trên cao, xác nhận ở dưới thấp.** Bay cao để quét vùng rộng; khi đã có
   ứng viên thì hạ độ cao trước khi khoá mục tiêu.
3. **Đặt camera mặt đất cao nhất có thể** — đã có trong hồ sơ pilot M4.

**Cho pilot 07–08/10:**

- Máy góc cao ở tầng 4–6 (~15–20 m) nằm ở **đầu thấp** của dải 15–45 m của
  AG-ReID.v2 — đúng vùng thuận lợi nhất theo phân tích này.
- Nếu sau này thu thêm dữ liệu, quay từ **hai độ cao khác nhau** sẽ cho phép kiểm
  chứng hiệu ứng độ cao ngay trên khuôn viên trường. **Không đổi giữa phiên 1 và
  phiên 2** của đợt này — hai phiên phải cùng điều kiện thì mới tách dev/test được
  (mục 4.7).

## Giới hạn

- Tất cả trên **một mô hình** (OSNet-AIN đa nguồn). Chưa kiểm tra mô hình khác có
  cùng xu hướng không.
- Mục 2 chỉ làm được cho hai protocol có truy vấn là ảnh UAV (exp1, exp2).
- "Cùng phiên" là xấp xỉ thô của tình huống bàn giao thật, và là cận dưới.
- Mục 3 và mục 4 là **thí nghiệm phụ**, không thay con số chính thức theo protocol
  của tác giả (mục 4.7 README).
- Chưa làm phần tuỳ chọn RemoteCLIP.

## Tái lập

```bash
python dt2_handoff/src/vn04_phan_tich_loi.py \
    --pred dt2_handoff/predictions/VN03-ain-20261004 \
    --anh D:/Data/AG-ReID.v2/AG-ReID.v2 --protocol-dir D:/Data/AG-ReID.v2 \
    --ra-csv dt2_handoff/metrics/VN04-phan-tich-loi-20261007.csv
```

Chạy trên CPU, không cần GPU — chỉ đọc lại `predictions/` của VN-03. Kết quả:
`metrics/VN04-phan-tich-loi-20261007.csv`, 64 dòng theo mẫu 17 cột.
