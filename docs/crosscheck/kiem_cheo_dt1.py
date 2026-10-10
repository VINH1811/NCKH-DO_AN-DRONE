# -*- coding: utf-8 -*-
"""Kiểm tra chéo rút gọn ĐT1 (Việt) — người kiểm tra: Vinh, 11/10/2026.

Chạy lại được toàn bộ các phép kiểm trong biên bản docs/crosscheck/dt1_follow.md,
không cần GPU và không cần nhãn gốc VisDrone:

  1. file dự đoán trong M10 có đúng là của lần chạy VT-05 không
  2. điểm tổng IDF1 / MOTA / ID switch tính lại từ 7 sequence có khớp không
  3. khoảng tin cậy khai báo có khớp bootstrap theo sequence không
  4. mã băm trọng số (nếu có file trọng số trên máy)

Chạy từ gốc repo:
  python docs/crosscheck/kiem_cheo_dt1.py [--trong-so E:/RTCN/yolo11s.pt]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

import numpy as np
import pandas as pd

DT1 = "dt1_follow"
KHAI = {"IDF1": (0.2699, 0.2410, 0.2985), "MOTA": (0.1078, 0.0820, 0.1340),
        "IDSW": 213, "sha256": "85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trong-so", default="")
    a = ap.parse_args()

    s = pd.read_csv(f"{DT1}/metrics/VT05-tracking-20261007.csv")
    s = s[s.sequence != "OVERALL"].fillna(0)
    p = pd.read_csv(f"{DT1}/predictions/VT08-eval-freeze-20261010/uav0000086_00000_v.txt",
                    header=None)

    print("1. File dự đoán M10")
    ky_vong = int(s[s.sequence == "uav0000086_00000_v"].num_predictions.iloc[0])
    print(f"   {len(p)} dòng, VT-05 ghi {ky_vong} -> {'KHỚP' if len(p) == ky_vong else 'LỆCH'}")
    print(f"   có dự đoán cho {1}/{len(s)} sequence")

    O, P = s.num_objects.values, s.num_predictions.values
    idtp, tp, sw = s.idr.values * O, s.recall.values * O, s.id_switches.values
    idf1 = 2 * idtp.sum() / (O.sum() + P.sum())
    mota = 1 - ((O - tp).sum() + (P - tp).sum() + sw.sum()) / O.sum()
    print("2. Điểm tổng tính lại từ 7 sequence")
    print(f"   IDF1 {idf1:.4f} (khai {KHAI['IDF1'][0]})  MOTA {mota:.4f} (khai {KHAI['MOTA'][0]})"
          f"  IDSW {int(sw.sum())} (khai {KHAI['IDSW']})")

    rng = np.random.default_rng(0)
    b1, b2 = [], []
    for _ in range(10000):
        k = rng.integers(0, len(s), len(s))
        b1.append(2 * idtp[k].sum() / (O[k].sum() + P[k].sum()))
        b2.append(1 - ((O[k] - tp[k]).sum() + (P[k] - tp[k]).sum() + sw[k].sum()) / O[k].sum())
    print("3. Khoảng tin cậy 95% nếu bootstrap theo sequence")
    print(f"   IDF1 [{np.percentile(b1, 2.5):.4f}, {np.percentile(b1, 97.5):.4f}]"
          f"  (khai [{KHAI['IDF1'][1]}, {KHAI['IDF1'][2]}])")
    print(f"   MOTA [{np.percentile(b2, 2.5):.4f}, {np.percentile(b2, 97.5):.4f}]"
          f"  (khai [{KHAI['MOTA'][1]}, {KHAI['MOTA'][2]}])")
    print(f"   sequence lớn nhất chiếm {O.max() / O.sum() * 100:.1f}% số đối tượng;"
          f" {int((P < 0.05 * O).sum())} sequence gần như không có phát hiện")

    if a.trong_so and os.path.exists(a.trong_so):
        h = hashlib.sha256(open(a.trong_so, "rb").read()).hexdigest()
        print(f"4. SHA256 trọng số: {'KHỚP' if h == KHAI['sha256'] else 'LỆCH'} ({h[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
