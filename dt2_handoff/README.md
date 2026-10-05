# dt2_handoff

ĐT2 – Bàn giao mục tiêu từ camera mặt đất sang drone. Vinh (TV2).

## Cấu trúc và vai trò

```text
dt2_handoff/
├── README.md                 # file này
├── requirements.txt          # thư viện cần cài
├── configs/                  # mỗi lần chạy một file config (do script tự sinh)
├── src/
│   ├── eval_agreid.py        # VN-03: đánh giá OSNet trên AG-ReID.v2
│   └── ghi_moi_truong.py     # VN-02: ghi môi trường + khoá hash checkpoint
├── data/splits/              # protocol lấy thẳng từ tác giả, xem mục Dữ liệu
├── checkpoints/
│   ├── SHA256SUMS            # hash trọng số; KHÔNG commit trọng số
│   └── checkpoint.lock.json  # kèm số danh tính để biết trọng số học trên tập nào
├── env/<run_id>/             # môi trường từng lần chạy
├── predictions/<run_id>/     # dự đoán thô, dùng để kiểm tra chéo không cần GPU
├── metrics/                  # ket_qua.csv, toc_do.csv theo mẫu chung
└── reports/                  # báo cáo ngắn và phân tích
```

## Trạng thái

| Mốc | Trạng thái | Kết quả |
|---|---|---|
| **VN-01** (M1) | Xong | Gói SecondPaper giao Lương: 98.552 ảnh, 250 mô tả, 500 file ghi âm |
| **VN-02** | Xong | `env/VN02-setup-20261004/`, `checkpoints/SHA256SUMS` |
| **VN-03** | Xong | `metrics/ket_qua_chuan.csv` (mẫu chung), `reports/VN03_baseline.md` |
| **C-03** | Xong | `common/bootstrap_ci.py` + mục 4 README gốc |

## Môi trường

```bash
conda create -n dt2 python=3.12 -y && conda activate dt2
pip install -r dt2_handoff/requirements.txt
```

Cần GPU CUDA. Lần chạy tham chiếu: RTX 3060 Laptop 6 GB, driver 546.30,
torch 2.7.1+cu118, Python 3.12.12. Chi tiết đầy đủ trong `env/VN02-setup-20261004/`.

## Dữ liệu — AG-ReID.v2

Tải công khai, **không cần xin phép**, từ repo chính thức
[huynguyen792/AG-ReID.v2](https://github.com/huynguyen792/AG-ReID.v2):

```bash
python -m gdown --folder "https://drive.google.com/drive/folders/16r7G_CuUqfWG6_UCT7goIGRMqJird6vK" -O D:/Data/AG-ReID.v2
cd D:/Data/AG-ReID.v2 && python -c "import zipfile; zipfile.ZipFile('AG-ReID.v2.zip').extractall('.')"
```

Kết quả: 100.502 ảnh, 1.615 danh tính, 807 train / 808 test. Ba nền tảng — UAV
(DJI XT2, 15–45 m), kính đeo (Vuzix M4000, ~1,5 m), CCTV (Bosch, ~3 m).

**Không commit dữ liệu.** Bốn protocol đi kèm bản tải về nên cũng không chép lại
vào `data/splits/`; chúng là file `exp*.txt` nằm cạnh file zip:

| File | Chiều | Query | Gallery |
|---|---|---|---|
| `exp1_aerial_to_cctv.txt` | UAV → CCTV | 2.356 | 6.347 |
| `exp2_aerial_to_wearable.txt` | UAV → kính đeo | 2.209 | 12.912 |
| `exp4_cctv_to_aerial.txt` | CCTV → UAV | 1.811 | 14.362 |
| `exp5_wearable_to_aerial.txt` | kính đeo → UAV | 2.340 | 12.568 |

## Trọng số

Từ Model Zoo của [deep-person-reid](https://github.com/KaiyangZhou/deep-person-reid/blob/master/docs/MODEL_ZOO.md),
tải vào `models/` **ngoài repo**:

| Tên | Huấn luyện trên | Số danh tính |
|---|---|---|
| `osnet_ain_x1_0_dangguon_msdc.pth` | MSMT17 + Duke + CUHK03 (đa nguồn, khái quát miền) | 2510 |
| `osnet_x1_0_msmt17.pth` | MSMT17 (cùng miền) | 1041 |

Hash trong `checkpoints/SHA256SUMS`. **Số danh tính là cách kiểm tra tải đúng file
chưa** — 1000 nghĩa là lỡ lấy bản ImageNet, không dùng làm baseline được.

## Lệnh chạy

**VN-02 — ghi môi trường và khoá hash checkpoint**

```bash
python dt2_handoff/src/ghi_moi_truong.py --ra dt2_handoff/env/VN02-setup-20261004 \
    --ckpt-thu-muc models --precision fp32 --ghi-chu "VN-02: OSNet + AG-ReID.v2"
```

**VN-03 — baseline cả bốn protocol**

```bash
P=D:/Data/AG-ReID.v2
python dt2_handoff/src/eval_agreid.py --goc $P/AG-ReID.v2 \
  --protocol $P/exp1_aerial_to_cctv.txt \
  --protocol $P/exp2_aerial_to_wearable.txt \
  --protocol $P/exp4_cctv_to_aerial.txt \
  --protocol $P/exp5_wearable_to_aerial.txt \
  --model osnet_ain_x1_0 --ckpt models/osnet_ain_x1_0_dangguon_msdc.pth \
  --ra dt2_handoff/metrics/VN03-ain-20261004
```

Khoảng 6 phút cho cả bốn protocol trên RTX 3060.

## Ba chỗ dễ sai

**1. Danh tính là bộ ba (người, thời điểm, độ cao), không phải chỉ người.**
Mã chính thức của tác giả tính `pid = int(P + T + A)` bằng cách nối chuỗi. Cùng
một người quay ở độ cao khác là hai danh tính khác nhau. Nhìn qua rất giống lỗi
nhưng **không được sửa** — đổi đi là mất khả năng so với bài báo. Muốn thử cách
gộp theo người thì chạy `--gop-theo-nguoi` và báo cáo riêng.

**2. torch ≥ 2.6 từ chối nạp checkpoint torchreid.** Mặc định
`weights_only=True` chặn numpy scalar mà mọi checkpoint torchreid đều lưu kèm
(trường `rank1`). Cho phép theo tên lớp cũng không ăn thua vì numpy 2 đã đổi
đường dẫn module. `eval_agreid.py` xử lý bằng cách tự băm SHA256 và in ra trước
khi nạp, rồi chỉ lấy tensor trong `state_dict` — toàn vẹn dựa vào chữ ký đối
chiếu `SHA256SUMS`, không dựa vào lớp chặn của pickle.

> Việt và Lương cũng sẽ gặp lỗi này với bất kỳ checkpoint torchreid nào.

**3. Cython evaluation không chạy được trên Windows.** torchreid lùi về bản
Python thuần, chậm hơn nhưng kết quả giống hệt. `eval_agreid.py` tự tính
CMC/mAP nên không phụ thuộc phần này. Đừng mất công dựng Visual Studio Build
Tools.

## Quy ước lưu trữ

- `data/`: không commit dữ liệu gốc.
- `checkpoints/`: chỉ commit `SHA256SUMS` và `checkpoint.lock.json`.
- `predictions/<run_id>/`: commit dự đoán thô (~2 MB mỗi lần chạy) để kiểm tra
  chéo chạy lại được metric mà không cần GPU.
- `metrics/`: CSV có cột `run_id` để gộp nhiều lần chạy vào một file.
