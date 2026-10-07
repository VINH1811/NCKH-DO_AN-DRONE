# -*- coding: utf-8 -*-
"""VN-04 — phân tích lỗi ReID theo góc nhìn trên AG-ReID.v2.

Đọc lại dự đoán thô của VN-03 (predictions/*.npz), không chạy lại GPU. Bốn phân
tích, mỗi cái trả lời một câu hỏi cho bài toán bàn giao camera sang drone:

  1. Theo ĐỘ CAO BAY (trường A: 0 thấp, 1 vừa, 2 cao)
     Drone bay càng cao thì khớp càng kém tới mức nào?

  2. Theo KÍCH THƯỚC NGƯỜI TRONG ẢNH UAV
     Độ cao làm hại qua cơ chế nào — có phải vì người nhỏ lại, mất chi tiết?

  3. PHÂN LOẠI LỖI Rank-1
     Khi sai thì sai kiểu gì: nhầm người khác cùng cảnh, nhầm hẳn, hay thật ra
     đã tìm đúng người mà protocol tính là sai?

  4. Rank-1 THEO NGƯỜI (thí nghiệm phụ, KHÔNG thay con số chính thức)
     Protocol coi danh tính là bộ ba (người, thời điểm, độ cao). Bàn giao drone
     thì chỉ cần đúng người. Hai con số chênh nhau bao nhiêu?

Giải mã danh tính: mã chính thức tính pid = int(P + T + A) bằng nối chuỗi, với P
4 chữ số, T 5 chữ số, A 1 chữ số. Nên giải ngược được:
    A = pid % 10,  T = (pid // 10) % 100000,  P = pid // 1000000
Đã đối chiếu với tên file trong protocol: khớp 2.356/2.356 ở exp1.

Chạy:
  python dt2_handoff/src/vn04_phan_tich_loi.py \\
      --pred dt2_handoff/predictions/VN03-ain-20261004 \\
      --anh D:/Data/AG-ReID.v2/AG-ReID.v2 --protocol-dir D:/Data/AG-ReID.v2
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
from datetime import date

import numpy as np

PROTOCOL = {
    "exp1_aerial_to_cctv": "UAV → CCTV",
    "exp2_aerial_to_wearable": "UAV → kính đeo",
    "exp4_cctv_to_aerial": "CCTV → UAV",
    "exp5_wearable_to_aerial": "kính đeo → UAV",
}
TEN_A = {0: "thấp", 1: "vừa", 2: "cao"}
COT = ["run_id", "date", "commit", "task_id", "dataset", "split", "model",
       "checkpoint_sha256", "precision", "metric", "value", "ci95_low",
       "ci95_high", "n", "chance_level", "hardware", "notes"]


def giai_ma(pid: np.ndarray):
    pid = pid.astype(np.int64)
    return pid // 1000000, (pid // 10) % 100000, pid % 10      # P, T, A


def bootstrap(x: np.ndarray, n_boot: int = 1000, hat: int = 0):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(hat)
    tb = np.array([x[rng.integers(0, len(x), len(x))].mean()
                   for _ in range(n_boot)])
    return float(x.mean()), float(np.percentile(tb, 2.5)), \
        float(np.percentile(tb, 97.5))


def hieu_khong_cap(a: np.ndarray, b: np.ndarray, n_boot: int = 1000,
                   hat: int = 0):
    """Hiệu giữa hai NHÓM TRUY VẤN KHÁC NHAU — nên lấy mẫu lại độc lập hai bên.

    Khác với so sánh cặp ở mục 4.2 README: ở đó hai cấu hình chạy trên cùng
    truy vấn nên lấy hiệu theo từng truy vấn. Ở đây nhóm 'bay thấp' và 'bay cao'
    là hai tập truy vấn khác nhau, không ghép cặp được.
    """
    rng = np.random.default_rng(hat)
    d = np.array([a[rng.integers(0, len(a), len(a))].mean()
                  - b[rng.integers(0, len(b), len(b))].mean()
                  for _ in range(n_boot)])
    return float(a.mean() - b.mean()), float(np.percentile(d, 2.5)), \
        float(np.percentile(d, 97.5))


def doc_query(protocol_dir: str, ten: str) -> list[str]:
    p = os.path.join(protocol_dir, ten + ".txt")
    return [l.strip().replace("\\", "/") for l in io.open(p, encoding="utf-8")
            if l.strip().startswith("query/")]


def chieu_cao_anh(goc: str, ds: list[str]) -> np.ndarray:
    from PIL import Image
    h = np.zeros(len(ds), dtype=np.int32)
    for i, f in enumerate(ds):
        try:
            with Image.open(os.path.join(goc, f)) as im:   # chỉ đọc đầu file
                h[i] = im.size[1]
        except Exception:
            h[i] = -1
    return h


def commit_hien_tai() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="VN-04: phân tích lỗi theo góc nhìn")
    ap.add_argument("--pred", required=True, help="thư mục predictions/<run_id>")
    ap.add_argument("--anh", default="", help="gốc ảnh AG-ReID.v2 (cho phân tích 2)")
    ap.add_argument("--protocol-dir", default="", help="nơi có exp*.txt")
    ap.add_argument("--ra-csv", default="")
    ap.add_argument("--run-id", default="VN04-phan-tich-loi-20261007")
    ap.add_argument("--model", default="osnet_ain_x1_0_dangguon")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args()

    hang, bc = [], {}
    meta = dict(run_id=a.run_id, date=date.today().isoformat(),
                commit=commit_hien_tai(), task_id="VN-04", dataset="AG-ReID.v2",
                model=a.model, checkpoint_sha256="", precision="fp32",
                hardware="RTX 3060 Laptop 6GB")

    def ghi(split, metric, v, lo, hi, n, chance="", notes=""):
        hang.append(dict(meta, split=split, metric=metric,
                         value=round(v * 100, 4), ci95_low=round(lo * 100, 4),
                         ci95_high=round(hi * 100, 4), n=n,
                         chance_level=chance, notes=notes))

    for ten, nhan in PROTOCOL.items():
        f = os.path.join(a.pred, f"predictions_{ten}.npz")
        if not os.path.exists(f):
            print(f"Bỏ qua {ten}: không có {f}")
            continue
        z = np.load(f)
        qp, qc = z["query_pid"], z["query_cam"]
        gp, gc = z["gallery_pid"], z["gallery_cam"]
        r1, ap_ = z["cmc"][:, 0].astype(float), z["ap"].astype(float)
        top1 = z["thu_tu_top100"][:, 0]

        # bốn protocol này query và gallery khác camera hoàn toàn, nên luật loại
        # ảnh trùng (cùng pid VÀ cùng camera) không loại gì; top-1 thô là top-1 thật
        assert not set(np.unique(qc)) & set(np.unique(gc)), "camera trùng"

        Pq, Tq, Aq = giai_ma(qp)
        Pg, Tg, Ag = giai_ma(gp)
        d = {"nhan": nhan, "n": len(qp)}
        print(f"\n=== {nhan}  (n = {len(qp)}) ===")

        # ── 1. theo độ cao bay
        d["do_cao"] = {}
        for A in (0, 1, 2):
            m = Aq == A
            v, lo, hi = bootstrap(r1[m], a.n_boot)
            vm, lom, him = bootstrap(ap_[m], a.n_boot)
            d["do_cao"][A] = (int(m.sum()), v, lo, hi, vm, lom, him)
            ghi(ten, f"Rank1_docao_{TEN_A[A]}", v, lo, hi, int(m.sum()))
            ghi(ten, f"mAP_docao_{TEN_A[A]}", vm, lom, him, int(m.sum()))
            print(f"  bay {TEN_A[A]:<4} n={m.sum():4d}  Rank-1 {v*100:5.2f}% "
                  f"[{lo*100:5.2f}–{hi*100:5.2f}]   mAP {vm*100:5.2f}%")
        h, lo, hi = hieu_khong_cap(r1[Aq == 0], r1[Aq == 2], a.n_boot)
        d["thap_tru_cao"] = (h, lo, hi)
        ghi(ten, "Rank1_thap_tru_cao", h, lo, hi,
            int((Aq == 0).sum() + (Aq == 2).sum()), chance=0,
            notes="hai nhom truy van khac nhau, bootstrap khong cap")
        print(f"  thấp − cao = {h*100:+.2f} [{lo*100:+.2f} – {hi*100:+.2f}]"
              + ("  -> CÓ ý nghĩa" if lo > 0 or hi < 0 else "  -> chưa đủ bằng chứng"))

        # ── 3. phân loại lỗi Rank-1
        sai = r1 == 0
        g = top1[sai]
        cung_P = Pg[g] == Pq[sai]
        cung_T = Tg[g] == Tq[sai]
        loai = {
            "dung_nguoi_cung_phien": int((cung_P & cung_T).sum()),
            "dung_nguoi_khac_phien": int((cung_P & ~cung_T).sum()),
            "nham_nguoi_cung_canh": int((~cung_P & cung_T).sum()),
            "nham_han": int((~cung_P & ~cung_T).sum()),
        }
        d["loi"] = (int(sai.sum()), loai)
        print(f"  {sai.sum()} truy vấn sai Rank-1:")
        for k, v in loai.items():
            print(f"    {k:<24} {v:5d}  ({v/max(sai.sum(),1)*100:5.1f}%)")
            ghi(ten, f"loi_{k}", v / max(sai.sum(), 1), float("nan"),
                float("nan"), int(sai.sum()),
                notes="ti le trong so truy van sai Rank-1")

        # ── 4. Rank-1 theo người — thí nghiệm phụ, KHÔNG thay số chính thức
        r1_nguoi = (Pg[top1] == Pq).astype(float)
        v, lo, hi = bootstrap(r1_nguoi, a.n_boot)
        v0, _, _ = bootstrap(r1, a.n_boot)
        d["theo_nguoi"] = (v0, v, lo, hi)
        ghi(ten, "Rank1_theo_nguoi_PHU", v, lo, hi, len(qp),
            notes="thi nghiem phu: dung khi trung ma nguoi P, bo qua T va A; "
                  "KHONG thay so chinh thuc theo protocol")
        print(f"  Rank-1 chính thức {v0*100:.2f}%  ->  theo người {v*100:.2f}% "
              f"[{lo*100:.2f}–{hi*100:.2f}]   (+{(v-v0)*100:.2f})")

        # ── 5. Rank-1 khi chỉ so với người CÙNG PHIÊN — thí nghiệm phụ
        # Gallery của benchmark trộn người từ mọi ngày quay. Bàn giao thật chỉ
        # cần phân biệt những người ĐANG có mặt ở hiện trường. Giới hạn gallery
        # về cùng trường T (cùng ngày, cùng buổi) là phép xấp xỉ gần nhất có thể.
        # Chỉ có top-100 nên truy vấn không có ứng viên cùng phiên nào trong
        # top-100 bị tính là trượt -> con số là CẬN DƯỚI.
        top = z["thu_tu_top100"]
        trung = np.zeros(len(qp))
        khong_ro, co_g = 0, []
        for i in range(len(qp)):
            cung = top[i][Tg[top[i]] == Tq[i]]
            co_g.append(int((Tg == Tq[i]).sum()))
            if len(cung) == 0:
                khong_ro += 1
                continue
            trung[i] = float(gp[cung[0]] == qp[i])
        v, lo, hi = bootstrap(trung, a.n_boot)
        d["cung_phien"] = (v, lo, hi, khong_ro, float(np.mean(co_g)), len(gp))
        ghi(ten, "Rank1_cung_phien_PHU_can_duoi", v, lo, hi, len(qp),
            notes=f"thi nghiem phu: chi so voi gallery cung truong T; "
                  f"can duoi vi chi co top-100, {khong_ro} truy van khong ro "
                  f"tinh la truot; gallery cung phien TB {np.mean(co_g):.0f} "
                  f"so voi {len(gp)}")
        print(f"  chỉ so với người cùng phiên: Rank-1 ≥ {v*100:.2f}% "
              f"[{lo*100:.2f}–{hi*100:.2f}]  (gallery TB {np.mean(co_g):.0f} "
              f"thay vì {len(gp)}, {khong_ro} không rõ tính là trượt)")

        # ── 2. theo kích thước người trong ảnh UAV (chỉ khi query là UAV)
        query_la_uav = ten.startswith(("exp1", "exp2"))
        if a.anh and a.protocol_dir and query_la_uav:
            ds = doc_query(a.protocol_dir, ten)
            if len(ds) == len(qp):
                hq = chieu_cao_anh(a.anh, ds)
                ok = hq > 0
                bien = np.percentile(hq[ok], [33.3, 66.7])
                nhom = np.digitize(hq, bien)            # 0 nhỏ · 1 vừa · 2 lớn
                d["co_anh"] = {"bien": bien.tolist()}
                print(f"  chiều cao người trong ảnh UAV: ranh giới "
                      f"{bien[0]:.0f} / {bien[1]:.0f} px")
                for k, tk in enumerate(("nho", "vua", "lon")):
                    m = ok & (nhom == k)
                    v, lo, hi = bootstrap(r1[m], a.n_boot)
                    d["co_anh"][tk] = (int(m.sum()), v, lo, hi,
                                       float(np.median(hq[m])))
                    ghi(ten, f"Rank1_coanh_{tk}", v, lo, hi, int(m.sum()),
                        notes=f"chieu cao trung vi {np.median(hq[m]):.0f}px")
                    print(f"    người {tk:<4} (~{np.median(hq[m]):3.0f}px) "
                          f"n={m.sum():4d}  Rank-1 {v*100:5.2f}% "
                          f"[{lo*100:5.2f}–{hi*100:5.2f}]")
                # cỡ ảnh có phải là đường đi của độ cao không
                d["co_theo_do_cao"] = {int(A): float(np.median(hq[ok & (Aq == A)]))
                                       for A in (0, 1, 2)}
                # trong CÙNG một độ cao, người to có còn dễ khớp hơn người nhỏ?
                # Nếu có thì độ phân giải là yếu tố thật, không chỉ là nhãn độ cao.
                print("    trong cùng độ cao, người lớn − người nhỏ (tách ở trung vị):")
                for A in (0, 1, 2):
                    m = ok & (Aq == A)
                    med = np.median(hq[m])
                    lon, nho = r1[m & (hq >= med)], r1[m & (hq < med)]
                    h_, lo_, hi_ = hieu_khong_cap(lon, nho, a.n_boot)
                    ghi(ten, f"Rank1_lon_tru_nho_docao_{TEN_A[A]}", h_, lo_, hi_,
                        int(m.sum()), chance=0,
                        notes=f"tach o trung vi {med:.0f}px trong cung do cao")
                    print(f"      bay {TEN_A[A]:<4} {h_*100:+6.2f} "
                          f"[{lo_*100:+6.2f} – {hi_*100:+6.2f}]"
                          + ("  có ý nghĩa" if lo_ > 0 or hi_ < 0 else
                             "  chưa đủ bằng chứng"))
                print("    trung vị chiều cao theo độ cao bay: " + ", ".join(
                    f"{TEN_A[A]} {v:.0f}px"
                    for A, v in d["co_theo_do_cao"].items()))
        bc[ten] = d

    if a.ra_csv:
        os.makedirs(os.path.dirname(a.ra_csv) or ".", exist_ok=True)
        with io.open(a.ra_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COT)
            w.writeheader()
            for r in hang:
                r = {k: ("" if isinstance(v, float) and np.isnan(v) else v)
                     for k, v in r.items()}
                w.writerow(r)
        print(f"\nĐã ghi {len(hang)} dòng -> {a.ra_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
