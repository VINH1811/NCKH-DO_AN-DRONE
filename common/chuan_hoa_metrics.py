# -*- coding: utf-8 -*-
"""Đưa một file metrics bất kỳ về đúng mẫu 17 cột ở mục 3 README.

Vì sao cần: ba đề tài sinh CSV với tên cột khác nhau — chỗ gọi `gpu`, chỗ gọi
`hardware`; chỗ `n_images`, chỗ `n`. Nội dung giống nhau nhưng gộp ba bảng lại
thì lệch cột, không so được. Script này đổi tên và điền cột thiếu, GIỮ NGUYÊN
file gốc, ghi ra file mới.

Ba cách điền một cột thiếu, theo thứ tự ưu tiên:
  1. Suy từ run_id   — `VT03-...-20261005` cho ra task_id VT-03 và date 2026-10-05
  2. Lấy từ git      — --commit auto dùng commit gần nhất chạm vào file đầu vào
  3. Người dùng nêu  — --dat precision=fp32

Cột thừa không vứt đi mà gộp vào `notes`, vì chúng thường là thông tin thật
(imgsz, conf, target...) mà mẫu chung không có chỗ chứa.

Dùng:
  python common/chuan_hoa_metrics.py \\
      --vao dt1_follow/metrics/VT03-detector-comparison-20261005.csv \\
      --ra  dt1_follow/metrics/VT03-detector-comparison-20261005-ban-sua-du-17-cot.csv \\
      --doi-ten gpu=hardware,n_images=n \\
      --dat precision=fp32,split=val,dataset=VisDrone2019-DET \\
      --commit auto
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

import pandas as pd

COT = ["run_id", "date", "commit", "task_id", "dataset", "split", "model",
       "checkpoint_sha256", "precision", "metric", "value", "ci95_low",
       "ci95_high", "n", "chance_level", "hardware", "notes"]


def tach_cap(s: str) -> dict:
    """Đọc chuỗi dạng 'a=b,c=d' thành dict."""
    d = {}
    for phan in s.split(","):
        phan = phan.strip()
        if not phan:
            continue
        if "=" not in phan:
            raise SystemExit(f"Sai định dạng (cần a=b): {phan}")
        k, v = phan.split("=", 1)
        d[k.strip()] = v.strip()
    return d


def commit_cua_file(duong_dan: str) -> str:
    """Commit gần nhất chạm vào file này — dấu vết tốt nhất khi lần chạy không
    ghi lại commit hash."""
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%h", "--", duong_dan],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or ""
    except Exception:
        return ""


def suy_tu_run_id(rid: str) -> dict:
    """VT03-yolo11s-visdrone-20261005 -> task_id VT-03, date 2026-10-05."""
    d = {}
    m = re.match(r"^([A-Za-z]{2})[-_]?(\d{2})", str(rid))
    if m:
        d["task_id"] = f"{m.group(1).upper()}-{m.group(2)}"
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", str(rid))
    if m:
        d["date"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="Đưa metrics về mẫu 17 cột")
    ap.add_argument("--vao", required=True)
    ap.add_argument("--ra", required=True)
    ap.add_argument("--doi-ten", default="", help="cot_cu=cot_moi,...")
    ap.add_argument("--dat", default="", help="cot=gia_tri,... điền cho mọi dòng")
    ap.add_argument("--commit", default="",
                    help="giá trị commit, hoặc 'auto' để lấy từ git")
    ap.add_argument("--vao-notes", default="",
                    help="cột thừa cần gộp vào notes; bỏ trống = gộp hết")
    ap.add_argument("--them-notes", default="",
                    help="nối thêm câu này vào notes của mọi dòng")
    a = ap.parse_args()

    d = pd.read_csv(a.vao, encoding="utf-8-sig")
    print(f"Vào : {a.vao}  ({len(d)} dòng, {len(d.columns)} cột)")

    if a.doi_ten:
        bang = tach_cap(a.doi_ten)
        thieu = [k for k in bang if k not in d.columns]
        if thieu:
            print(f"  Cảnh báo: không có cột để đổi tên: {thieu}")
        d = d.rename(columns={k: v for k, v in bang.items() if k in d.columns})
        print(f"  đổi tên: {bang}")

    # gộp cột thừa vào notes trước khi bỏ chúng đi
    thua = [c for c in d.columns if c not in COT]
    chon = ([c for c in a.vao_notes.split(",") if c.strip() in thua]
            if a.vao_notes else thua)
    if chon:
        cu = d["notes"].fillna("").astype(str) if "notes" in d.columns else ""
        them = d[chon].apply(
            lambda r: "; ".join(f"{c}={r[c]}" for c in chon
                                if pd.notna(r[c]) and str(r[c]) != ""), axis=1)
        d["notes"] = (cu + "; " + them).str.strip("; ") if len(str(cu)) else them
        print(f"  gộp vào notes: {chon}")

    dat = tach_cap(a.dat) if a.dat else {}
    if a.commit:
        dat["commit"] = (commit_cua_file(a.vao) if a.commit == "auto"
                         else a.commit)
        if a.commit == "auto":
            print(f"  commit lấy từ git: {dat['commit'] or '(không tìm được)'}")

    # điền cột thiếu: suy từ run_id trước, rồi mới tới giá trị người dùng đặt
    da_suy, de_trong = [], []
    for c in COT:
        if c in d.columns and d[c].notna().any():
            continue
        if c in dat:
            d[c] = dat[c]
        elif "run_id" in d.columns:
            v = d["run_id"].map(lambda r: suy_tu_run_id(r).get(c, ""))
            if (v != "").any():
                d[c] = v
                da_suy.append(c)
            else:
                d[c] = ""
                de_trong.append(c)
        else:
            d[c] = ""
            de_trong.append(c)

    if da_suy:
        print(f"  suy từ run_id: {da_suy}")
    if dat:
        print(f"  điền tay: {dat}")
    if de_trong:
        print(f"  ĐỂ TRỐNG: {de_trong}")

    if a.them_notes:
        # nối thêm chứ không ghi đè: notes thường đã chứa các cột thừa gộp vào
        d["notes"] = (d["notes"].fillna("").astype(str)
                      .str.cat([a.them_notes] * len(d), sep="; ").str.strip("; "))
        print(f"  thêm vào notes: {a.them_notes}")

    d = d[COT]
    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    d.to_csv(a.ra, index=False, encoding="utf-8-sig")

    assert list(d.columns) == COT, "sai thứ tự cột"
    print(f"Ra  : {a.ra}  ({len(d)} dòng, đúng {len(d.columns)} cột)")
    if de_trong:
        print(f"\nCòn {len(de_trong)} cột trống: {', '.join(de_trong)}. "
              f"Điền bằng --dat nếu biết giá trị.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
