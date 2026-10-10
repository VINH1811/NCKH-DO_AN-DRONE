# Gói dữ liệu SecondPaper — mốc M1

**Giao:** Vinh (ĐT2) → **Nhận:** Lương (ĐT3) · Tạo lúc 04/10/2026 16:27
Phục vụ **LG-01, LG-02, LG-03**.

---

## ĐỌC BA MỤC NÀY TRƯỚC KHI CHẠY

### 1. Embedding là 768 chiều, không dùng được với ViT-B/32

Chỉ mục trong gói sinh bằng:

- Ảnh: `open_clip ViT-L-14, pretrained='openai'`
- Chữ: `M-CLIP/XLM-Roberta-Large-Vit-L-14`
- Vector **768 chiều**, đã chuẩn hoá L2 (đã kiểm tra)

Mô hình `xlm-roberta-base-ViT-B-32` trong việc LG-01 cho vector **512 chiều**,
**không khớp** với gói này.

| Việc | Dùng gì |
|---|---|
| **LG-02** tái lập baseline | Dùng lại `emb/emb_f32.npy`; nạp đúng `M-CLIP/XLM-Roberta-Large-Vit-L-14` để mã hoá câu truy vấn |
| **LG-03** so sánh mô hình | **Phải tự nhúng lại toàn bộ `crops/`** bằng ViT-B/32. Vector trong gói không dùng được |

### 2. Con số 93.548 trong bảng tiến độ không tái lập được

Cơ sở dữ liệu đã thay đổi từ lúc viết bài báo (thêm camera drone, thêm nhãn, xoá
bớt track). Các con số hiện tại:

| Cách lọc | Số ảnh |
|---|---|
| Tất cả (gói này) | 98,552 |
| Trừ camera drone | 94.650 |
| Trừ drone + keyframe đã xoá | 94.009 |
| Trừ drone + track đã xoá | 90.241 |

**Không tổ hợp nào ra 93.548.** Vì vậy **`manifest/keyframes.csv` là mốc chính
thức từ nay**. Mọi kết quả báo cáo phải nói rõ lọc theo cột nào của file đó.
Đừng mất thời gian dựng lại con số cũ.

### 3. Dữ liệu gồm hai nửa khác hẳn nhau — đừng gộp

Cột `camera` trong `index.db` chỉ là **tên khu vực** (5 giá trị), không phải danh
tính camera. Gói này đã tách sẵn cột **`camera_id`** (18 giá trị)
và cột **`nguon`** trong mọi file manifest.

| `nguon` | Là gì | Số ảnh | Số mô tả |
|---|---|---|---|
| `edata` | **9 camera cố định** | 23,436 | **228** |
| `video` | 8 lần quay bằng **điện thoại** | 71,214 | 22 |
| `drone` | Tello bay trực tiếp | 3,902 | 0 |

9 camera cố định là: `DuongGiangVien/Cam1`, `SanCanteenLemon/Cam1`, `SanCanteenLemon/Cam2`, `SanCanteenLemon/Cam3`, `SanTruong/Cam1`, `SanTruong/Cam2`, `SanTruong/Cam3`, `SanhGiangDuongHai/Cam1`, `SanhGiangDuongMot/Cam1`.

Ba điều rút ra:

- **"9 camera" trong bảng tiến độ ứng với nửa `edata`**, và nửa đó chỉ có
  23,436 ảnh — không phải 93.548. Hai con số này không thuộc
  cùng một tập. Cần thống nhất lại với chủ nhiệm trước khi viết báo cáo.
- **228/250 mô tả nằm trên nửa `edata`.** Nên phần
  đánh giá tìm kiếm thực chất chạy trên 9 camera cố định, còn nửa video chỉ
  đóng góp 22 câu.
- **Dùng `camera_id`, đừng dùng `khu_vuc`** — nếu không thì 3 camera Sân trường
  bị gộp làm một và phân tích theo camera sẽ sai.

---

## Nội dung gói

```
SecondPaper_M1/
├── README.md                     file này
├── SHA256SUMS.txt                kiểm tra toàn vẹn (trừ crops)
├── index.db                      có
├── crops/                        98,549 ảnh (557 MB)
├── annot_audio/                  250 file, khớp cột `audio`
├── audio_nhieu_nguoi/            250 file, 2 người nói
├── emb/
│   ├── emb_f32.npy               (98,552, 768) float32
│   └── emb_kf_id.npy             kf_id theo đúng thứ tự dòng trên
├── manifest/
│   ├── keyframes.csv             98,552 dòng  <- MỐC CHÍNH THỨC
│   ├── annotations_250.csv       250 dòng
│   ├── tracks.csv                38,063 dòng
│   ├── speaker_asr.csv
│   └── thong_ke.json
└── moi_truong/pip_freeze.txt
```

### Về 250 mô tả

Bảng `annotations` có **409 dòng**, nhưng **159 dòng rỗng** (ca bị bỏ qua lúc gán
nhãn). File `annotations_250.csv` **đã lọc sẵn** đúng 250 dòng có cả
chữ lẫn ghi âm. Mỗi dòng kèm sẵn bản chép lời Whisper, PhoWhisper và bản dịch
tiếng Anh, khỏi phải join lại.

Phân bố theo camera:

| camera_id | Số mô tả |
|---|---|
| `SanTruong/Cam1` | 49 |
| `SanTruong/Cam3` | 48 |
| `SanTruong/Cam2` | 42 |
| `SanCanteenLemon/Cam1` | 39 |
| `SanhGiangDuongMot/Cam1` | 18 |
| `SanhGiangDuongHai/Cam1` | 11 |
| `SanCanteenLemon/Cam3` | 11 |
| `SanCanteenLemon/Cam2` | 10 |
| `SanCanteenLemon1` | 8 |
| `SanCanteenLemon3` | 4 |
| `DuongGiangVien` | 3 |
| `SanhGiangDuongHai` | 2 |
| `SanTruong1` | 2 |
| `SanhGiangDuongMot` | 2 |
| `SanCanteenLemon2` | 1 |

---

## Nạp dữ liệu

```python
import numpy as np, pandas as pd

E  = np.load("emb/emb_f32.npy")     # (98,552, 768) float32, đã chuẩn hoá L2
ID = np.load("emb/emb_kf_id.npy")   # kf_id tương ứng từng dòng của E
kf = pd.read_csv("manifest/keyframes.csv")
an = pd.read_csv("manifest/annotations_250.csv")

dong = {int(k): i for i, k in enumerate(ID)}   # kf_id -> chỉ số dòng trong E
```

Vì vector đã chuẩn hoá L2, **tích vô hướng chính là cosine** — không chuẩn hoá
lại lần nữa:

```python
from multilingual_clip import pt_multilingual_clip
import transformers

ten = "M-CLIP/XLM-Roberta-Large-Vit-L-14"
m   = pt_multilingual_clip.MultilingualCLIP.from_pretrained(ten)
tok = transformers.AutoTokenizer.from_pretrained(ten)

q = m.forward(["nữ sinh mặc áo cam, đeo balo đen"], tok).detach().numpy()
q = q / np.linalg.norm(q, axis=1, keepdims=True)
top = np.argsort(-(E @ q[0]))[:10]
print(kf.set_index("kf_id").loc[ID[top], ["camera_id", "ts", "crop_path"]])
```

Ảnh của một keyframe nằm ở `crops/<crop_path>`.

---

## Khuyến nghị chia dev/test cho LG-02

Checklist tái lập yêu cầu **chia theo phiên quay, không chia ngẫu nhiên theo
frame**. Với bộ 250 mô tả, cần lưu ý:

- Một camera chiếm phần lớn số mô tả (xem bảng trên). Chia ngẫu nhiên sẽ khiến
  camera đó át cả hai tập, và Recall không nói lên điều gì về camera khác.
- **Chia theo `camera_id`**, giữ nguyên cả cụm của một camera về một phía.
- Cùng một `track_id` tuyệt đối không được nằm ở cả dev lẫn test.
- Khoá split xong thì xuất `split_manifest.csv` và **không sửa nữa** sau khi đã
  nhìn kết quả test.

---

## Kiểm tra toàn vẹn sau khi chép

```bash
# đứng trong thư mục SecondPaper_M1
sha256sum -c SHA256SUMS.txt
```

**Lưu ý:** `keyframes.csv` có 98.552 dòng nhưng `crops/` chỉ có 98.549 ảnh — thiếu
3 khung hình chụp từ drone (ghi hỏng lúc bay trực tiếp). Cả 3 đều **không** nằm
trong 250 mô tả, và track của chúng vẫn còn khung hình khác, nên không ảnh hưởng
gì. Khi lặp qua manifest nhớ bỏ qua file không tồn tại.

Ảnh cắt không nằm trong file băm (quá nhiều file). Kiểm tra bằng số lượng:

```bash
ls crops | wc -l      # phải ra 98549
```

---

## Vướng thì hỏi ai

Mọi thắc mắc về dữ liệu, nhãn, hoặc cách sinh embedding: **hỏi Vinh**, đừng tự
suy đoán rồi chạy tiếp — sai ở bước nạp dữ liệu thì mọi số phía sau đều hỏng.
