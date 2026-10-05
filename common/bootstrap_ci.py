# -*- coding: utf-8 -*-
"""Khoảng tin cậy 95% và so sánh cặp — công cụ chung cho cả ba đề tài (C-03).

Mọi đề tài đều quy về cùng một dạng đầu vào: **một vector điểm theo từng mục**.
Mục là gì thì tuỳ đề tài — ĐT1 là mỗi ảnh một AP, ĐT2 và ĐT3 là mỗi truy vấn một
AP hoặc một chỉ báo trúng/trượt. Nhờ vậy một công cụ dùng được cho cả ba, và số
liệu của ba người so với nhau được.

Hai phép tính:

1. KHOẢNG TIN CẬY 95% — lấy mẫu lại có hoàn lại trên các mục, tính lại trung
   bình 1.000 lần, lấy phân vị 2,5% và 97,5%. Trả lời: "nếu thu một tập truy vấn
   khác cùng cỡ thì con số này dao động trong khoảng nào".

2. SO SÁNH CẶP — khi so hai cấu hình, KHÔNG so hai khoảng tin cậy xem có chồng
   nhau không. Cách đó yếu và dễ kết luận sai theo hướng thận trọng quá mức.

   Lý do: hai cấu hình chạy trên CÙNG một tập truy vấn, mà truy vấn thì có cái
   dễ cái khó. Phần dao động do "truy vấn khó" xuất hiện ở cả hai bên và tự triệt
   tiêu khi lấy hiệu. Nên phải lấy hiệu THEO TỪNG TRUY VẤN rồi mới bootstrap
   trên hiệu đó. Kết luận chặt hơn hẳn với cùng một lượng dữ liệu.

   Khoảng tin cậy của hiệu không chứa 0  ->  khác biệt có ý nghĩa.

Dùng:
  # một cấu hình
  python common/bootstrap_ci.py --diem kq.npz --khoa ap --ten "OSNet-AIN"

  # so sánh cặp hai cấu hình trên cùng truy vấn
  python common/bootstrap_ci.py \\
      --diem  ain/predictions_exp1.npz  --khoa ap --ten "AIN đa nguồn" \\
      --diem-b msmt/predictions_exp1.npz --khoa-b ap --ten-b "MSMT17" \\
      --ngau-nhien 0.00308 --ra metrics/ket_qua_chuan.csv \\
      --run-id VN03-ain-20261004 --task-id VN-03 --dataset AG-ReID.v2 \\
      --split exp1_aerial_to_cctv --metric mAP
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

COT = ["run_id", "date", "commit", "task_id", "dataset", "split", "model",
       "checkpoint_sha256", "precision", "metric", "value", "ci95_low",
       "ci95_high", "n", "chance_level", "hardware", "notes"]


def nap_diem(duong_dan: str, khoa: str = "") -> np.ndarray:
    """Đọc vector điểm từ .npy, .npz hoặc .csv. Mỗi phần tử là một mục."""
    duoi = os.path.splitext(duong_dan)[1].lower()
    if duoi == ".npy":
        v = np.load(duong_dan)
    elif duoi == ".npz":
        z = np.load(duong_dan)
        if not khoa:
            raise SystemExit(f"{duong_dan} là .npz, phải nêu --khoa. "
                             f"Khoá có sẵn: {list(z.files)}")
        if khoa not in z.files:
            raise SystemExit(f"Không có khoá '{khoa}'. Có: {list(z.files)}")
        v = z[khoa]
    elif duoi in (".csv", ".txt"):
        import pandas as pd
        d = pd.read_csv(duong_dan)
        if khoa:
            v = d[khoa].to_numpy()
        elif d.shape[1] == 1:
            v = d.iloc[:, 0].to_numpy()
        else:
            raise SystemExit(f"{duong_dan} có {d.shape[1]} cột, phải nêu --khoa")
    else:
        raise SystemExit(f"Không đọc được định dạng: {duoi}")

    v = np.asarray(v, dtype=np.float64)
    if v.ndim == 2 and v.shape[1] >= 1:
        # cmc là ma trận [n_truy_van, k]; cột 0 chính là Rank-1
        print(f"  ({os.path.basename(duong_dan)}: mảng {v.shape}, lấy cột 0)")
        v = v[:, 0]
    if v.ndim != 1:
        raise SystemExit(f"Cần vector một chiều, nhận được {v.shape}")
    return v


def khoang_tin_cay(x: np.ndarray, n_boot: int, hat: int) -> tuple:
    rng = np.random.default_rng(hat)
    n = len(x)
    tb = np.array([x[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return float(x.mean()), float(np.percentile(tb, 2.5)), \
        float(np.percentile(tb, 97.5))


def so_sanh_cap(a: np.ndarray, b: np.ndarray, n_boot: int, hat: int) -> dict:
    """So sánh cặp: lấy hiệu theo từng mục rồi bootstrap trên hiệu đó.

    Lấy lại CÙNG một bộ chỉ số cho cả hai bên trong mỗi lần lấy mẫu — đó chính
    là chỗ làm nên tính 'cặp'. Lấy mẫu độc lập hai bên là quay về so hai khoảng
    rời rạc, mất hết lợi thế.
    """
    if len(a) != len(b):
        raise SystemExit(f"Hai vector khác độ dài ({len(a)} và {len(b)}); "
                         f"so sánh cặp đòi cùng tập truy vấn, cùng thứ tự.")
    d = a - b
    rng = np.random.default_rng(hat)
    n = len(d)
    tb = np.array([d[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))
    return {
        "hieu_tb": float(d.mean()),
        "hieu_ci_duoi": lo,
        "hieu_ci_tren": hi,
        "co_y_nghia": bool(lo > 0 or hi < 0),      # khoảng không chứa 0
        "a_thang": float((d > 0).mean()),
        "b_thang": float((d < 0).mean()),
        "hoa": float((d == 0).mean()),
        "n": n,
    }


def kiem_dinh_ngau_nhien(x: np.ndarray, p_null, n_mo_phong: int = 200000,
                         hat: int = 0) -> dict:
    """Kiểm định hoán vị một phía: kết quả này có vượt xếp hạng ngẫu nhiên không?

    Giả thuyết không là hệ thống xếp hạng ngẫu nhiên. Dưới giả thuyết đó, mỗi
    mục là MỘT LẦN BỐC ĐỘC LẬP với xác suất p_null — bất kể điểm thật của mô
    hình có tương quan giữa các truy vấn hay không.

    Đây là chỗ hay nhầm: tương quan giữa truy vấn làm giảm cỡ mẫu hiệu dụng khi
    ƯỚC LƯỢNG KHOẢNG, nhưng không làm hỏng PHÉP KIỂM ĐỊNH này. Vì vậy khi số lần
    trúng quá ít khiến bootstrap suy biến, phép kiểm định vẫn dùng được.

    p_null nhận một số, hoặc một vector cùng độ dài x khi mỗi mục có gallery
    khác cỡ (khi đó là tổng các Bernoulli khác xác suất).
    """
    x = np.asarray(x, dtype=float)
    pn = np.full(len(x), float(p_null)) if np.isscalar(p_null)         else np.asarray(p_null, dtype=float)
    if len(pn) != len(x):
        raise SystemExit("p_null phải là một số hoặc vector cùng độ dài điểm")
    quan_sat = float(x.sum())
    rng = np.random.default_rng(hat)
    lo = 0
    con = n_mo_phong
    while con > 0:                       # chia mẻ để không ngốn bộ nhớ
        me = min(con, 20000)
        gia = (rng.random((me, len(pn))) < pn).sum(axis=1)
        lo += int((gia >= quan_sat).sum())
        con -= me
    return {"so_trung": quan_sat, "n": len(x),
            "p_mot_phia": (lo + 1) / (n_mo_phong + 1),   # hiệu chỉnh, không ra 0
            "n_mo_phong": n_mo_phong}


def commit_hien_tai() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "?"
    except Exception:
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Khoảng tin cậy 95% và so sánh cặp (C-03)")
    ap.add_argument("--diem", required=True, help=".npy/.npz/.csv điểm từng mục")
    ap.add_argument("--khoa", default="", help="tên khoá/cột trong file")
    ap.add_argument("--ten", default="A", help="nhãn cấu hình A")
    ap.add_argument("--diem-b", default="", help="cấu hình B để so sánh cặp")
    ap.add_argument("--khoa-b", default="")
    ap.add_argument("--ten-b", default="B")
    ap.add_argument("--ngau-nhien", type=float, default=float("nan"),
                    help="mức ngẫu nhiên, cùng thang với điểm (0–1)")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--hat", type=int, default=0)
    ap.add_argument("--phan-tram", action="store_true",
                    help="in và ghi theo %% thay vì 0–1")
    ap.add_argument("--p-null", default="",
                    help="xác suất trúng dưới xếp hạng ngẫu nhiên: một số, hoặc "
                         "tên cột trong file CSV khi gallery khác cỡ từng mục. "
                         "Có tham số này thì chạy thêm kiểm định một phía.")
    # các cột của mẫu CSV chung
    ap.add_argument("--ra", default="", help="ghi thêm vào CSV theo mẫu chung")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--task-id", default="")
    ap.add_argument("--dataset", default="")
    ap.add_argument("--split", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--checkpoint-sha256", default="")
    ap.add_argument("--precision", default="")
    ap.add_argument("--metric", default="metric")
    ap.add_argument("--hardware", default="")
    ap.add_argument("--notes", default="")
    a = ap.parse_args()

    k = 100.0 if a.phan_tram else 1.0
    don = "%" if a.phan_tram else ""

    x = nap_diem(a.diem, a.khoa)
    tb, lo, hi = khoang_tin_cay(x, a.n_boot, a.hat)
    print(f"\n{a.ten}")
    print(f"  n = {len(x)}")
    print(f"  {a.metric} = {tb*k:.2f}{don}  [khoảng tin cậy 95%: "
          f"{lo*k:.2f} – {hi*k:.2f}]")
    if not np.isnan(a.ngau_nhien):
        print(f"  mức ngẫu nhiên = {a.ngau_nhien*k:.3f}{don}"
              f"   (gấp {tb/a.ngau_nhien:.1f} lần)" if a.ngau_nhien > 0 else "")

    kd = None
    if a.p_null:
        try:
            pn = float(a.p_null)
        except ValueError:
            import pandas as pd
            pn = pd.read_csv(a.diem, encoding="utf-8-sig")[a.p_null].to_numpy()
        kd = kiem_dinh_ngau_nhien(x, pn, hat=a.hat)
        print(f"  kiểm định một phía vs xếp hạng ngẫu nhiên: "
              f"p = {kd['p_mot_phia']:.6f}  ({int(kd['so_trung'])} lần trúng)")
        print("    -> " + ("VƯỢT ngẫu nhiên (p < 0,05)" if kd["p_mot_phia"] < 0.05
                           else "CHƯA đủ bằng chứng vượt ngẫu nhiên"))
        if kd["so_trung"] < 5:
            print("    Lưu ý: dưới 5 lần trúng — khoảng bootstrap ở trên suy "
                  "biến, kết luận vượt ngẫu nhiên lấy theo kiểm định này.")

    hang = [{"run_id": a.run_id, "date": date.today().isoformat(),
             "commit": commit_hien_tai(), "task_id": a.task_id,
             "dataset": a.dataset, "split": a.split, "model": a.model or a.ten,
             "checkpoint_sha256": a.checkpoint_sha256, "precision": a.precision,
             "metric": a.metric, "value": round(tb * k, 4),
             "ci95_low": round(lo * k, 4), "ci95_high": round(hi * k, 4),
             "n": len(x),
             "chance_level": ("" if np.isnan(a.ngau_nhien)
                              else round(a.ngau_nhien * k, 5)),
             "hardware": a.hardware,
             "notes": (a.notes + ("; " if a.notes else "")
                       + (f"p_mot_phia={kd['p_mot_phia']:.6f}; "
                          f"so_trung={int(kd['so_trung'])}"
                          + ("; bootstrap suy bien do hiem lan trung"
                             if kd["so_trung"] < 5 else "") if kd else "")
                       ).strip("; ")}]

    if a.diem_b:
        y = nap_diem(a.diem_b, a.khoa_b or a.khoa)
        tb2, lo2, hi2 = khoang_tin_cay(y, a.n_boot, a.hat)
        print(f"\n{a.ten_b}")
        print(f"  {a.metric} = {tb2*k:.2f}{don}  [khoảng tin cậy 95%: "
              f"{lo2*k:.2f} – {hi2*k:.2f}]")
        hang.append(dict(hang[0], model=a.ten_b, value=round(tb2 * k, 4),
                         ci95_low=round(lo2 * k, 4),
                         ci95_high=round(hi2 * k, 4),
                         checkpoint_sha256="", notes=a.notes))

        s = so_sanh_cap(x, y, a.n_boot, a.hat)
        print(f"\nSo sánh cặp trên cùng {s['n']} truy vấn "
              f"({a.ten} trừ {a.ten_b})")
        print(f"  hiệu trung bình = {s['hieu_tb']*k:+.2f}{don}  "
              f"[{s['hieu_ci_duoi']*k:+.2f} – {s['hieu_ci_tren']*k:+.2f}]")
        print(f"  {a.ten} hơn ở {s['a_thang']*100:.1f}% truy vấn · "
              f"{a.ten_b} hơn ở {s['b_thang']*100:.1f}% · "
              f"hoà {s['hoa']*100:.1f}%")
        print("  -> " + ("KHÁC BIỆT CÓ Ý NGHĨA (khoảng tin cậy không chứa 0)"
                         if s["co_y_nghia"] else
                         "CHƯA đủ bằng chứng (khoảng tin cậy chứa 0)"))

        # đối chiếu với cách yếu hơn, để thấy vì sao quy ước chọn so sánh cặp
        chong = not (hi < lo2 or hi2 < lo)
        print(f"  (so hai khoảng rời rạc thì chúng "
              f"{'CHỒNG nhau — kết luận được ít hơn' if chong else 'không chồng nhau'})")

        hang.append(dict(hang[0], model=f"{a.ten} − {a.ten_b}",
                         metric=f"{a.metric}_hieu_cap",
                         value=round(s["hieu_tb"] * k, 4),
                         ci95_low=round(s["hieu_ci_duoi"] * k, 4),
                         ci95_high=round(s["hieu_ci_tren"] * k, 4),
                         checkpoint_sha256="", chance_level=0,
                         notes=f"so sánh cặp; {a.ten} thắng "
                               f"{s['a_thang']*100:.1f}% truy vấn; "
                               f"{'có' if s['co_y_nghia'] else 'chưa có'} ý nghĩa"))

    if a.ra:
        os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
        moi = not os.path.exists(a.ra)
        with io.open(a.ra, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COT)
            if moi:
                w.writeheader()
            w.writerows(hang)
        print(f"\nĐã ghi thêm {len(hang)} dòng vào {a.ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
