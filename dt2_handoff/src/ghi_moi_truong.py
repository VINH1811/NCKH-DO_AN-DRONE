# -*- coding: utf-8 -*-
"""Ghi lại môi trường chạy và khoá hash checkpoint — đầu ra của VN-02 và C-01.

Checklist tái lập của đợt test đòi bảy thứ. Script này sinh đủ cả bảy:
  - commit hash của lần chạy              -> moi_truong.json
  - lệnh chạy đầy đủ                      -> tự ghi lại argv
  - phiên bản thư viện                    -> pip_freeze.txt
  - phần cứng: GPU, driver, CUDA          -> moi_truong.json
  - checkpoint và SHA256                  -> checkpoint.lock.json
  - precision khi chạy                    -> khai báo bằng --precision
  - config từng thí nghiệm                -> --ghi-chu và file config kèm theo

Vì sao phải khoá hash checkpoint: cùng một tên file "osnet_x1_0_market.pth" có
thể là hai bản trọng số khác nhau tuỳ nguồn tải. Không khoá hash thì nửa tháng
sau không ai chứng minh được con số Rank-1 sinh ra từ trọng số nào.

Dùng:
  python ghi_moi_truong.py --ra bao_cao/vn02
  python ghi_moi_truong.py --ra bao_cao/vn02 --ckpt models/osnet_ain_x1_0_msmt.pth
  python ghi_moi_truong.py --ra bao_cao/vn02 --ckpt-thu-muc models --precision fp32
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def chay(lenh: list[str], han: int = 120) -> str:
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, timeout=han)
        return (r.stdout or r.stderr or "").strip()
    except Exception as e:
        return f"(không chạy được: {e})"


def sha256(duong_dan: str, khoi: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        while True:
            b = f.read(khoi)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def thong_tin_gpu() -> dict:
    d = {"nvidia_smi": chay(["nvidia-smi",
                             "--query-gpu=name,memory.total,driver_version",
                             "--format=csv,noheader"])}
    try:
        import torch
        d["torch"] = torch.__version__
        d["cuda_cua_torch"] = torch.version.cuda
        d["co_gpu"] = bool(torch.cuda.is_available())
        if d["co_gpu"]:
            p = torch.cuda.get_device_properties(0)
            d["gpu"] = p.name
            d["vram_gb"] = round(p.total_memory / 1e9, 1)
            d["compute_capability"] = f"{p.major}.{p.minor}"
        try:
            import torchvision
            d["torchvision"] = torchvision.__version__
        except Exception:
            pass
    except Exception as e:
        d["torch"] = f"(không nạp được: {e})"
    return d


def thong_tin_git() -> dict:
    return {
        "commit": chay(["git", "rev-parse", "HEAD"]),
        "nhanh": chay(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        # có thay đổi chưa commit thì kết quả KHÔNG tái lập được từ commit này
        # chỉ xét file ĐÃ theo dõi bị sửa; file chưa theo dõi (như chính thư mục
        # env/ đang ghi) không làm kết quả khó tái lập
        "ban_lam_viec_sach": chay(["git", "status", "--porcelain",
                                   "--untracked-files=no"]) == "",
        "mo_ta": chay(["git", "log", "-1", "--pretty=%s"]),
    }


def khoa_checkpoint(duong_dan: str) -> dict:
    d = {"duong_dan": duong_dan.replace("\\", "/"),
         "ten": os.path.basename(duong_dan),
         "byte": os.path.getsize(duong_dan),
         "sha256": sha256(duong_dan)}
    # đọc thêm siêu dữ liệu bên trong để biết trọng số này huấn luyện ra sao
    try:
        import torch
        o = torch.load(duong_dan, map_location="cpu", weights_only=False)
        if isinstance(o, dict):
            d["khoa_cap_cao"] = sorted(k for k in o.keys()
                                       if k != "state_dict")[:12]
            sd = o.get("state_dict", o)
            if isinstance(sd, dict):
                d["so_tensor"] = len(sd)
                # số lớp ở tầng phân loại = số danh tính của tập huấn luyện,
                # đây là dấu vết đáng tin nhất cho biết nó học trên dữ liệu nào
                for k, v in sd.items():
                    if k.endswith("classifier.weight") and hasattr(v, "shape"):
                        d["so_danh_tinh_huan_luyen"] = int(v.shape[0])
                        break
            for k in ("epoch", "rank1", "mAP", "arch"):
                if k in o:
                    v = o[k]
                    # checkpoint hay lưu rank1/mAP kiểu numpy hoặc tensor, hai
                    # thứ này đều không ghi thẳng ra JSON được
                    if hasattr(v, "item"):
                        try:
                            v = v.item()
                        except Exception:
                            v = str(v)
                    elif not isinstance(v, (int, float, str, bool, type(None))):
                        v = str(v)
                    d[k] = v
    except Exception as e:
        d["doc_noi_dung"] = f"(không đọc được: {e})"
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="Ghi môi trường + khoá hash checkpoint")
    ap.add_argument("--ra", required=True, help="thư mục ghi kết quả")
    ap.add_argument("--ckpt", action="append", default=[],
                    help="một file checkpoint (lặp lại được)")
    ap.add_argument("--ckpt-thu-muc", default="",
                    help="quét mọi .pth/.pt/.tar trong thư mục này")
    ap.add_argument("--precision", default="fp32",
                    choices=["fp32", "fp16", "bf16", "int8"],
                    help="precision dùng khi chạy thí nghiệm")
    ap.add_argument("--ghi-chu", default="", help="mô tả ngắn thí nghiệm")
    a = ap.parse_args()

    os.makedirs(a.ra, exist_ok=True)

    # ── pip freeze: lấy đúng interpreter đang chạy, không phải python mặc định
    fr = chay([sys.executable, "-m", "pip", "freeze"], han=240)
    io.open(os.path.join(a.ra, "pip_freeze.txt"), "w",
            encoding="utf-8", newline="\n").write(fr + "\n")

    # ── checkpoint
    ds = list(a.ckpt)
    if a.ckpt_thu_muc and os.path.isdir(a.ckpt_thu_muc):
        for r, _, fs in os.walk(a.ckpt_thu_muc):
            for f in sorted(fs):
                if f.lower().endswith((".pth", ".pt", ".tar", ".pth.tar")):
                    ds.append(os.path.join(r, f))
    ds = sorted({os.path.abspath(p) for p in ds if os.path.exists(p)})

    khoa = []
    for p in ds:
        print(f"Đang băm {os.path.basename(p)} ...")
        khoa.append(khoa_checkpoint(p))
    io.open(os.path.join(a.ra, "checkpoint.lock.json"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(khoa, ensure_ascii=False, indent=2) + "\n")

    # ── môi trường
    mt = {
        "ghi_luc": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "ghi_chu": a.ghi_chu,
        "precision": a.precision,
        "lenh_chay": " ".join(sys.argv),
        "interpreter": sys.executable.replace("\\", "/"),
        "python": sys.version.split()[0],
        "he_dieu_hanh": f"{platform.system()} {platform.release()} "
                        f"({platform.machine()})",
        "git": thong_tin_git(),
        "phan_cung": thong_tin_gpu(),
        "so_checkpoint": len(khoa),
    }
    io.open(os.path.join(a.ra, "moi_truong.json"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(mt, ensure_ascii=False, indent=2) + "\n")

    # ── bản tóm tắt cho người đọc
    g = mt["git"]
    pc = mt["phan_cung"]
    dong = [
        "# Môi trường chạy",
        "",
        f"Ghi lúc **{mt['ghi_luc']}**" + (f" — {a.ghi_chu}" if a.ghi_chu else ""),
        "",
        "| Mục | Giá trị |",
        "|---|---|",
        f"| Commit | `{g['commit'][:12]}` ({g['nhanh']}) |",
        f"| Bản làm việc sạch | {'có' if g['ban_lam_viec_sach'] else '**KHÔNG — có sửa chưa commit**'} |",
        f"| Python | {mt['python']} |",
        f"| Hệ điều hành | {mt['he_dieu_hanh']} |",
        f"| torch | {pc.get('torch')} (CUDA {pc.get('cuda_cua_torch')}) |",
        f"| GPU | {pc.get('gpu', '(không có)')} "
        f"{pc.get('vram_gb', '')} GB |",
        f"| Driver | {pc.get('nvidia_smi', '')} |",
        f"| Precision | {a.precision} |",
        "",
    ]
    if khoa:
        dong += ["## Checkpoint đã khoá hash", "",
                 "| Tên | SHA256 (12 ký tự đầu) | MB | Số danh tính |", "|---|---|---|---|"]
        for k in khoa:
            dong.append(f"| `{k['ten']}` | `{k['sha256'][:12]}` | "
                        f"{k['byte']/1e6:.1f} | "
                        f"{k.get('so_danh_tinh_huan_luyen', '—')} |")
        dong += ["", "SHA256 đầy đủ nằm trong `checkpoint.lock.json`.", ""]
    else:
        dong += ["## Checkpoint", "",
                 "**Chưa khoá checkpoint nào.** Chạy lại với `--ckpt` hoặc "
                 "`--ckpt-thu-muc` sau khi tải trọng số về.", ""]
    io.open(os.path.join(a.ra, "MOI_TRUONG.md"), "w",
            encoding="utf-8", newline="\n").write("\n".join(dong))

    print(f"\nĐã ghi vào {a.ra}/")
    print(f"  moi_truong.json · pip_freeze.txt · checkpoint.lock.json · MOI_TRUONG.md")
    if not g["ban_lam_viec_sach"]:
        print("\nCẢNH BÁO: còn thay đổi chưa commit. Kết quả chạy lúc này KHÔNG "
              "tái lập được từ commit đã ghi. Commit trước khi chạy thí nghiệm.")
    if not khoa:
        print("\nCHƯA có checkpoint nào được khoá — VN-02 chưa hoàn thành.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
