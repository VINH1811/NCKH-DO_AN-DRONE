# -*- coding: utf-8 -*-
"""Gộp metrics của ba đề tài thành một bảng để đối chiếu.

Quét `*/metrics/*.csv`, chỉ nhận file **đúng 17 cột** ở mục 3 README, rồi nối
lại. File nào chưa đúng mẫu thì bỏ qua và báo tên — như vậy ai quên chuẩn hoá
là biết ngay, thay vì ra một bảng lệch cột đầy ô trống mà không rõ vì sao.

Bỏ qua cả file `*-ban-sua-du-17-cot.csv` lẫn bản gốc của nó thì mất dữ liệu, nên
quy tắc là: nếu có bản `-ban-sua-du-17-cot` thì dùng bản đó và bỏ bản gốc.

Kết quả ra `docs/metrics_tong_hop.csv`. Đây là **file sinh lại được**, ai cập
nhật metrics thì chạy lại, không sửa tay.

Chạy:  python common/gop_metrics.py
"""
from __future__ import annotations

import glob
import io
import os
import sys
from datetime import datetime

import pandas as pd

COT = ["run_id", "date", "commit", "task_id", "dataset", "split", "model",
       "checkpoint_sha256", "precision", "metric", "value", "ci95_low",
       "ci95_high", "n", "chance_level", "hardware", "notes"]

RA = "docs/metrics_tong_hop.csv"
HAU_TO_SUA = "-ban-sua-du-17-cot"


def main() -> int:
    files = sorted(glob.glob("*/metrics/*.csv"))
    if not files:
        print("Không thấy file nào ở */metrics/*.csv. Chạy từ gốc repo.")
        return 1

    # bản đã chuẩn hoá thì thay cho bản gốc
    da_sua = {f.replace(HAU_TO_SUA, "") for f in files if HAU_TO_SUA in f}
    files = [f for f in files if f not in da_sua]

    nhan, bo = [], []
    for f in files:
        try:
            d = pd.read_csv(f, encoding="utf-8-sig")
        except Exception as e:
            bo.append((f, f"đọc lỗi: {e}"))
            continue
        if list(d.columns) != COT:
            thieu = [c for c in COT if c not in d.columns]
            bo.append((f, f"thiếu {len(thieu)} cột: {', '.join(thieu[:5])}"
                          + ("..." if len(thieu) > 5 else "")))
            continue
        d.insert(0, "de_tai", f.split(os.sep)[0].replace("/", ""))
        nhan.append(d)
        print(f"  nhận  {f}  ({len(d)} dòng)")

    for f, ly_do in bo:
        print(f"  BỎ    {f}  -> {ly_do}")

    if not nhan:
        print("\nKhông file nào đúng mẫu 17 cột. Dùng "
              "common/chuan_hoa_metrics.py để chuyển trước.")
        return 1

    d = pd.concat(nhan, ignore_index=True)
    d = d.sort_values(["de_tai", "run_id", "metric", "model"],
                      kind="stable").reset_index(drop=True)
    os.makedirs(os.path.dirname(RA), exist_ok=True)
    d.to_csv(RA, index=False, encoding="utf-8-sig")

    print(f"\nĐã gộp {len(nhan)}/{len(files)} file -> {RA}")
    print(f"  {len(d)} dòng · {d.de_tai.nunique()} đề tài · "
          f"{d.run_id.nunique()} lần chạy · {d.metric.nunique()} loại metric")
    print()
    print(d.groupby("de_tai").agg(
        so_dong=("metric", "size"), so_lan_chay=("run_id", "nunique"),
        co_ci=("ci95_low", lambda s: int(pd.to_numeric(s, errors="coerce")
                                         .notna().sum()))).to_string())

    thieu_ci = d[pd.to_numeric(d.ci95_low, errors="coerce").isna()]
    if len(thieu_ci):
        print(f"\n{len(thieu_ci)}/{len(d)} dòng chưa có khoảng tin cậy "
              f"(mục 4.1 README yêu cầu có). Theo đề tài:")
        print("  " + thieu_ci.groupby("de_tai").size().to_string().replace(
            "\n", "\n  "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
