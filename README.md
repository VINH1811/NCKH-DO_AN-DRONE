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

Thống nhất ngày 05/10 (C-03):

- Luôn báo cáo **n** (số truy vấn / ảnh / track) và **mức ngẫu nhiên**.
- **Khoảng tin cậy 95%** bằng bootstrap: `python common/bootstrap_ci.py --predictions <dir> --metric <tên> --n-boot 1000`.
- So sánh hai cấu hình bằng **so sánh cặp trên cùng truy vấn**.
- Dữ liệu pilot quay **ít nhất 2 phiên**: **phiên 1 để chọn ngưỡng, phiên 2 để test**. Sau khi xem kết quả test thì không chỉnh ngưỡng nữa.
- Split **chia theo phiên quay / danh tính**, không chia ngẫu nhiên frame.
- Benchmark gốc phải giữ **evaluator và protocol gốc**. Kết quả trên dữ liệu tự thu báo cáo **riêng** (chuyển miền).

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
