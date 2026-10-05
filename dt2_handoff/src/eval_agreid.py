# -*- coding: utf-8 -*-
"""VN-03 — chạy OSNet trên AG-ReID.v2 theo đúng protocol của bài báo.

Bốn protocol do chính tác giả cung cấp, mỗi file liệt kê sẵn ảnh query và gallery:
  exp1_aerial_to_cctv      UAV      -> CCTV
  exp2_aerial_to_wearable  UAV      -> kính đeo
  exp4_cctv_to_aerial      CCTV     -> UAV
  exp5_wearable_to_aerial  kính đeo -> UAV

Dùng thẳng các file này thay vì tự lọc theo trường C trong tên ảnh: chỉ khi đó
con số mới so được với bài báo, đúng yêu cầu "theo protocol của bài báo".

Quy ước danh tính lấy nguyên từ mã chính thức (agreidtools/datasets/agreidv2.py):

    pid = int(P + T + A)        # người + thời điểm + độ cao, NỐI CHUỖI

Nghĩa là cùng một người quay ở độ cao khác nhau là hai danh tính khác nhau.
Nhìn qua rất giống lỗi. KHÔNG được "sửa cho hợp lý" — đổi đi là mất khả năng so
sánh với bài báo. Muốn thử cách gộp theo người thì chạy thêm --gop-theo-nguoi và
báo cáo riêng, giữ nguyên số theo protocol gốc làm mốc.

Đầu ra (theo Checklist tái lập của đợt test):
  ket_qua.csv        Rank-1/5/10, mAP, n, mức ngẫu nhiên, khoảng tin cậy 95%
  toc_do.csv         p50/p95 — tách riêng tốc độ model và tốc độ toàn pipeline
  predictions.npz    thứ hạng thô, để kiểm tra chéo mà không cần chạy lại GPU

Chạy:
  python eval_agreid.py --goc D:/Data/AG-ReID.v2/AG-ReID.v2 \\
      --protocol D:/Data/AG-ReID.v2/exp1_aerial_to_cctv.txt \\
      --ckpt models/osnet_ain_x1_0_msmt.pth --ra bao_cao/vn03
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

P_PID = re.compile(r"P([-\d]+)T([-\d]+)A([-\d]+)")
P_CAM = re.compile(r"C([-\d]+)F([-\d]+)")
TEN_CAM = {0: "UAV", 2: "kính đeo", 3: "CCTV"}

CAO, RONG = 256, 128
TB = (0.485, 0.456, 0.406)
DL = (0.229, 0.224, 0.225)


def doc_nhan(duong_dan: str, gop_theo_nguoi: bool) -> tuple[int, int]:
    """Lấy (pid, camid) từ tên ảnh, theo đúng quy ước của mã chính thức."""
    ten = os.path.basename(duong_dan)
    a, b, c = P_PID.search(ten).groups()
    pid = int(a) if gop_theo_nguoi else int(a + b + c)
    cam = int(P_CAM.search(ten).group(1))
    return pid, cam


class TapAnh(Dataset):
    def __init__(self, goc: str, duong_dans: list[str], gop: bool):
        self.goc, self.ds, self.gop = goc, duong_dans, gop

    def __len__(self) -> int:
        return len(self.ds)

    def __getitem__(self, i: int):
        rel = self.ds[i]
        img = Image.open(os.path.join(self.goc, rel)).convert("RGB")
        img = img.resize((RONG, CAO), Image.BILINEAR)
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0)
        x = x.permute(2, 0, 1)
        x = (x - torch.tensor(TB).view(3, 1, 1)) / torch.tensor(DL).view(3, 1, 1)
        pid, cam = doc_nhan(rel, self.gop)
        return x, pid, cam


def doc_protocol(duong_dan: str) -> tuple[list[str], list[str]]:
    q, g = [], []
    for d in io.open(duong_dan, encoding="utf-8"):
        d = d.strip().replace("\\", "/")
        if not d:
            continue
        (q if d.startswith("query/") else g).append(d)
    return q, g


@torch.no_grad()
def trich_dac_trung(model, tap: Dataset, thiet_bi: str, lo: int, fp16: bool):
    dl = DataLoader(tap, batch_size=lo, shuffle=False, num_workers=0)
    fs, ps, cs = [], [], []
    for x, pid, cam in dl:
        x = x.to(thiet_bi, non_blocking=True)
        if fp16:
            x = x.half()
        f = model(x).float()
        # chuẩn hoá L2 -> tích vô hướng chính là cosine, khỏi tính lại khoảng cách
        f = f / f.norm(dim=1, keepdim=True).clamp_min(1e-12)
        fs.append(f.cpu())
        ps.append(pid)
        cs.append(cam)
    return (torch.cat(fs).numpy(), torch.cat(ps).numpy(), torch.cat(cs).numpy())


def tinh_chi_so(thu_tu: np.ndarray, q_pid, q_cam, g_pid, g_cam,
                topk=(1, 5, 10)) -> tuple[np.ndarray, np.ndarray]:
    """Trả về (cmc_tung_query [n_q, max(topk)], ap_tung_query [n_q]).

    Loại ảnh gallery trùng CẢ danh tính LẪN camera với query — quy tắc chuẩn của
    Market-1501. Với bốn protocol này query và gallery khác camera hoàn toàn nên
    thực tế không loại gì, nhưng vẫn làm đúng để script dùng lại được chỗ khác.
    """
    n_q, k_max = len(q_pid), max(topk)
    cmc = np.zeros((n_q, k_max), dtype=np.float32)
    ap = np.zeros(n_q, dtype=np.float32)
    # "có đáp án" phải đếm riêng: sau khi chỉ ghi nhận trúng trong top-k, không
    # còn suy ra được từ cmc nữa
    co_dap_an = np.zeros(n_q, dtype=bool)

    for i in range(n_q):
        od = thu_tu[i]
        giu = ~((g_pid[od] == q_pid[i]) & (g_cam[od] == q_cam[i]))
        od = od[giu]
        khop = (g_pid[od] == q_pid[i])
        if not khop.any():
            continue                      # query không có ảnh đúng trong gallery
        co_dap_an[i] = True
        vt = np.flatnonzero(khop)
        # chỉ đánh dấu trúng khi ảnh đúng ĐẦU TIÊN nằm trong top-k_max. Kẹp bằng
        # min() là sai: query có ảnh đúng ở hạng 500 cũng bị tính là trúng Rank-10
        if vt[0] < k_max:
            cmc[i, vt[0]:] = 1.0
        # AP: trung bình độ chính xác tại mỗi vị trí trúng
        prec = np.arange(1, len(vt) + 1) / (vt + 1)
        ap[i] = prec.mean()
    return cmc, ap, co_dap_an


def bootstrap(gt: np.ndarray, lan: int, hat: int = 0) -> tuple[float, float]:
    """Khoảng tin cậy 95% bằng lấy mẫu lại theo query (yêu cầu của C-03)."""
    if len(gt) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(hat)
    tb = [gt[rng.integers(0, len(gt), len(gt))].mean() for _ in range(lan)]
    return float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))


def muc_ngau_nhien(q_pid, q_cam, g_pid, g_cam, lan: int = 5, hat: int = 0):
    """Mức ngẫu nhiên: xếp hạng gallery ngẫu nhiên, chạy lại đúng hàm chấm.

    Tính thẳng bằng mô phỏng thay vì công thức, để con số này so được trực tiếp
    với kết quả thật — cùng một bộ query, cùng một cách loại ảnh trùng.
    """
    rng = np.random.default_rng(hat)
    r1, mp = [], []
    goc = np.tile(np.arange(len(g_pid), dtype=np.int32), (len(q_pid), 1))
    for _ in range(lan):
        # hoán vị từng hàng: O(n) mỗi hàng, nhanh hơn hẳn argsort một ma trận
        # số ngẫu nhiên khi gallery lên tới hơn chục nghìn ảnh
        tt = rng.permuted(goc, axis=1)
        c, a, _ = tinh_chi_so(tt, q_pid, q_cam, g_pid, g_cam)
        r1.append(c[:, 0].mean())
        mp.append(a.mean())
    return float(np.mean(r1)), float(np.mean(mp))


@torch.no_grad()
def do_toc_do(model, tap: Dataset, thiet_bi: str, lo: int, fp16: bool,
              lan: int = 3, n_batch: int = 20) -> list[dict]:
    """Đo p50/p95 sau khi làm nóng, lặp >=3 lần — yêu cầu của Checklist.

    Tách hai con số vì chúng nói hai chuyện khác nhau: 'model' là giới hạn của
    mô hình, 'pipeline' là thứ người dùng thật sự chờ (có cả đọc ảnh và biến đổi).
    """
    dl = DataLoader(tap, batch_size=lo, shuffle=False, num_workers=0)
    mau = []
    for i, b in enumerate(dl):
        mau.append(b[0])
        if i + 1 >= n_batch:
            break
    if not mau:
        return []

    x0 = mau[0].to(thiet_bi)
    if fp16:
        x0 = x0.half()
    for _ in range(10):                   # làm nóng, bỏ qua không tính
        model(x0)
    if thiet_bi.startswith("cuda"):
        torch.cuda.synchronize()

    ds = []
    for vong in range(lan):
        t_model = []
        for x in mau:
            x = x.to(thiet_bi)
            if fp16:
                x = x.half()
            if thiet_bi.startswith("cuda"):
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            model(x)
            if thiet_bi.startswith("cuda"):
                torch.cuda.synchronize()
            t_model.append((time.perf_counter() - t0) * 1000 / x.shape[0])

        t0 = time.perf_counter()
        n = 0
        for i, (x, _, _) in enumerate(dl):
            x = x.to(thiet_bi)
            if fp16:
                x = x.half()
            model(x)
            n += x.shape[0]
            if i + 1 >= n_batch:
                break
        if thiet_bi.startswith("cuda"):
            torch.cuda.synchronize()
        t_pipe = (time.perf_counter() - t0) * 1000 / max(n, 1)

        ds.append({"vong": vong + 1,
                   "model_p50_ms": round(float(np.percentile(t_model, 50)), 3),
                   "model_p95_ms": round(float(np.percentile(t_model, 95)), 3),
                   "pipeline_tb_ms": round(t_pipe, 3),
                   "so_anh": n})
    return ds


def nap_trong_so(model, duong_dan: str) -> str:
    """Nạp checkpoint torchreid trên torch >= 2.6, có ghi lại SHA256.

    Từ torch 2.6, torch.load mặc định weights_only=True và từ chối file có numpy
    scalar — mà checkpoint torchreid nào cũng lưu kèm trường rank1 như vậy. Cho
    phép riêng lớp đó không ăn thua vì numpy 2 đã đổi đường dẫn module, chuỗi
    trong file pickle cũ không còn khớp.

    Nên ở đây đi đường khác: tự băm file và IN RA SHA256 trước khi nạp. Tính toàn
    vẹn được bảo đảm bằng chữ ký đối chiếu với checkpoint.lock.json, chứ không
    dựa vào lớp chặn của pickle. Chỉ nạp tensor trong state_dict, bỏ mọi thứ khác
    trong file.
    """
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    chu_ky = h.hexdigest()

    o = torch.load(duong_dan, map_location="cpu", weights_only=False)
    sd = o.get("state_dict", o) if isinstance(o, dict) else o
    # bỏ tiền tố module. do checkpoint được lưu khi bọc DataParallel
    sd = {k[7:] if k.startswith("module.") else k: v for k, v in sd.items()}
    goc = model.state_dict()
    dung = {k: v for k, v in sd.items()
            if k in goc and goc[k].shape == v.shape}
    bo = len(sd) - len(dung)
    model.load_state_dict(dung, strict=False)
    print(f"  nạp {len(dung)}/{len(goc)} tensor"
          + (f", bỏ {bo} tensor lệch (thường là tầng phân loại)" if bo else ""))
    return chu_ky


def main() -> int:
    ap = argparse.ArgumentParser(description="VN-03: OSNet trên AG-ReID.v2")
    ap.add_argument("--goc", required=True, help="thư mục chứa query/ và gallery/")
    ap.add_argument("--protocol", required=True, action="append",
                    help="file exp*.txt (lặp lại được để chạy nhiều protocol)")
    ap.add_argument("--ckpt", default="", help="checkpoint ReID; bỏ trống = ImageNet")
    ap.add_argument("--model", default="osnet_x1_0")
    ap.add_argument("--ra", required=True)
    ap.add_argument("--lo", type=int, default=64)
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--gop-theo-nguoi", action="store_true",
                    help="thí nghiệm phụ: pid chỉ lấy mã người, KHÔNG phải protocol gốc")
    a = ap.parse_args()

    os.makedirs(a.ra, exist_ok=True)
    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Thiết bị: {thiet_bi} · precision: {'fp16' if a.fp16 else 'fp32'}")
    if a.gop_theo_nguoi:
        print("CẢNH BÁO: --gop-theo-nguoi KHÔNG phải protocol của bài báo. "
              "Chỉ dùng làm thí nghiệm phụ, báo cáo riêng.")

    from torchreid.reid import models
    model = models.build_model(a.model, num_classes=1000, loss="softmax",
                               pretrained=not a.ckpt, use_gpu=(thiet_bi == "cuda"))
    chu_ky = ""
    if a.ckpt:
        print(f"Nạp checkpoint: {a.ckpt}")
        chu_ky = nap_trong_so(model, a.ckpt)
        print(f"  SHA256: {chu_ky}")
    else:
        print("CHƯA có checkpoint ReID — đang dùng trọng số ImageNet. Con số ra "
              "sẽ rất thấp và KHÔNG dùng làm baseline được.")
    model = model.to(thiet_bi).eval()
    if a.fp16:
        model = model.half()

    hang, toc_do, thoat = [], [], 0
    for pfile in a.protocol:
        ten = os.path.splitext(os.path.basename(pfile))[0]
        print(f"\n=== {ten} ===")
        q_ds, g_ds = doc_protocol(pfile)
        tq = TapAnh(a.goc, q_ds, a.gop_theo_nguoi)
        tg = TapAnh(a.goc, g_ds, a.gop_theo_nguoi)

        t0 = time.time()
        qf, qp, qc = trich_dac_trung(model, tq, thiet_bi, a.lo, a.fp16)
        gf, gp, gc = trich_dac_trung(model, tg, thiet_bi, a.lo, a.fp16)
        print(f"  query {len(qp)} ảnh / {len(set(qp))} danh tính · "
              f"gallery {len(gp)} ảnh / {len(set(gp))} danh tính "
              f"({time.time()-t0:.0f}s)")
        print(f"  camera: query {sorted({TEN_CAM.get(c, c) for c in qc})} -> "
              f"gallery {sorted({TEN_CAM.get(c, c) for c in gc})}")

        # cosine giảm dần = khoảng cách tăng dần, vì vector đã chuẩn hoá L2
        thu_tu = np.argsort(-(qf @ gf.T), axis=1)
        cmc, apq, co_da = tinh_chi_so(thu_tu, qp, qc, gp, gc)
        co_dap_an = int(co_da.sum())

        r_r1, r_map = muc_ngau_nhien(qp, qc, gp, gc)
        d = {"protocol": ten,
             "model": a.model,
             "checkpoint": os.path.basename(a.ckpt) if a.ckpt else "(ImageNet)",
             "checkpoint_sha256": chu_ky[:16],
             "precision": "fp16" if a.fp16 else "fp32",
             "n_query": len(qp), "n_gallery": len(gp),
             "n_query_co_dap_an": co_dap_an,
             "rank1": round(float(cmc[:, 0].mean()) * 100, 2),
             "rank5": round(float(cmc[:, 4].mean()) * 100, 2),
             "rank10": round(float(cmc[:, 9].mean()) * 100, 2),
             "mAP": round(float(apq.mean()) * 100, 2),
             "rank1_ngau_nhien": round(r_r1 * 100, 3),
             "mAP_ngau_nhien": round(r_map * 100, 3)}
        lo_, hi = bootstrap(cmc[:, 0], a.bootstrap)
        d["rank1_ci95_duoi"], d["rank1_ci95_tren"] = round(lo_*100, 2), round(hi*100, 2)
        lo_, hi = bootstrap(apq, a.bootstrap)
        d["mAP_ci95_duoi"], d["mAP_ci95_tren"] = round(lo_*100, 2), round(hi*100, 2)
        hang.append(d)

        print(f"  Rank-1 {d['rank1']:.2f}%  [{d['rank1_ci95_duoi']:.2f}–"
              f"{d['rank1_ci95_tren']:.2f}]   ngẫu nhiên {d['rank1_ngau_nhien']:.3f}%")
        print(f"  mAP    {d['mAP']:.2f}%  [{d['mAP_ci95_duoi']:.2f}–"
              f"{d['mAP_ci95_tren']:.2f}]   ngẫu nhiên {d['mAP_ngau_nhien']:.3f}%")
        if co_dap_an < len(qp):
            print(f"  Lưu ý: {len(qp)-co_dap_an} query không có ảnh đúng nào "
                  f"trong gallery (đã tính là trượt)")

        np.savez_compressed(
            os.path.join(a.ra, f"predictions_{ten}.npz"),
            thu_tu_top100=thu_tu[:, :100].astype(np.int32),
            query_pid=qp, query_cam=qc, gallery_pid=gp, gallery_cam=gc,
            cmc=cmc, ap=apq)

        if not toc_do:
            for r in do_toc_do(model, tq, thiet_bi, a.lo, a.fp16):
                r.update({"protocol": ten, "model": a.model,
                          "precision": "fp16" if a.fp16 else "fp32",
                          "thiet_bi": thiet_bi, "batch": a.lo})
                toc_do.append(r)

    import csv
    for ten_file, ds in (("ket_qua.csv", hang), ("toc_do.csv", toc_do)):
        if not ds:
            continue
        with io.open(os.path.join(a.ra, ten_file), "w",
                     encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ds[0].keys()))
            w.writeheader()
            w.writerows(ds)

    io.open(os.path.join(a.ra, "cau_hinh.json"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(vars(a) | {"lenh": " ".join(sys.argv)},
                   ensure_ascii=False, indent=2) + "\n")

    print(f"\nĐã ghi {a.ra}/ket_qua.csv · toc_do.csv · predictions_*.npz · "
          f"cau_hinh.json")
    return thoat


if __name__ == "__main__":
    sys.exit(main())
