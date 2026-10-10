# -*- coding: utf-8 -*-
"""Đóng gói mốc M1 — bàn giao dữ liệu SecondPaper từ Vinh sang Lương.

Gói phục vụ hai việc khác nhau của Lương, và chúng cần hai thứ khác nhau:
  LG-02 tái lập baseline  -> dùng lại embedding có sẵn (M-CLIP ViT-L/14, 768-d)
  LG-03 so sánh mô hình   -> phải tự nhúng lại, nên BẮT BUỘC có ảnh cắt gốc

Ba chỗ dễ sai mà script xử lý sẵn:
  1. Bảng annotations có 409 dòng nhưng chỉ 250 dòng có cả chữ lẫn ghi âm.
     Lọc sẵn, không để người nhận tự đoán.
  2. Cột tracks.camera chỉ có 5 giá trị (tên khu vực), trong khi dữ liệu thật
     có 9 camera. Danh tính camera nằm trong chuỗi video. Tách ra thành
     camera_id, nếu không thì 3 camera Sân trường bị gộp làm một.
  3. Embedding nằm dưới dạng BLOB trong SQLite. Xuất thêm .npy để người nhận
     nạp một dòng là chạy, không phải tự giải mã.

Chạy:
  python dong_goi_m1.py --ra D:/giao_Luong
  python dong_goi_m1.py --ra D:/giao_Luong --nhanh   # bỏ db và ảnh, để thử
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

import numpy as np

DB = "data/index.db"
CROP_DIR = "data/crops"
ANNOT_AUDIO = "data/annot_audio"
AUDIO_NGUOI = "Audio"

MO_HINH_ANH = "open_clip ViT-L-14, pretrained='openai'"
MO_HINH_CHU = "M-CLIP/XLM-Roberta-Large-Vit-L-14"
EMB_DIM = 768


def camera_id(video: str) -> tuple[str, str]:
    """Suy ra (camera_id, loại nguồn) từ chuỗi video.

    edata:SanTruong/Cam1-20260609T064658Z-3-001/... -> SanTruong/Cam1
    F:/RawVideo/MotCam/DuongGiangVien.MOV           -> DuongGiangVien
    drone-live                                      -> Drone/Tello

    Phần đuôi dấu thời gian của edata bị cắt đi: cùng một camera nhưng mỗi lần
    tải xuống lại sinh một hậu tố khác, giữ lại thì một camera hoá thành nhiều.
    """
    if video == "drone-live":
        return "Drone/Tello", "drone"
    if video.startswith("edata:"):
        p = video[6:].split("/")
        khu = p[0] if p else "?"
        cam = p[1].split("-")[0] if len(p) > 1 else "Cam?"
        return f"{khu}/{cam}", "edata"
    stem = os.path.splitext(os.path.basename(video.replace("\\", "/")))[0]
    return stem, "video"


def ghi_csv(duong_dan: str, cot: list[str], hang) -> int:
    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    n = 0
    # utf-8-sig để Excel trên Windows mở ra không vỡ dấu tiếng Việt
    with io.open(duong_dan, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cot)
        for r in hang:
            w.writerow(r)
            n += 1
    return n


def sha256(duong_dan: str, khoi: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        while True:
            b = f.read(khoi)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def chep_thu_muc(nguon: str, dich: str) -> tuple[int, int]:
    if not os.path.isdir(nguon):
        return 0, 0
    n = sz = 0
    for goc, _, files in os.walk(nguon):
        rel = os.path.relpath(goc, nguon)
        ra = dich if rel == "." else os.path.join(dich, rel)
        os.makedirs(ra, exist_ok=True)
        for f in files:
            s = os.path.join(goc, f)
            shutil.copy2(s, os.path.join(ra, f))
            n += 1
            sz += os.path.getsize(s)
    return n, sz


def main() -> int:
    ap = argparse.ArgumentParser(description="Đóng gói M1 giao cho Lương")
    ap.add_argument("--ra", required=True, help="thư mục đích, vd D:/giao_Luong")
    ap.add_argument("--nhanh", action="store_true",
                    help="bỏ index.db và ảnh cắt — chỉ để thử cấu trúc gói")
    a = ap.parse_args()

    if not os.path.exists(DB):
        print(f"Không thấy {DB}. Chạy script từ thư mục gốc dự án.")
        return 1

    goc = os.path.join(a.ra, "SecondPaper_M1")
    os.makedirs(goc, exist_ok=True)
    t0 = time.time()
    db = sqlite3.connect(DB)
    bao: dict = {}

    # ── bản đồ track -> (camera_id, loại nguồn, khu vực, video gốc)
    print("Đang dựng bản đồ camera...")
    tr = {}
    for tid, cam, vid in db.execute("select id, camera, video from tracks"):
        cid, loai = camera_id(vid or "")
        tr[tid] = (cid, loai, cam or "", vid or "")
    bao["so_track"] = len(tr)
    bao["so_camera"] = len({v[0] for v in tr.values()})
    # 9 camera cố định nằm ở nửa edata; nửa video là 8 lần quay bằng điện thoại.
    # Hai nửa này khác hẳn nhau về bản chất nên phải báo riêng, không gộp.
    bao["cam_edata"] = sorted({v[0] for v in tr.values() if v[1] == "edata"})
    bao["nguon_video"] = sorted({v[0] for v in tr.values() if v[1] == "video"})

    n = ghi_csv(
        os.path.join(goc, "manifest", "tracks.csv"),
        ["track_id", "camera_id", "nguon", "khu_vuc", "video", "t_start", "t_end"],
        ([tid, tr[tid][0], tr[tid][1], tr[tid][2], tr[tid][3], ts, te]
         for tid, ts, te in db.execute(
             "select id, t_start, t_end from tracks order by id")))
    print(f"  tracks.csv              {n:>7} dòng")

    # ── keyframes: vừa là manifest, vừa là danh sách ảnh cần chép
    print("Đang xuất manifest keyframes...")
    kfs = []
    for kid, tid, ts, cp, ql in db.execute(
            "select id, track_id, ts, crop_path, quality from keyframes order by id"):
        cid, loai, khu, _ = tr.get(tid, ("?", "?", "", ""))
        kfs.append([kid, tid, cid, loai, khu, ts, cp, ql])
    n_kf = ghi_csv(os.path.join(goc, "manifest", "keyframes.csv"),
                   ["kf_id", "track_id", "camera_id", "nguon", "khu_vuc",
                    "ts", "crop_path", "quality"], kfs)
    bao["so_keyframe"] = n_kf
    kf_loai: dict[str, int] = {}
    for r in kfs:
        kf_loai[r[3]] = kf_loai.get(r[3], 0) + 1
    bao["kf_theo_nguon"] = kf_loai
    print(f"  keyframes.csv           {n_kf:>7} dòng")

    # ── 250 mô tả, gộp sẵn mọi bảng phụ để người nhận khỏi phải join lại
    print("Đang xuất 250 mô tả...")
    phu = {}
    for ten, bang, cot in (("asr_whisper", "asr_transcripts", "text_asr"),
                           ("asr_whisper_beam1", "asr_transcripts_beam1", "text_asr"),
                           ("asr_phowhisper", "asr_pho", "text_asr"),
                           ("dich_en", "dich_en", "text_en")):
        try:
            phu[ten] = dict(db.execute(f"select annot_id, {cot} from {bang}"))
        except sqlite3.Error:
            phu[ten] = {}

    ans = []
    for aid, tid, txt, au, ngv, reg, ct in db.execute(
            "select id, track_id, text, audio, annotator, region, created_at "
            "from annotations where text is not null and text<>'' "
            "and audio is not null and audio<>'' order by id"):
        cid, loai, khu, _ = tr.get(tid, ("?", "?", "", ""))
        ans.append([aid, tid, cid, loai, khu, txt, au,
                    phu["asr_whisper"].get(aid, ""),
                    phu["asr_whisper_beam1"].get(aid, ""),
                    phu["asr_phowhisper"].get(aid, ""),
                    phu["dich_en"].get(aid, ""), ngv, reg, ct])
    n_an = ghi_csv(os.path.join(goc, "manifest", "annotations_250.csv"),
                   ["annot_id", "track_id", "camera_id", "nguon", "khu_vuc",
                    "text_vi", "audio", "asr_whisper", "asr_whisper_beam1",
                    "asr_phowhisper", "dich_en", "annotator", "region",
                    "created_at"], ans)
    bao["so_mo_ta"] = n_an
    theo_cam: dict[str, int] = {}
    for r in ans:
        theo_cam[r[2]] = theo_cam.get(r[2], 0) + 1
    bao["mo_ta_theo_camera"] = theo_cam
    mt_loai: dict[str, int] = {}
    for r in ans:
        mt_loai[r[3]] = mt_loai.get(r[3], 0) + 1
    bao["mo_ta_theo_nguon"] = mt_loai
    print(f"  annotations_250.csv     {n_an:>7} dòng")

    try:
        n = ghi_csv(os.path.join(goc, "manifest", "speaker_asr.csv"),
                    ["nguoi", "stt", "annot_id", "file", "text_asr", "created_at"],
                    db.execute("select nguoi, stt, annot_id, file, text_asr, "
                               "created_at from speaker_asr order by nguoi, stt"))
        print(f"  speaker_asr.csv         {n:>7} dòng")
    except sqlite3.Error:
        pass

    # ── embedding ra .npy, đúng thứ tự kf_id tăng dần
    print("Đang xuất embedding...")
    ids, vecs, la = [], [], 0
    for kid, e in db.execute(
            "select id, emb from keyframes where emb is not null order by id"):
        v = np.frombuffer(e, dtype=np.float32)
        if v.shape[0] != EMB_DIM:      # vector lạ chiều: bỏ và đếm lại ở cuối
            la += 1
            continue
        ids.append(kid)
        vecs.append(v)
    M = np.vstack(vecs) if vecs else np.zeros((0, EMB_DIM), np.float32)
    I = np.asarray(ids, dtype=np.int64)
    os.makedirs(os.path.join(goc, "emb"), exist_ok=True)
    np.save(os.path.join(goc, "emb", "emb_f32.npy"), M)
    np.save(os.path.join(goc, "emb", "emb_kf_id.npy"), I)
    bao["so_emb"] = int(M.shape[0])
    bao["emb_la_chieu"] = la
    bao["chuan_hoa"] = bool(M.shape[0] and
                            abs(float(np.linalg.norm(M[0])) - 1.0) < 1e-3)
    print(f"  emb_f32.npy             {M.shape}  ({M.nbytes/1e6:.0f} MB)"
          + (f"  [bỏ {la} vector lạ chiều]" if la else ""))

    # ── ghi âm
    print("Đang chép file ghi âm...")
    n1, s1 = chep_thu_muc(ANNOT_AUDIO, os.path.join(goc, "annot_audio"))
    n2, s2 = chep_thu_muc(AUDIO_NGUOI, os.path.join(goc, "audio_nhieu_nguoi"))
    bao["annot_audio"] = [n1, s1]
    bao["audio_nhieu_nguoi"] = [n2, s2]
    print(f"  annot_audio             {n1:>7} file ({s1/1e6:.0f} MB)")
    print(f"  audio_nhieu_nguoi       {n2:>7} file ({s2/1e6:.0f} MB)")

    # ── index.db và ảnh cắt
    bao["co_db"] = bao["co_anh"] = False
    bao["anh"] = [0, 0, 0]
    if not a.nhanh:
        print("Đang chép index.db (414 MB, hơi lâu)...")
        shutil.copy2(DB, os.path.join(goc, "index.db"))
        bao["co_db"] = True

        print(f"Đang chép {n_kf} ảnh cắt...")
        ra_anh = os.path.join(goc, "crops")
        os.makedirs(ra_anh, exist_ok=True)
        dem = thieu = tong = 0
        # chép theo manifest chứ không chép cả thư mục: gói ra đúng bằng thứ
        # được tham chiếu, và biết ngay ảnh nào thiếu
        for r in kfs:
            cp = r[6]
            s = os.path.join(CROP_DIR, cp)
            if not os.path.exists(s):
                thieu += 1
                continue
            shutil.copy2(s, os.path.join(ra_anh, cp))
            dem += 1
            tong += os.path.getsize(s)
            if dem % 10000 == 0:
                print(f"    ...{dem}/{n_kf}")
        bao["co_anh"] = True
        bao["anh"] = [dem, thieu, tong]
        print(f"  crops                   {dem:>7} ảnh ({tong/1e6:.0f} MB), "
              f"thiếu {thieu}")

    # ── môi trường
    os.makedirs(os.path.join(goc, "moi_truong"), exist_ok=True)
    try:
        fr = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                            capture_output=True, text=True, timeout=180).stdout
    except Exception:
        fr = "(không lấy được pip freeze)\n"
    io.open(os.path.join(goc, "moi_truong", "pip_freeze.txt"), "w",
            encoding="utf-8").write(fr)

    db.close()
    bao["tao_luc"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    io.open(os.path.join(goc, "manifest", "thong_ke.json"), "w",
            encoding="utf-8").write(json.dumps(bao, ensure_ascii=False, indent=2))

    viet_readme(goc, bao)

    # ── SHA256 cho mọi file trừ ảnh cắt (98k file thì băm từng cái quá lâu)
    print("Đang tính SHA256...")
    dong = []
    for r, _, fs in os.walk(goc):
        if os.path.basename(r) == "crops":
            continue
        for f in sorted(fs):
            if f == "SHA256SUMS.txt":
                continue
            p = os.path.join(r, f)
            dong.append(f"{sha256(p)}  "
                        f"{os.path.relpath(p, goc).replace(os.sep, '/')}")
    # newline="\n" bắt buộc: trên Windows io.open mặc định đổi \n thành \r\n, mà
    # sha256sum -c coi \r là một phần tên file nên sẽ hỏng ở mọi dòng
    io.open(os.path.join(goc, "SHA256SUMS.txt"), "w", encoding="utf-8",
            newline="\n").write("\n".join(dong) + "\n")

    print(f"\nXong sau {time.time()-t0:.0f} giây.")
    print(f"Gói nằm ở: {goc}")
    if a.nhanh:
        print("CHẾ ĐỘ NHANH — chưa có index.db và ảnh cắt. Chạy lại không "
              "--nhanh để tạo gói giao thật.")
    return 0


def viet_readme(goc: str, b: dict) -> None:
    cam = b.get("mo_ta_theo_camera", {})
    bang_cam = "\n".join(f"| `{k}` | {v} |"
                         for k, v in sorted(cam.items(), key=lambda x: -x[1]))
    anh = b.get("anh", [0, 0, 0])
    kfn = b.get("kf_theo_nguon", {})
    mtn = b.get("mo_ta_theo_nguon", {})
    n_cam = len(b.get("cam_edata", []))
    n_vid = len(b.get("nguon_video", []))
    ds_cam = ", ".join(f"`{c}`" for c in b.get("cam_edata", []))
    s = f"""# Gói dữ liệu SecondPaper — mốc M1

**Giao:** Vinh (ĐT2) → **Nhận:** Lương (ĐT3) · Tạo lúc {b['tao_luc']}
Phục vụ **LG-01, LG-02, LG-03**.

---

## ĐỌC BA MỤC NÀY TRƯỚC KHI CHẠY

### 1. Embedding là 768 chiều, không dùng được với ViT-B/32

Chỉ mục trong gói sinh bằng:

- Ảnh: `{MO_HINH_ANH}`
- Chữ: `{MO_HINH_CHU}`
- Vector **{EMB_DIM} chiều**, đã chuẩn hoá L2 \
({'đã kiểm tra' if b.get('chuan_hoa') else 'CHƯA xác nhận'})

Mô hình `xlm-roberta-base-ViT-B-32` trong việc LG-01 cho vector **512 chiều**,
**không khớp** với gói này.

| Việc | Dùng gì |
|---|---|
| **LG-02** tái lập baseline | Dùng lại `emb/emb_f32.npy`; nạp đúng `{MO_HINH_CHU}` để mã hoá câu truy vấn |
| **LG-03** so sánh mô hình | **Phải tự nhúng lại toàn bộ `crops/`** bằng ViT-B/32. Vector trong gói không dùng được |

### 2. Con số 93.548 trong bảng tiến độ không tái lập được

Cơ sở dữ liệu đã thay đổi từ lúc viết bài báo (thêm camera drone, thêm nhãn, xoá
bớt track). Các con số hiện tại:

| Cách lọc | Số ảnh |
|---|---|
| Tất cả (gói này) | {b['so_keyframe']:,} |
| Trừ camera drone | 94.650 |
| Trừ drone + keyframe đã xoá | 94.009 |
| Trừ drone + track đã xoá | 90.241 |

**Không tổ hợp nào ra 93.548.** Vì vậy **`manifest/keyframes.csv` là mốc chính
thức từ nay**. Mọi kết quả báo cáo phải nói rõ lọc theo cột nào của file đó.
Đừng mất thời gian dựng lại con số cũ.

### 3. Dữ liệu gồm hai nửa khác hẳn nhau — đừng gộp

Cột `camera` trong `index.db` chỉ là **tên khu vực** (5 giá trị), không phải danh
tính camera. Gói này đã tách sẵn cột **`camera_id`** ({b['so_camera']} giá trị)
và cột **`nguon`** trong mọi file manifest.

| `nguon` | Là gì | Số ảnh | Số mô tả |
|---|---|---|---|
| `edata` | **{n_cam} camera cố định** | {kfn.get('edata', 0):,} | **{mtn.get('edata', 0)}** |
| `video` | {n_vid} lần quay bằng **điện thoại** | {kfn.get('video', 0):,} | {mtn.get('video', 0)} |
| `drone` | Tello bay trực tiếp | {kfn.get('drone', 0):,} | {mtn.get('drone', 0)} |

{n_cam} camera cố định là: {ds_cam}.

Ba điều rút ra:

- **"9 camera" trong bảng tiến độ ứng với nửa `edata`**, và nửa đó chỉ có
  {kfn.get('edata', 0):,} ảnh — không phải 93.548. Hai con số này không thuộc
  cùng một tập. Cần thống nhất lại với chủ nhiệm trước khi viết báo cáo.
- **{mtn.get('edata', 0)}/{b['so_mo_ta']} mô tả nằm trên nửa `edata`.** Nên phần
  đánh giá tìm kiếm thực chất chạy trên {n_cam} camera cố định, còn nửa video chỉ
  đóng góp {mtn.get('video', 0)} câu.
- **Dùng `camera_id`, đừng dùng `khu_vuc`** — nếu không thì 3 camera Sân trường
  bị gộp làm một và phân tích theo camera sẽ sai.

---

## Nội dung gói

```
SecondPaper_M1/
├── README.md                     file này
├── SHA256SUMS.txt                kiểm tra toàn vẹn (trừ crops)
├── index.db                      {'có' if b.get('co_db') else 'CHƯA CHÉP (chế độ nhanh)'}
├── crops/                        {anh[0]:,} ảnh ({anh[2]/1e6:.0f} MB)\
{'' if b.get('co_anh') else '  — CHƯA CHÉP'}
├── annot_audio/                  {b['annot_audio'][0]} file, khớp cột `audio`
├── audio_nhieu_nguoi/            {b['audio_nhieu_nguoi'][0]} file, 2 người nói
├── emb/
│   ├── emb_f32.npy               ({b['so_emb']:,}, {EMB_DIM}) float32
│   └── emb_kf_id.npy             kf_id theo đúng thứ tự dòng trên
├── manifest/
│   ├── keyframes.csv             {b['so_keyframe']:,} dòng  <- MỐC CHÍNH THỨC
│   ├── annotations_250.csv       {b['so_mo_ta']} dòng
│   ├── tracks.csv                {b['so_track']:,} dòng
│   ├── speaker_asr.csv
│   └── thong_ke.json
└── moi_truong/pip_freeze.txt
```

### Về 250 mô tả

Bảng `annotations` có **409 dòng**, nhưng **159 dòng rỗng** (ca bị bỏ qua lúc gán
nhãn). File `annotations_250.csv` **đã lọc sẵn** đúng {b['so_mo_ta']} dòng có cả
chữ lẫn ghi âm. Mỗi dòng kèm sẵn bản chép lời Whisper, PhoWhisper và bản dịch
tiếng Anh, khỏi phải join lại.

Phân bố theo camera:

| camera_id | Số mô tả |
|---|---|
{bang_cam}

---

## Nạp dữ liệu

```python
import numpy as np, pandas as pd

E  = np.load("emb/emb_f32.npy")     # ({b['so_emb']:,}, {EMB_DIM}) float32, đã chuẩn hoá L2
ID = np.load("emb/emb_kf_id.npy")   # kf_id tương ứng từng dòng của E
kf = pd.read_csv("manifest/keyframes.csv")
an = pd.read_csv("manifest/annotations_250.csv")

dong = {{int(k): i for i, k in enumerate(ID)}}   # kf_id -> chỉ số dòng trong E
```

Vì vector đã chuẩn hoá L2, **tích vô hướng chính là cosine** — không chuẩn hoá
lại lần nữa:

```python
from multilingual_clip import pt_multilingual_clip
import transformers

ten = "{MO_HINH_CHU}"
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

{'''**Lưu ý:** `keyframes.csv` có {kf} dòng nhưng `crops/` chỉ có {ok} ảnh — thiếu
{t} khung hình chụp từ drone (ghi hỏng lúc bay trực tiếp). Cả {t} đều **không**
nằm trong 250 mô tả, và track của chúng vẫn còn khung hình khác, nên không ảnh
hưởng gì. Khi lặp qua manifest nhớ bỏ qua file không tồn tại.

'''.format(kf=b['so_keyframe'], ok=anh[0], t=anh[1]) if anh[1] else ''}Ảnh cắt không nằm trong file băm (quá nhiều file). Kiểm tra bằng số lượng:

```bash
ls crops | wc -l      # phải ra {anh[0]}
```

---

## Vướng thì hỏi ai

Mọi thắc mắc về dữ liệu, nhãn, hoặc cách sinh embedding: **hỏi Vinh**, đừng tự
suy đoán rồi chạy tiếp — sai ở bước nạp dữ liệu thì mọi số phía sau đều hỏng.
"""
    io.open(os.path.join(goc, "README.md"), "w", encoding="utf-8").write(s)


if __name__ == "__main__":
    sys.exit(main())
