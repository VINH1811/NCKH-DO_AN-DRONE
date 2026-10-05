# Đợt test mô hình và dữ liệu – Đề tài NCKH Drone

Repo chung của nhóm cho đợt test mô hình và dữ liệu của 3 đề tài con. Mục tiêu: mọi kết quả đều **chạy lại được** và **kiểm tra chéo được** giữa các thành viên.

| | |
|---|---|
| **Đợt test chính** | 04/10 – 11/10/2026 |
| **Kiểm tra chéo rút gọn** | 11/10/2026 |
| **Kiểm tra chéo đầy đủ** | 12 – 13/10/2026 |
| **Theo dõi tiến độ** | File `Tiến độ test mô hình drone.xlsx` (bản dùng chung trên Drive) |

## Thành viên và đề tài

| Thành viên | Đề tài | Thư mục | Mô hình / công cụ chính | Dữ liệu |
|---|---|---|---|---|
| Việt (TV1) | ĐT1 – Drone tự động bám theo người trên PX4 | `dt1_follow/` | YOLO11, YOLO-World (Ultralytics), ByteTrack, PX4 SITL + Gazebo | VisDrone DET/MOT |
| Vinh (TV2) | ĐT2 – Bàn giao mục tiêu từ camera mặt đất sang drone | `dt2_handoff/` | OSNet (Torchreid), homography; RemoteCLIP tùy chọn | AG-ReID.v2, pilot tự thu |
| Lương (TV3) | ĐT3 – Tìm người bằng mô tả tiếng Việt trên đa camera | `dt3_retrieval/` | M-CLIP, OpenCLIP đa ngôn ngữ (xlm-roberta-base-ViT-B-32) | SecondPaper (9 camera, 250 mô tả), pilot tự thu |

Ba đề tài nối thành một chuỗi demo:

```
ĐT3: mô tả tiếng Việt → ứng viên (camera, thời điểm)   ──M8──▶
ĐT2: ReID mặt đất → trên cao → mục tiêu đã xác minh     ──M9──▶
ĐT1: detector + tracker + Offboard PX4 → drone bám người
```

---

## 1. Cấu trúc repo

```
.
├── README.md
├── common/                   # dùng chung cho cả 3 đề tài
│   ├── record_env.sh         # ghi pip freeze, nvidia-smi, commit hash
│   ├── sha256_checkpoints.sh # khóa hash checkpoint
│   ├── bootstrap_ci.py       # khoảng tin cậy 95% bằng bootstrap
│   ├── latency.py            # đo p50/p95 sau warm-up
│   └── metrics_template.csv  # mẫu CSV kết quả
├── dt1_follow/
├── dt2_handoff/
├── dt3_retrieval/
└── docs/
    ├── gpu_schedule.md       # lịch dùng GPU
    └── crosscheck/           # biên bản kiểm tra chéo
```

Mỗi thư mục đề tài có cùng cấu trúc:

```
dtX_<tên>/
├── README.md                 # lệnh chạy cụ thể của đề tài
├── requirements.txt          # hoặc environment.yml
├── configs/                  # mỗi thí nghiệm một file config
├── src/
├── data/splits/              # chỉ commit split manifest, không commit dữ liệu
├── checkpoints/SHA256SUMS    # chỉ commit hash, không commit trọng số
├── env/<run_id>/             # thông tin môi trường từng lần chạy
├── predictions/<run_id>/     # dự đoán thô
├── metrics/                  # CSV theo mẫu chung
└── reports/                  # báo cáo ngắn, hình, phân tích lỗi
```

## 2. Quy trình một lần chạy

```bash
# 1. Mỗi đề tài một môi trường riêng
conda create -n dt1 python=3.10 -y && conda activate dt1
pip install -r dt1_follow/requirements.txt

# 2. Khóa hash checkpoint (làm một lần sau khi tải)
bash common/sha256_checkpoints.sh dt1_follow/checkpoints

# 3. Ghi môi trường trước mỗi lần chạy
bash common/record_env.sh dt1_follow <run_id>
#    → dt1_follow/env/<run_id>/{pip_freeze.txt,nvidia_smi.txt,git_commit.txt}

# 4. Chạy thí nghiệm theo config, lưu predictions và metrics
#    (lệnh cụ thể xem README trong từng thư mục đề tài)
```

Quy ước đặt `run_id`: `<mã việc>-<mô tả ngắn>-<yyyymmdd>`, ví dụ `VT03-yolo11s-visdrone-20261005`.

## 3. Mẫu CSV kết quả

Tất cả file trong `*/metrics/` dùng chung các cột:

```csv
run_id,date,commit,task_id,dataset,split,model,checkpoint_sha256,precision,metric,value,ci95_low,ci95_high,n,chance_level,hardware,notes
VT03-yolo11s-visdrone-20261005,2026-10-05,abc1234,VT-03,VisDrone-DET,val,yolo11s,<sha256>,FP16,AP50_person,,,,,,RTX 3090,person-only
```

- Mỗi dòng là **một metric** của một lần chạy, để gộp CSV của cả nhóm cho dễ.
- `chance_level` để trống nếu không áp dụng (ví dụ AP của detector).

## 4. Quy ước thống kê

Chốt ngày 05/10 (C-03). Gộp từ hai bản đề xuất: quy trình và công cụ (Vinh),
cách diễn giải và giới hạn phương pháp (Lương). **Mọi con số trong báo cáo cuối
phải theo mục này.**

Dẫn giải chi tiết các phương pháp khoảng tin cậy và tính toán cỡ mẫu:
[dt3_retrieval/reports/LG02_statistical_reporting.md](dt3_retrieval/reports/LG02_statistical_reporting.md).

### 4.1. Bốn thứ luôn đi kèm mỗi con số

| Bắt buộc | Nghĩa là |
|---|---|
| **n** | Số mục tạo ra con số: số truy vấn, số ảnh, hay số track |
| **Đơn vị lấy mẫu** | Lấy mẫu theo gì: theo truy vấn, theo track, hay theo camera. Quyết định cách tính khoảng tin cậy |
| **Mức ngẫu nhiên** | Điểm của hệ thống đoán bừa trên cùng tập. Không có nó thì "Rank-1 20%" không nói lên điều gì |
| **Khoảng tin cậy 95% + tên phương pháp** | Ghi rõ dùng bootstrap, Wilson hay exact. Phương pháp khác nhau cho kết luận khác nhau |

Mức ngẫu nhiên nên tính bằng **mô phỏng** — xáo thứ hạng rồi chấm lại bằng đúng
hàm chấm điểm — để nó đi chung một đường chấm với kết quả thật.

Các truy vấn **gộp cụm theo track hoặc camera thì không độc lập**. Khi đó bootstrap
phải lấy mẫu theo cụm, không lấy mẫu theo từng truy vấn rời.

### 4.2. So sánh hai cấu hình: dùng so sánh cặp

**Không kết luận bằng cách nhìn hai khoảng tin cậy có chồng nhau hay không.**

Hai cấu hình chạy trên **cùng một tập truy vấn**, mà truy vấn có cái dễ cái khó.
Phần dao động đó xuất hiện ở cả hai bên và **tự triệt tiêu khi lấy hiệu**. Nên
lấy hiệu theo **từng mục** rồi bootstrap trên hiệu đó.

> Khoảng tin cậy của **hiệu** không chứa 0 → khác biệt có ý nghĩa.

Kèm **tỉ lệ thắng theo mục** — "A hơn ở 87% truy vấn" cho biết A thắng đều hay
chỉ nhờ vài ca cá biệt, điều trung bình không nói được.

**Hai cách cho kết luận ngược nhau — ví dụ thật từ ĐT1:**

```
yolo11s          AP = 15,00%  [13,60 – 16,67]
yolov8s-worldv2  AP = 13,43%  [11,99 – 15,04]    <- hai khoảng CHỒNG nhau

So sánh cặp (n = 520 ảnh)
  hiệu = +1,58%  [+1,05 – +2,15]                 <- CÓ ý nghĩa
  yolo11s hơn ở 59,2% số ảnh · worldv2 hơn ở 30,0% · hoà 10,8%
```

Nhìn hai khoảng thì không chốt được detector. So sánh cặp thì chốt được. Đây là
lý do quy ước chọn so sánh cặp, không phải hình thức.

Lý do kỹ thuật thấy rõ hơn ở ĐT2: với Rank-1 trên exp5, **82,9% truy vấn hoà**
(cả hai cùng trúng hoặc cùng trượt). Những mục đó không mang thông tin về khác
biệt — so sánh cặp bỏ qua chúng, so hai khoảng rời rạc thì vẫn gánh hết nhiễu.

### 4.3. Cách diễn giải

Với **metric chính đã chọn trước**:

| Khoảng tin cậy so với mức ngẫu nhiên | Ghi là |
|---|---|
| Hoàn toàn ở trên | Có bằng chứng vượt baseline ngẫu nhiên theo protocol này |
| Cắt qua mức ngẫu nhiên | **"Chưa đủ bằng chứng rằng metric khác mức ngẫu nhiên với dữ liệu và phương pháp hiện tại"** |
| Hoàn toàn ở dưới | Có bằng chứng kém hơn baseline |

Câu ở giữa **không được** diễn giải thành "mô hình bằng ngẫu nhiên", "mô hình vô
dụng", hay "không kết luận được gì". Nó chỉ nói về bằng chứng, không nói về mô hình.

Vượt ngẫu nhiên **không** đồng nghĩa đủ tốt để vận hành. Hai câu hỏi khác nhau.

Nếu kiểm định nhiều metric hoặc nhiều mô hình, phải **định trước metric chính**
hoặc xử lý đa kiểm định.

### 4.4. Metric hiếm lần trúng — chỗ phải cẩn thận nhất

Khi số lần trúng rất ít, **bootstrap percentile cho cận dưới suy biến về 0** —
nhiều mẫu lấy lại không chứa mục trúng nào. Đó là giới hạn của phương pháp, **không
phải bằng chứng rằng n không đủ**.

Ví dụ thật, ĐT3 Recall@1 = 2/70, mức ngẫu nhiên 0,0234%:

| Phương pháp | Khoảng 95% | Loại trừ ngẫu nhiên? |
|---|---|---|
| Bootstrap percentile theo cụm | [0,00 – 7,35]% | Không |
| Wilson | [0,787 – 9,832]% | Có |
| Clopper–Pearson | [0,348 – 9,943]% | Có |
| Binomial một phía | p = 0,00013 | Có |

Nhưng Wilson, Clopper–Pearson và binomial đều **giả định các phép thử độc lập**,
trong khi truy vấn gộp cụm theo track và camera thì không. Nên chúng **lạc quan**.
Còn bootstrap theo cụm thì trung thực với tương quan nhưng suy biến khi hiếm trúng.

> **Với rất ít lần trúng, không phương pháp nào sạch.** Phải nói ra giới hạn, đừng
> chọn con số thuận lợi.

**Quy tắc chốt:** khi số lần trúng **< 5**, báo cáo **cả hai** — khoảng bootstrap
theo cụm *và* kiểm định một phía so với mức ngẫu nhiên — rồi kết luận theo
**phương pháp đã đăng ký trước**, nêu rõ phương pháp còn lại cho kết quả gì.

> **CẦN QUYẾT TRƯỚC 10/10:** phương pháp chính cho nhóm metric này là bootstrap
> theo cụm hay kiểm định nhị thức? Chốt **trước khi** Lương mở tập test.
> Đổi phương pháp sau khi nhìn số là chọn phương pháp theo kết quả.

### 4.5. Cỡ mẫu: không có một n tối thiểu chung

Cỡ mẫu gắn với **mục tiêu cụ thể** (độ chính xác ước lượng hay power), effect
size, alpha, đơn vị độc lập và cách lấy mẫu. Ví dụ thiết kế với truy vấn độc lập,
p ≈ 2/70:

| Mục tiêu | Cỡ mẫu |
|---|---:|
| Phát hiện Recall@1 = 3% vượt chance 1/4.272, power ≥ 80% | n ≈ 53 |
| Ước lượng tỉ lệ với sai số ±2 điểm phần trăm | n ≈ 267 |
| Sai số ±1 điểm phần trăm | n ≈ 1.067 |
| Sai số ±2 điểm phần trăm khi chưa biết p (thiết kế bảo thủ) | n ≈ 2.401 |

Đây là **số hoạch định xấp xỉ**, cho phép thử độc lập. Gộp cụm theo track hoặc
camera thì phải hoạch định bằng mô phỏng lấy mẫu theo nhóm. **Thêm câu mô tả cho
cùng một người không tự động thêm bằng chứng độc lập.**

Các metric khác — mAP, hiệu giữa hai mô hình, tỉ lệ báo nhầm, p95 độ trễ — cần
thiết kế riêng. Không áp n của metric này sang metric kia.

### 4.6. Công cụ chung

Mỗi đề tài xuất một **vector điểm theo từng mục** (`.npy`, `.npz` hoặc `.csv`) —
ĐT1 mỗi ảnh một AP, ĐT2 và ĐT3 mỗi truy vấn một AP hoặc chỉ báo trúng/trượt.
Đã chạy được trên cả ba định dạng của ba đề tài.

```bash
# một cấu hình
python common/bootstrap_ci.py --diem kq.npz --khoa ap --ten "M-CLIP"     --ngau-nhien 0.003 --metric mAP --phan-tram

# so sánh cặp, ghi luôn vào CSV theo mẫu mục 3
python common/bootstrap_ci.py     --diem   a/kq.npz --khoa ap --ten "cấu hình A"     --diem-b b/kq.npz            --ten-b "cấu hình B"     --ngau-nhien 0.00308 --metric mAP --phan-tram     --ra <đề-tài>/metrics/ket_qua_chuan.csv --run-id ... --task-id ...
```

Công cụ tự thêm dòng `<metric>_hieu_cap` vào CSV, nên bảng của cả nhóm có sẵn cả
con số lẫn kết luận so sánh. **CSV phải đúng 17 cột ở mục 3** để gộp được ba đề tài.

### 4.7. Kỷ luật đánh giá

- **Không mở tập test chỉ để tăng n cho khoảng tin cậy đẹp hơn.** Test là đánh giá
  cuối sau khi khoá mọi cấu hình. Có thể báo cáo thêm số gộp dev+test, nhưng phải
  gắn nhãn *"có dữ liệu đã dùng để phát triển"* và không dùng nó để ước lượng hiệu
  năng trên dữ liệu chưa thấy.
- **Không đổi phương pháp thống kê sau khi đã nhìn kết quả.** Thống nhất trước,
  giữ cố định.
- Pilot quay **ít nhất 2 phiên**: phiên 1 chọn ngưỡng, phiên 2 để test.
- Split **chia theo phiên quay / danh tính / camera**, không chia ngẫu nhiên frame.
- Benchmark gốc giữ nguyên **evaluator và protocol của tác giả**. Thấy chỗ lạ cũng
  đừng "sửa cho hợp lý" — sửa là mất khả năng so với bài báo. Muốn thử cách khác
  thì báo cáo **riêng** như thí nghiệm phụ.
- Dữ liệu tự thu báo cáo **riêng**, không gộp bảng với benchmark gốc.
- **Nguồn dữ liệu khác nhau thì báo cáo riêng.** Bộ 250 mô tả gồm 228 câu trên
  `edata` (9 camera, gallery 4.272 track) và 22 câu trên video (gallery 32.404
  track) — hai mức ngẫu nhiên khác nhau, không dùng chung một con số chance, và
  không lấy trung bình đơn giản giữa hai nguồn.
- Lưu **dự đoán thô** vào `predictions/<run_id>/` để người kiểm tra chéo tính lại
  metric mà không cần GPU.

## 5. Đo tốc độ

- Chỉ đo trong **khung giờ GPU riêng** theo [docs/gpu_schedule.md](docs/gpu_schedule.md) (C-02), để chạy chung máy không làm nhiễu p50/p95.
- Warm-up trước, đo **≥ 3 lần**, báo cáo **latency p50/p95** và **VRAM**.
- Tách **tốc độ model** với **tốc độ toàn pipeline**.
- Ghi rõ GPU, driver, CUDA và precision (FP32/FP16/INT8).

## 6. Dữ liệu và đạo đức

| Dữ liệu | Đề tài | Ghi chú |
|---|---|---|
| VisDrone DET/MOT | ĐT1 | Chốt class mapping `pedestrian`/`people` và vùng ignore |
| AG-ReID.v2 | ĐT2 | Protocol mặt đất → trên cao và ngược lại |
| SecondPaper | ĐT3 | 9 camera, 250 mô tả tiếng Việt, file ghi âm; split dev/test theo danh tính |
| Pilot tự thu (07–08/10) | ĐT2, ĐT3 | 2 phiên, nhãn `person_id`/`camera_id`/`timestamp`, bảng điểm mốc mặt đất (mét) |

- **Không commit dữ liệu, video hay trọng số** lên repo. Chỉ commit manifest, hash và script tải.
- Pilot chỉ được thu khi đã có **phiếu đồng ý** và **khu vực quay được duyệt** (C-04). Nếu chưa có drone hoặc giấy phép bay thì quay từ tầng cao/sân thượng.
- Video pilot lưu ở nơi lưu trữ đã được duyệt, không chia sẻ ra ngoài nhóm.

## 7. Lịch đợt test

| Ngày | Việt – ĐT1 | Vinh – ĐT2 | Lương – ĐT3 |
|---|---|---|---|
| **CN 04/10** | Cài Ultralytics, tải VisDrone; cài PX4 SITL + Gazebo | Giao gói SecondPaper (M1); cài Torchreid/OSNet, tải AG-ReID.v2 | Cài môi trường, tải M-CLIP/OpenCLIP; nhận gói SecondPaper |
| **T2 05/10** | YOLO11 vs YOLO-World trên VisDrone DET-val | Baseline OSNet trên AG-ReID.v2 | Tái lập baseline SecondPaper (M-CLIP); khóa split dev/test |
| **T3 06/10** | Chọn detector, giao gói detector/crop (M3) | Phân tích lỗi theo góc nhìn; hồ sơ pilot (M4) | M-CLIP vs OpenCLIP; tiếng Việt / dịch Anh / truy vấn nói; hướng dẫn viết mô tả |
| **T4 07/10** | Detector + ByteTrack trên VisDrone MOT-val | Thu pilot phiên 1, đo điểm mốc (M5) | Thu pilot phiên 1; pipeline YOLO11 → crop → embedding → cosine |
| **T5 08/10** | Đưa quan sát vào SITL | Thu pilot phiên 2, gán nhãn, homography (M6) | Thu pilot phiên 2; viết 30–50 truy vấn (M7) |
| **T6 09/10** | Thử độ trễ, mất quan sát, timeout Offboard | Pilot ReID; chọn ngưỡng trên phiên 1 | Gộp theo track; crop GT vs detector; chọn ngưỡng từ chối |
| **T7 10/10** | Chạy lại kịch bản đã chốt; lưu predictions (M10) | Test cố định phiên 2; gửi mục tiêu cho Việt (M9, M10) | Test cố định; gửi ứng viên cho Vinh (M8, M10) |
| **CN 11/10** | Báo cáo (M11); kiểm tra chéo rút gọn của Lương | Báo cáo (M11); kiểm tra chéo rút gọn của Việt | Báo cáo (M11); kiểm tra chéo rút gọn của Vinh |

Chi tiết từng việc, phụ thuộc và trạng thái: xem sheet **Tiến độ** trong file Excel.

## 8. Mốc bàn giao

| Mã | Nội dung | Giao → Nhận | Hạn | Nếu trễ |
|---|---|---|---|---|
| M1 | Gói dữ liệu SecondPaper | Vinh → Lương | 04/10 | Lương không chạy được baseline 05/10 |
| M2 | Repo mẫu, script ghi môi trường, mẫu CSV | Cả nhóm | 04/10 | Thiếu thông tin tái lập từ đầu |
| M3 | Gói detector + script crop | Việt → Vinh, Lương | 06/10 | Không chạy được pipeline trên pilot |
| M4 | Hồ sơ pilot | Vinh, Lương → Chủ nhiệm | 06/10 | Không thu được pilot 07/10 |
| M5 | Pilot phiên 1 + điểm mốc | Vinh, Lương → Cả nhóm | 07/10 | Không có dữ liệu chọn ngưỡng |
| M6 | Pilot phiên 2 + nhãn + split manifest | Vinh, Lương → Cả nhóm | 08/10 | Chỉ báo cáo baseline trên AG-ReID.v2 và SecondPaper |
| M7 | Bộ truy vấn pilot (30–50 câu) | Lương → Cả nhóm | 08/10 | ĐT3 chỉ đánh giá trên 250 mô tả |
| M8 | Ứng viên (camera, thời điểm) | Lương → Vinh | 10/10 | Không có demo tìm kiếm → bàn giao |
| M9 | Mục tiêu xác minh bàn giao | Vinh → Việt | 10/10 | Không có demo bàn giao → bám theo |
| M10 | Predictions + metrics + README | Mỗi người → Người kiểm tra chéo | 10/10 | Không kiểm tra chéo được 11/10 |
| M11 | Báo cáo ngắn + CSV + config + README | Mỗi người → Chủ nhiệm | 11/10 | Không nghiệm thu được đợt test |

## 9. Kiểm tra chéo

| Người kiểm tra | Kiểm tra đề tài |
|---|---|
| Vinh | ĐT1 – Việt |
| Lương | ĐT2 – Vinh |
| Việt | ĐT3 – Lương |

- **Rút gọn (11/10):** chạy lại evaluator trên predictions đã lưu và smoke test vài mẫu.
- **Đầy đủ (12–13/10):** dựng lại môi trường từ README, chạy lại inference, so sánh với metrics đã báo cáo.
- Ghi kết quả vào `docs/crosscheck/<đề tài>.md`.

Các bước cơ bản cho người kiểm tra:

```bash
git checkout <commit ghi trong báo cáo>
conda create -n check python=3.10 -y && conda activate check
pip install -r dtX_<tên>/requirements.txt
cd dtX_<tên>/checkpoints && sha256sum -c SHA256SUMS && cd -
# chạy evaluator trên predictions đã lưu (lệnh trong README của đề tài)
```

## 10. Checklist tái lập (hạn 11/10/2026)

Mỗi người copy checklist này vào README của đề tài mình và tick dần.

**Mã nguồn**
- [ ] Repo và commit hash của lần chạy cuối
- [ ] Lệnh chạy đầy đủ, chạy lại được từ README
- [ ] File config của từng thí nghiệm

**Mô hình**
- [ ] Checkpoint và hash SHA256
- [ ] Precision khi chạy (FP32/FP16/INT8)
- [ ] Prompt / ngôn ngữ truy vấn (nếu có)

**Môi trường**
- [ ] Phiên bản thư viện (pip freeze hoặc conda env)
- [ ] Phần cứng: GPU, driver, CUDA

**Dữ liệu**
- [ ] Split manifest chia theo phiên quay (không chia ngẫu nhiên frame)
- [ ] Benchmark gốc giữ evaluator và protocol gốc; dữ liệu tự thu báo cáo riêng

**Đánh giá**
- [ ] Ngưỡng chọn trên validation, không chỉnh sau khi xem test
- [ ] Predictions thô đã lưu
- [ ] Metrics xuất CSV theo mẫu chung
- [ ] Báo cáo n, mức ngẫu nhiên, CI 95% (bootstrap)

**Tốc độ**
- [ ] Latency p50/p95 sau warm-up, đo ≥ 3 lần, trong khung giờ GPU riêng
- [ ] Tách tốc độ model với tốc độ toàn pipeline

**Bàn giao**
- [ ] Báo cáo ngắn
- [ ] Kiểm tra chéo rút gọn đã thực hiện và ghi chú kết quả

## 11. Quy ước làm việc

- Mỗi người làm trên nhánh riêng (`dt1`, `dt2`, `dt3`), merge vào `main` khi có kết quả xong.
- Commit message ghi mã việc, ví dụ `VN-03: baseline OSNet trên AG-ReID.v2`.
- Cuối mỗi ngày cập nhật file Excel tiến độ. Ở cột **Link kết quả**, dán link commit chứa kết quả.
- Nếu bị chặn vì chờ người khác hoặc lỗi môi trường, chọn trạng thái **Bị chặn** và ghi rõ lý do.
