# -*- coding: utf-8 -*-
"""VN-07 + VN-08 — MÔ PHỎNG pilot bàn giao trên AG-ReID.v2.

Vì sao mô phỏng: hai phiên pilot trong khuôn viên trường chưa quay được (M5, M6
trễ). AG-ReID.v2 có đúng cấu trúc mà pilot cần — nhiều buổi quay khác ngày, cùng
một người được thấy từ camera mặt đất và từ UAV — nên dựng lại được cả thiết kế
pilot trên đó. Kết quả là của AG-ReID.v2, KHÔNG phải của khuôn viên trường, và
phải báo cáo riêng như vậy (mục 4.7 README).

Thiết kế, chốt trước khi chạy:

  Phiên     chia theo NGÀY quay (trường T = MMDD + buổi). Các ngày sớm nhất vào
            phiên 1 cho tới khi đủ ~50% truy vấn, còn lại là phiên 2. Mỗi phiên
            dùng gallery UAV của riêng nó, như một đợt triển khai thật.
  A         ngoại hình-only: ứng viên là mọi ảnh UAV trong phiên
  B         ngoại hình + giới hạn thời gian: chỉ ứng viên cùng buổi quay
  Vắng mặt  mỗi truy vấn có thêm một bản sao đã xoá người đúng khỏi ứng viên;
            khi đó mọi lần chấp nhận bàn giao đều là sai
  Giống áo  truy vấn mà ứng viên có người KHÁC trùng loại áo, quần, túi và màu
            tóc (thuộc tính chính thức của AG-ReID.v2)
  Ngưỡng τ  nhỏ nhất sao cho tỉ lệ chấp nhận nhầm khi vắng mặt <= 10% trên
            PHIÊN 1. Khoá cố định, áp nguyên cho phiên 2.
  Quyết định điểm cosine cao nhất >= τ -> bàn giao cho người đó; ngược lại từ chối

Chạy:
  python dt2_handoff/src/vn07_vn08_ban_giao.py --goc D:/Data/AG-ReID.v2
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from datetime import date

import numpy as np

DT2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ID = "VN0708-mo-phong-agreid-20261010"
COT = ["run_id", "date", "commit", "task_id", "dataset", "split", "model",
       "checkpoint_sha256", "precision", "metric", "value", "ci95_low",
       "ci95_high", "n", "chance_level", "hardware", "notes"]
PROT = {"exp4_cctv_to_aerial": "CCTV → UAV",
        "exp5_wearable_to_aerial": "kính đeo → UAV"}
NHOM_TT = ("upper", "lower", "bag", "haircolor")      # nhóm thuộc tính "giống áo"
FAR_MUC_TIEU = 0.10


def nap_eval():
    sp = importlib.util.spec_from_file_location(
        "eval_agreid", os.path.join(DT2, "src", "eval_agreid.py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def giai_ma(pid):
    pid = np.asarray(pid, dtype=np.int64)
    return pid // 1000000, (pid // 10) % 100000, pid % 10      # P, T, A


def bootstrap(x, n=1000, hat=0):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(hat)
    tb = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return float(x.mean()), float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))


def bootstrap_cap(a, b, n=1000, hat=0):
    d = np.asarray(a, float) - np.asarray(b, float)
    return bootstrap(d, n, hat)


def chu_ky_trang_phuc(goc: str) -> dict[int, tuple]:
    """pid -> (loại áo, loại quần, túi, màu tóc). Mỗi nhóm là one-hot trong .mat."""
    import mat4py
    import pandas as pd
    m = mat4py.loadmat(os.path.join(goc, "qut_attribute_v8.mat"))["qut_attribute"]
    ds = {}
    for phan in ("train", "test"):
        d = pd.DataFrame(m[phan], index=m[phan]["image_index"]).drop(columns=["image_index"])
        for nhom in NHOM_TT:
            cot = [c for c in d.columns if c.startswith(nhom)]
            d["_" + nhom] = d[cot].values.argmax(axis=1)   # giá trị 2 = có
        for idx, r in d.iterrows():
            ds[int(idx)] = tuple(int(r["_" + g]) for g in NHOM_TT)
    return ds


def chia_phien(T_query: np.ndarray) -> tuple[set, set, list]:
    """Ngày sớm vào phiên 1 tới khi đủ ~50% truy vấn. Trả về (ngày p1, ngày p2, manifest)."""
    ngay = T_query // 10                      # MMDD
    ds = sorted(set(ngay.tolist()))
    dem = {d_: int((ngay == d_).sum()) for d_ in ds}
    p1, cong = set(), 0
    for d_ in ds:
        if cong >= 0.5 * len(T_query):
            break
        p1.add(d_)
        cong += dem[d_]
    p2 = set(ds) - p1
    man = [{"ngay_MMDD": f"{d_:04d}", "phien": 1 if d_ in p1 else 2,
            "so_truy_van": dem[d_]} for d_ in ds]
    return p1, p2, man


def cham_mot_phien(qf, qpid, gf, gpid, chu_ky, dung_T: bool):
    """Mỗi truy vấn -> điểm và người dự đoán khi CÓ MẶT, điểm khi VẮNG MẶT, cờ giống áo."""
    _, Tq, _ = giai_ma(qpid)
    _, Tg, _ = giai_ma(gpid)
    S = qf @ gf.T                                          # cosine, đã chuẩn hoá L2
    n = len(qpid)
    out = {k: np.zeros(n) for k in ("s_co", "dung", "s_vang", "giong_ao", "n_ung_vien")}
    out["pid_du_doan"] = np.zeros(n, dtype=np.int64)
    out["g_chon"] = np.zeros(n, dtype=np.int64)
    for i in range(n):
        ung = (Tg == Tq[i]) if dung_T else np.ones(len(gpid), bool)
        idx = np.flatnonzero(ung)
        s = S[i, idx]
        j = int(np.argmax(s))
        out["s_co"][i] = s[j]
        out["pid_du_doan"][i] = gpid[idx[j]]
        out["g_chon"][i] = idx[j]
        out["dung"][i] = float(gpid[idx[j]] == qpid[i])
        khac = gpid[idx] != qpid[i]
        out["s_vang"][i] = s[khac].max() if khac.any() else -1.0
        ck = chu_ky.get(int(qpid[i]))
        nguoi_khac = set(gpid[idx][khac].tolist())
        out["giong_ao"][i] = float(ck is not None and
                                   any(chu_ky.get(int(p)) == ck for p in nguoi_khac))
        out["n_ung_vien"][i] = len(idx)
    return out


def quyet_dinh(o, tau):
    nhan = o["s_co"] >= tau
    return {"dung": (nhan & (o["dung"] == 1)).astype(float),
            "sai": (nhan & (o["dung"] == 0)).astype(float),
            "tu_choi": (~nhan).astype(float),
            "nhan_nham_vang": (o["s_vang"] >= tau).astype(float)}


def commit_hien_tai():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DT2,
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="VN-07/08: mô phỏng pilot bàn giao")
    ap.add_argument("--goc", required=True, help="thư mục có exp*.txt và AG-ReID.v2/")
    ap.add_argument("--ckpt", default="E:/RTCN/models/osnet_ain_x1_0_dangguon_msdc.pth")
    ap.add_argument("--model", default="osnet_ain_x1_0")
    ap.add_argument("--lo", type=int, default=64)
    a = ap.parse_args()

    import torch
    ev = nap_eval()
    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    from torchreid.reid import models
    model = models.build_model(a.model, num_classes=1000, loss="softmax",
                               pretrained=False, use_gpu=(thiet_bi == "cuda"))
    sha = ev.nap_trong_so(model, a.ckpt)
    model = model.to(thiet_bi).eval()
    anh_goc = os.path.join(a.goc, "AG-ReID.v2")

    ra_pred = os.path.join(DT2, "predictions", RUN_ID)
    os.makedirs(ra_pred, exist_ok=True)
    chu_ky = chu_ky_trang_phuc(a.goc)
    print(f"Thuộc tính trang phục: {len(chu_ky)} danh tính · thiết bị {thiet_bi}")

    hang, m9, tong = [], [], {}
    meta = dict(run_id=RUN_ID, date=date.today().isoformat(), commit=commit_hien_tai(),
                dataset="AG-ReID.v2 (mo phong pilot)", model="osnet_ain_x1_0_dangguon",
                checkpoint_sha256=sha[:16], precision="fp32",
                hardware="RTX 3060 Laptop 6GB")

    def ghi(split, task, metric, v, lo, hi, n, notes="", chance=""):
        hang.append(dict(meta, task_id=task, split=split, metric=metric,
                         value=round(v * 100, 4) if v == v else "",
                         ci95_low=round(lo * 100, 4) if lo == lo else "",
                         ci95_high=round(hi * 100, 4) if hi == hi else "",
                         n=n, chance_level=chance, notes=notes))

    for ten, nhan in PROT.items():
        q, g = ev.doc_protocol(os.path.join(a.goc, ten + ".txt"))
        t0 = time.time()
        qf, qpid, _ = ev.trich_dac_trung(model, ev.TapAnh(anh_goc, q, False), thiet_bi, a.lo, False)
        gf, gpid, _ = ev.trich_dac_trung(model, ev.TapAnh(anh_goc, g, False), thiet_bi, a.lo, False)
        print(f"\n=== {nhan}: {len(q)} truy vấn, {len(g)} ảnh UAV ({time.time()-t0:.0f}s)")

        _, Tq, Aq = giai_ma(qpid)
        _, Tg, _ = giai_ma(gpid)
        p1, p2, man = chia_phien(Tq)
        with io.open(os.path.join(ra_pred, f"split_manifest_{ten}.csv"), "w",
                     encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(man[0].keys()))
            w.writeheader()
            w.writerows(man)
        print(f"  phiên 1: ngày {sorted(p1)}  ·  phiên 2: ngày {sorted(p2)}")

        kq = {}
        for phien, ngay in ((1, p1), (2, p2)):
            mq = np.isin(Tq // 10, list(ngay))
            mg = np.isin(Tg // 10, list(ngay))
            for dk, dung_T in (("A", False), ("B", True)):
                kq[(phien, dk)] = cham_mot_phien(qf[mq], qpid[mq], gf[mg], gpid[mg],
                                                 chu_ky, dung_T)
                kq[(phien, dk)]["q_idx"] = np.flatnonzero(mq)
                kq[(phien, dk)]["g_idx_goc"] = np.flatnonzero(mg)

        for dk in ("A", "B"):
            o1 = kq[(1, dk)]
            # τ nhỏ nhất để chấp nhận nhầm khi vắng mặt <= 10% trên phiên 1
            tau = float(np.quantile(o1["s_vang"], 1 - FAR_MUC_TIEU))
            tong[(ten, dk)] = {"tau": tau}
            ten_dk = "ngoai hinh" if dk == "A" else "ngoai hinh + cung buoi"
            for phien in (1, 2):
                o = kq[(phien, dk)]
                qd = quyet_dinh(o, tau)
                vai = "VN-07" if phien == 1 else "VN-08"
                sp = f"{ten}_phien{phien}_{dk}"
                n = len(o["s_co"])
                r1 = bootstrap(o["dung"])
                ghi(sp, vai, "Rank1_khong_nguong", *r1, n, ten_dk,
                    chance=round(float(np.mean(1.0 / o["n_ung_vien"])) * 100, 4))
                for k in ("dung", "sai", "tu_choi"):
                    ghi(sp, vai, f"ban_giao_{k}", *bootstrap(qd[k]), n,
                        f"{ten_dk}; tau={tau:.4f} chot tren phien 1")
                ghi(sp, vai, "nhan_nham_khi_vang_mat", *bootstrap(qd["nhan_nham_vang"]), n,
                    f"{ten_dk}; muc tieu chon nguong <=10% tren phien 1")
                nhan_ = qd["dung"] + qd["sai"]
                prec = qd["dung"][nhan_ == 1]
                ghi(sp, vai, "do_chinh_xac_khi_ban_giao", *bootstrap(prec), int(nhan_.sum()),
                    "ti le dung trong so ca da ban giao (truong hop co mat)")
                hk = o["giong_ao"] == 1
                ghi(sp, vai, "ban_giao_dung_ca_giong_ao", *bootstrap(qd["dung"][hk]),
                    int(hk.sum()), "co nguoi khac trung loai ao, quan, tui, mau toc")
                ghi(sp, vai, "ban_giao_sai_ca_giong_ao", *bootstrap(qd["sai"][hk]), int(hk.sum()))
                tong[(ten, dk)][phien] = {
                    "n": n, "r1": r1[0], "dung": qd["dung"].mean(), "sai": qd["sai"].mean(),
                    "tu_choi": qd["tu_choi"].mean(), "far": qd["nhan_nham_vang"].mean(),
                    "prec": float(prec.mean()) if len(prec) else float("nan"),
                    "n_giong": int(hk.sum()), "dung_giong": float(qd["dung"][hk].mean()) if hk.any() else float("nan"),
                    "sai_giong": float(qd["sai"][hk].mean()) if hk.any() else float("nan"),
                    "ung_vien_tb": float(o["n_ung_vien"].mean())}
                print(f"  [{dk}] phiên {phien}: n={n}  Rank-1 {r1[0]*100:5.2f}%  ·  "
                      f"đúng {qd['dung'].mean()*100:5.2f}  sai {qd['sai'].mean()*100:5.2f}  "
                      f"từ chối {qd['tu_choi'].mean()*100:5.2f}  ·  nhận nhầm khi vắng "
                      f"{qd['nhan_nham_vang'].mean()*100:5.2f}%  (τ={tau:.3f})")

                # dự đoán thô cho kiểm tra chéo (M10)
                with io.open(os.path.join(ra_pred, f"predictions_{sp}.csv"), "w",
                             encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["truy_van", "pid_that", "pid_du_doan", "anh_uav_chon",
                                "diem_co_mat", "diem_vang_mat", "nguong", "quyet_dinh",
                                "ket_qua", "giong_ao", "so_ung_vien"])
                    for i in range(n):
                        qi = o["q_idx"][i]
                        gi = o["g_idx_goc"][o["g_chon"][i]]
                        quyet = "ban_giao" if o["s_co"][i] >= tau else "tu_choi"
                        kq_ = ("tu_choi" if quyet == "tu_choi" else
                               "dung" if o["dung"][i] == 1 else "sai")
                        w.writerow([q[qi], int(qpid[qi]), int(o["pid_du_doan"][i]), g[gi],
                                    round(float(o["s_co"][i]), 5), round(float(o["s_vang"][i]), 5),
                                    round(tau, 5), quyet, kq_, int(o["giong_ao"][i]),
                                    int(o["n_ung_vien"][i])])

                # M9: mục tiêu đã xác minh, chỉ lấy phiên 2, điều kiện B, chiều chính
                if phien == 2 and dk == "B" and ten == "exp4_cctv_to_aerial":
                    for i in np.flatnonzero(o["s_co"] >= tau):
                        qi = o["q_idx"][i]
                        p_du = int(o["pid_du_doan"][i])
                        mg_ = o["g_idx_goc"]
                        cung = [g[x] for x in mg_ if gpid[x] == p_du][:5]
                        _, T_, A_ = giai_ma(np.array([qpid[qi]]))
                        m9.append({
                            "ma_ban_giao": f"BG-{len(m9)+1:04d}",
                            "anh_truy_van_mat_dat": q[qi],
                            "ma_muc_tieu": p_du,
                            "anh_mau_muc_tieu_uav": cung,
                            "do_tin": round(float(o["s_co"][i]), 4),
                            "nguong": round(tau, 4),
                            "buoi_quay_T": int(T_[0]), "do_cao_A": int(A_[0]),
                            "ket_qua_that_chi_de_danh_gia": "dung" if o["dung"][i] == 1 else "sai",
                        })

        # so sánh cặp A với B trên CÙNG truy vấn phiên 2 (mục 4.2 README)
        oA, oB = kq[(2, "A")], kq[(2, "B")]
        qdA = quyet_dinh(oA, tong[(ten, "A")]["tau"])
        qdB = quyet_dinh(oB, tong[(ten, "B")]["tau"])
        h = bootstrap_cap(qdB["dung"], qdA["dung"])
        ghi(f"{ten}_phien2", "VN-08", "ban_giao_dung_B_tru_A_cap", *h, len(oA["s_co"]),
            "so sanh cap cung truy van: (ngoai hinh + cung buoi) - (ngoai hinh)", chance=0)
        hs = bootstrap_cap(qdB["sai"], qdA["sai"])
        ghi(f"{ten}_phien2", "VN-08", "ban_giao_sai_B_tru_A_cap", *hs, len(oA["s_co"]),
            "so sanh cap cung truy van", chance=0)
        tong[(ten, "cap")] = {"dung": h, "sai": hs}
        print(f"  So sánh cặp phiên 2 (B − A): bàn giao đúng {h[0]*100:+.2f} "
              f"[{h[1]*100:+.2f} – {h[2]*100:+.2f}] · bàn giao sai {hs[0]*100:+.2f} "
              f"[{hs[1]*100:+.2f} – {hs[2]*100:+.2f}]")

    met = os.path.join(DT2, "metrics", f"{RUN_ID}.csv")
    with io.open(met, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COT)
        w.writeheader()
        w.writerows(hang)
    m9_ra = os.path.join(DT2, "handoff_M9")
    os.makedirs(m9_ra, exist_ok=True)
    io.open(os.path.join(m9_ra, "muc_tieu_xac_minh.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(m9, ensure_ascii=False, indent=1) + "\n")
    io.open(os.path.join(ra_pred, "_tom_tat.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(
                {f"{k[0]}|{k[1]}": v for k, v in tong.items()}, ensure_ascii=False,
                indent=1, default=float) + "\n")
    io.open(os.path.join(DT2, "configs", f"{RUN_ID}.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(
                vars(a) | {"lenh": " ".join(sys.argv), "far_muc_tieu": FAR_MUC_TIEU,
                           "nhom_thuoc_tinh_giong_ao": NHOM_TT,
                           "quy_tac_chia_phien": "ngay som -> phien 1 toi khi du 50% truy van",
                           "checkpoint_sha256": sha}, ensure_ascii=False, indent=2) + "\n")
    print(f"\nĐã ghi {len(hang)} dòng metrics -> {met}")
    print(f"M9: {len(m9)} mục tiêu đã xác minh -> {m9_ra}/muc_tieu_xac_minh.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
