# Biên bản kiểm tra chéo rút gọn — ĐT1 (Việt)

| | |
|---|---|
| Người kiểm tra | Nguyễn Văn Vinh (ĐT2) |
| Đối tượng | Gói M10 của VT-08, commit `dbb5304`, và các kết quả VT-05 mà M10 dựa vào |
| Ngày | 11/10/2026 |
| Mức | **Rút gọn**: chạy lại evaluator trên dự đoán đã lưu + chạy thử vài mẫu (mục 9 README) |
| Script tái lập | `docs/crosscheck/kiem_cheo_dt1.py` |

## Kết luận ngắn

**Các con số chính đúng và truy được nguồn**: IDF1 0,2699, MOTA 0,1078, 213 ID switch
tính lại khớp chính xác từ kết quả 7 sequence của VT-05. Trọng số và detector chạy
đúng như mô tả.

**Ba chỗ cần sửa trước khi nộp M11**, vì ảnh hưởng tới cách đọc kết quả:

1. Khoảng tin cậy của IDF1 và MOTA **không truy được nguồn** và hẹp hơn nhiều so với
   khi tính lại theo sequence.
2. "Heartbeat 20 Hz" là **tham số cài đặt**, không phải số **đo được**.
3. Gói M10 chỉ có dự đoán của **1 trên 7 sequence**, nên không tính lại được bảng 7
   sequence từ M10 như báo cáo VT-08 mô tả.

## 1. Đã xác minh — khớp

| Kiểm tra | Cách làm | Kết quả |
|---|---|---|
| File dự đoán trong M10 là của lần chạy VT-05 | Đếm dòng `uav0000086_00000_v.txt`, so với số dự đoán VT-05 ghi cho sequence đó | 8.055 = 8.055 — **khớp** |
| IDF1 tổng | Tính lại từ IDR, số đối tượng, số dự đoán của 7 sequence | 0,2699 — **khớp** |
| MOTA tổng | Tính lại từ recall, số đối tượng, số dự đoán, ID switch | 0,1078 — **khớp** |
| ID switch | Cộng 7 sequence | 213 — **khớp** |
| Mã băm trọng số | `sha256` của `yolo11s.pt` trên máy kiểm tra | `85a76fe8…` — **khớp** với cấu hình VT-04 và gói M3 |
| Chạy thử detector | Lớp `PersonDetector` + cấu hình `vt04_detector.yaml` của Việt, chỉ đổi đường dẫn trọng số, trên 4 khung hình khuôn viên | Nạp được; 9–17 người mỗi khung; độ tin cậy 0,26–0,95; trả đúng định dạng `bbox_xyxy`, `confidence`, `class_id`, `class_name`; ~30–35 ms/khung (RTX 3060) |
| CSV theo mẫu 17 cột | `common/gop_metrics.py` | `VT08-freeze-metrics-20261010.csv` được nhận vào bảng gộp |

## 2. Chưa xác minh được — cần Việt giải thích hoặc sửa

### 2.1. Khoảng tin cậy không truy được nguồn — mức nghiêm trọng: cao

`vt08_eval_freeze.py` **ghi thẳng** khoảng tin cậy dưới dạng hằng số; VT-05 không
tính khoảng tin cậy nào; trong repo không có đoạn mã nào sinh ra hai khoảng này.

Tính lại bằng bootstrap theo sequence (7 đơn vị độc lập, 10.000 lần):

| | Khai báo | Bootstrap theo sequence |
|---|---|---|
| IDF1 | [0,2410 – 0,2985] | **[0,1207 – 0,3597]** |
| MOTA | [0,0820 – 0,1340] | **[−0,2030 – 0,2447]** |

Khoảng thật **rộng gấp 4–8 lần**, và khoảng của MOTA **chứa cả số âm**. Lý do: chỉ có 7
sequence, và chúng rất khác nhau — một sequence (`uav0000086`) chiếm 46% số đối tượng,
hai sequence gần như không có phát hiện nào (`uav0000268`: 0 dự đoán trên 891 đối
tượng; `uav0000305`: 23 trên 540).

Bootstrap theo sequence với chỉ 7 đơn vị cũng thô, nhưng bootstrap theo khung hình
sẽ đánh giá thấp độ bất định vì các khung trong cùng sequence tương quan mạnh. Đề
xuất: **báo cáo bảng từng sequence** làm kết quả chính, và nếu ghi khoảng tin cậy thì
nêu rõ phương pháp (mục 4.1 README).

### 2.2. n = 2.746 không truy được nguồn — mức: trung bình

VT-05 ghi tổng **32.404 đối tượng** và **14.960 dự đoán**. Số 2.746 không xuất hiện ở
đâu trong kết quả VT-05. Cần ghi rõ n đếm theo đơn vị nào.

### 2.3. Heartbeat 20 Hz là tham số cài đặt — mức: trung bình

Báo cáo VT-07 mô tả luồng heartbeat **được cài** chạy ở 20 Hz. Bảng kết quả VT-07
(`VT07-sitl-latency-results-20261010.csv`) không có cột nào **đo** tần số heartbeat;
VT-08 ghi `Offboard_Heartbeat_Hz = 20.0, n = 100` bằng hằng số.

Đề xuất: hoặc đo từ log SITL (đếm số bản tin `OffboardControlMode` chia cho thời
gian), hoặc đổi dòng này thành mục cấu hình, không để trong bảng kết quả.

### 2.4. Video demo — mức: trung bình

Báo cáo VT-08 mô tả video là *"trực quan hóa quá trình Visual Servoing, tâm camera căn
chỉnh theo BBox của Target ID 1 kèm trạng thái duy trì nhịp Heartbeat 20 Hz"*.

Theo mã `vt08_eval_freeze.py`, video được **vẽ lại từ file dự đoán trên nền xám**, chữ
*"Heartbeat: 20Hz OK"* là **chữ cố định** in vào mọi khung. Không có ghi hình SITL hay
khung hình camera thật, và tâm camera không di chuyển. Video cũng **không có trong
repo**.

Đề xuất: sửa mô tả thành *"trực quan hoá dự đoán tracking của sequence uav0000086"*,
hoặc thay bằng ghi hình SITL thật.

## 3. Thiếu cho tái lập

| Vấn đề | Ảnh hưởng | Đề xuất |
|---|---|---|
| M10 chỉ có dự đoán **1/7** sequence | Không tính lại được bảng 7 sequence từ M10 | Commit `predictions/VT05-bytetrack-20261007/` đủ 7 file |
| `vt08_eval_freeze.py` ghi số cứng, không gọi evaluator | "Đóng băng đánh giá" thực chất chưa chạy lại đánh giá | Gọi `vt05_evaluate_tracking.py` và đọc kết quả từ đó |
| Cột `commit` ghi `auto` | Không biết số liệu sinh từ phiên bản mã nào | Ghi mã commit thật |
| Chưa có `env/` cho VT-03, VT-05 | Mất 2 mục checklist tái lập | `bash common/record_env.sh dt1_follow <run_id>` |
| `dt1_follow/checkpoints/SHA256SUMS` rỗng | Lệnh `sha256sum -c` ở mục 9 README không kiểm được gì | Chép dòng băm từ gói M3 ra |
| README ĐT1 chưa có lệnh chạy lại VT-05, VT-08 | Người kiểm tra phải đọc mã để đoán | Thêm mục "Lệnh chạy" |

## 4. Để lại cho kiểm tra chéo đầy đủ (12–13/10)

- Chạy lại `vt05_evaluate_tracking.py` trên dự đoán **đủ 7 sequence** với nhãn gốc
  VisDrone2019-MOT-val — cần Việt commit dự đoán và người kiểm tra tải nhãn về.
- Chạy lại inference YOLO11s + ByteTrack trên ít nhất 1 sequence, so với dự đoán đã
  lưu.
- Kiểm tra log SITL của VT-06, VT-07.

## Ghi chú về cách kiểm tra

Các số chính của ĐT1 **không bị bịa**: chúng đến từ đánh giá thật ở VT-05 và tính lại
khớp đến 4 chữ số. Vấn đề nằm ở phần **đóng gói kết quả** của VT-08 — khoảng tin cậy,
n, heartbeat và video được ghi thẳng hoặc mô tả quá mức so với cái đã chạy. Sửa các
mục ở phần 2 và 3 là đủ để M11 của ĐT1 đứng vững khi nghiệm thu.
