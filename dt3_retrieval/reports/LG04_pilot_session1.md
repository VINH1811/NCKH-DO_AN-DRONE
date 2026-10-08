# LG-04 — Pipeline pilot phiên 1, đầu việc 07/10/2026

Chuẩn bị ngày 08/10/2026. Người phụ trách xác nhận **chưa thu phiên 1**.
Mã gói M3 có trong repo; chưa tìm thấy file `yolo11s.pt` tại các thư mục dự án/Downloads đã kiểm tra.
Trạng thái hiện tại: **đã dựng mã pipeline, chờ thu pilot và nhận trọng số để chạy thực tế**.
Chưa có kết quả detector/retrieval hay latency trên pilot; không dùng SecondPaper thay cho phiên 1.

## 1. Thu phiên 1 cùng Vinh

1. Thống nhất với Vinh camera dùng quay, mã camera và danh sách người tham gia. Đối chiếu hồ sơ ở `../docs/pilot/` trước khi thu.
2. Quay người đi qua vùng quan sát với các đặc điểm phân biệt như áo, quần, balô. Có cảnh nhiều người và cảnh không có người để kiểm tra pipeline.
3. Giữ nguyên video gốc, ghi camera, thời điểm bắt đầu và mô tả cảnh. Nếu cần đồng bộ nhiều camera, ghi mốc đồng bộ/độ lệch thời gian; không tự coi thời gian các camera là đồng bộ.
4. Dùng phiên 1 cho phát triển/chọn cấu hình; giữ riêng phiên 2 cho test. Không trộn frame hai phiên.
5. Tạo một vài mô tả tiếng Việt tương ứng người trong phiên 1 để kiểm tra ứng viên; đây chưa phải bộ 30–50 truy vấn bàn giao M7.

## 2. Nhận detector

Gói M3 detector/crop do **Việt** bàn giao cho Vinh và Lương. Mã đã có tại:
`../dt1_follow/packages/M3-detector-crop-20261006`.
Nhận trọng số YOLO11s từ gói đó, đặt tại `checkpoints/yolo11s.pt`.
Pipeline tự kiểm tra SHA256 đúng với README M3:
`85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5`.
Không tự tải/thay trọng số khác khi thiếu file. Dùng trực tiếp `PersonDetector` và `PersonCropper` của M3;
cấu hình runtime dùng đường dẫn tuyệt đối để tránh đường dẫn Linux của gói gốc.

## 3. Cài phần bổ sung

Chạy trong `dt3_retrieval`, giữ môi trường Python 3.10 và Torch CUDA hiện có:

```powershell
conda run --no-capture-output -n dt3_py310 python -m pip install -r requirements-pilot.txt
conda run -n dt3_py310 python -m pip check
```

File này giữ Torch 2.6.0 và NumPy 1.26.4, bổ sung Ultralytics theo phiên bản M3,
OpenCV 4.10.0.84 và PyYAML. Không cài nguyên requirements của ĐT1 vì sẽ đổi Torch.
Khả năng chạy checkpoint M3 với Torch 2.6.0 cần xác nhận bằng inference thực tế.

## 4. Khai báo video phiên 1

```powershell
New-Item -ItemType Directory -Force data/pilot/session1 | Out-Null
# Chỉ copy nếu chưa có sources.csv (file trống đã tạo trên máy hiện tại).
if (-not (Test-Path data/pilot/session1/sources.csv)) {
    Copy-Item configs/LG04_sources_template.csv data/pilot/session1/sources.csv
}
```

Thêm từng video/ảnh vào `sources.csv`, ví dụ (thay bằng file thật):

```csv
session_id,camera_id,path,timestamp_offset_ms
session1,cam01,cam01.mp4,0
session1,cam02,cam02.mp4,0
```

Đường dẫn media tính từ thư mục chứa CSV, hoặc dùng đường dẫn tuyệt đối.
`timestamp_ms` là thời gian tương đối trong video cộng offset đã khai báo, không phải giờ thực.
Offset bằng 0 không khẳng định camera đồng bộ. `source_id` giúp phân biệt nhiều video cùng camera.
Ảnh rời dùng offset làm timestamp; không có timestamp suy đoán từ tên file.
Config lấy mỗi 15 frame, không giới hạn tổng số frame. Có thể đổi stride trước khi chạy;
đổi config sau khi index cần tạo thư mục output mới, không dùng lại index cũ.

## 5. Kiểm tra và chạy

```powershell
conda run --no-capture-output -n dt3_py310 python -X utf8 src/pilot_pipeline.py check
conda run --no-capture-output -n dt3_py310 python -X utf8 src/pilot_pipeline.py index
conda run --no-capture-output -n dt3_py310 python -X utf8 src/pilot_pipeline.py search --query-file configs/LG04_example_query.txt --output data/pilot/session1/query_ao_do.csv
```

Sửa `configs/LG04_example_query.txt` bằng UTF-8 theo người thực tế trong phiên quay.
Dùng file để giữ dấu tiếng Việt khi Windows/Conda chuyển tiếp đối số; cũng hỗ trợ `--query` trực tiếp.
Lệnh `check` liệt kê đầu vào/dependency còn thiếu và kiểm tra hash weight.
`index` nạp model OpenCLIP từ cache hiện có; cache thiếu sẽ báo lỗi, không tự tải khi offline.
Ảnh BGR được chuyển sang RGB sau crop, rồi nhúng bằng encoder ảnh OpenCLIP đa ngôn ngữ.
Truy vấn dùng encoder văn bản **cùng checkpoint/cùng không gian 512 chiều**;
chuẩn hóa L2 cả hai phía rồi nhân vô hướng để lấy cosine, không dùng softmax như xác suất.
Đây là lựa chọn triển khai ban đầu để dùng cặp encoder có sẵn, chưa kết luận mô hình tốt nhất từ LG-03.

## 6. Đầu ra và điều kiện hoàn thành

Trong `data/pilot/session1/LG04-index/`:

- `crops/`: ảnh người sau crop/padding 10% theo M3.
- `candidates.csv`: ID crop, camera, video, frame, thời gian, confidence detector, bbox gốc và bbox crop.
- `embeddings.npy`: vector FP32 chuẩn hóa, cùng thứ tự với candidates.
- `index_info.json`: cấu hình, hash đầu vào/weight/mã M3/index, phiên bản thư viện và số frame/crop.
- `frame_timings.csv`: thời gian chẩn đoán một lượt; chưa phải benchmark p50/p95.
- `m3_runtime.yaml`: cấu hình thực tế truyền cho M3.

`query_ao_do.csv` lưu top-10 crop, cosine và vị trí để mở lại video.
File JSON đi kèm ghi truy vấn, hash index và thời gian một truy vấn (có cold-start).
Ảnh/video/crop/index chứa dữ liệu pilot được giữ ở `data/`, đang được Git bỏ qua.

Chỉ đánh dấu **Pipeline chạy được trên phiên 1** sau khi:

- Có video thật và weight đúng hash; `check` đạt.
- `index` hoàn tất, `index_info.json` có `status=indexed` và số crop > 0.
- `search` xuất được top-k; mở lại video theo camera/frame/bbox để kiểm tra ứng viên thật.
- Ghi lần chạy, cấu hình và kết quả vào báo cáo này.

Ứng viên hiện là **crop**, có thể lặp cùng người qua nhiều frame. Chưa gán track/person_id,
chưa có Recall/mAP pilot, chưa có ngưỡng từ chối. Gộp theo track và so crop GT/detector thuộc bước 09/10.

## 7. Kiểm thử mã

```powershell
conda run -n dt3_py310 python -X utf8 -m unittest discover -s src -p test_pilot_pipeline.py -v
```

Kiểm thử cosine/tie, embedding lỗi, chặn phiên 2, và hợp đồng index→search bằng ảnh màu
với detector/encoder giả lập có kiểm soát, dùng cropper M3 thực. Không thay thế inference trên pilot.

Kiểm tra ngày 08/10/2026: 12/12 kiểm thử hiện có đạt, gồm 4 kiểm thử pipeline mới.
Đã cài dependency bổ sung; `pip check` đạt, Torch vẫn là `2.6.0+cu124`, CUDA khả dụng.
Khôi phục cache OpenCLIP và metadata/embedding SecondPaper bị thiếu từ nhánh backup local;
file khôi phục vẫn được Git bỏ qua. Encoder ảnh/văn bản OpenCLIP thật đã chạy trên CUDA,
cho vector `(1, 512)` hữu hạn; ảnh thử là ảnh màu tổng hợp, không phải dữ liệu pilot.
Chi tiết smoke/preflight lưu ở `LG04_validation.json`. Còn thiếu video phiên 1 và weight M3.

API tham khảo: [Ultralytics predict](https://docs.ultralytics.com/modes/predict),
[OpenCLIP](https://github.com/mlfoundations/open_clip).
