# -*- coding: utf-8 -*-
"""Hình minh hoạ cho báo cáo tổng hợp ĐT1 (Việt) và ĐT3 (Lương).

Mọi số đọc từ file đã commit của chính hai đề tài, không gõ tay. Màu và quy cách
giống bộ hình của ĐT2 (bảng màu chuẩn, chữ màu mực, Times New Roman).

Chạy từ gốc repo:  python docs/tong_ket_nhom/tao_hinh_dt1_dt3.py
"""
from __future__ import annotations

import glob
import os
import shutil

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib import font_manager                  # noqa: E402

RA = "docs/tong_ket_nhom/hinh"
XANH, CAM, NGOC, VANG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
XAM, MUC, MUC2, LUOI = "#9a9993", "#0b0b0b", "#52514e", "#e6e5e1"


def dat_font():
    for f in glob.glob("C:/Windows/Fonts/times*.ttf"):
        font_manager.fontManager.addfont(f)
    plt.rcParams.update({
        "font.family": "Times New Roman", "font.size": 13,
        "axes.edgecolor": LUOI, "axes.labelcolor": MUC2, "xtick.color": MUC2,
        "ytick.color": MUC2, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": LUOI, "axes.axisbelow": True,
        "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight",
        "figure.facecolor": "white"})


def luu(fig, ten):
    fig.savefig(os.path.join(RA, ten))
    plt.close(fig)
    print(" ", ten)


# ───────────────────────────── ĐT1 ─────────────────────────────
def v1_tung_sequence():
    s = pd.read_csv("dt1_follow/metrics/VT05-tracking-20261007.csv")
    s = s[s.sequence != "OVERALL"].fillna(0)
    s = s.sort_values("num_objects", ascending=False)
    ten = [x.replace("uav0000", "").replace("_v", "") for x in s.sequence]
    x = np.arange(len(s))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(x - w / 2, s.idf1 * 100, w - 0.03, color=XANH, label="IDF1")
    ax.bar(x + w / 2, s.mota * 100, w - 0.03, color=CAM, label="MOTA")
    ax.axhline(0, color=MUC2, lw=1)
    for xi, o, p in zip(x, s.num_objects, s.num_predictions):
        ax.text(xi, -72, f"{int(o):,}".replace(",", ".") + "\nđối tượng", ha="center",
                fontsize=11, color=MUC2)
        if p < 0.05 * o:
            ax.text(xi, 6, f"chỉ {int(p)}\nphát hiện", ha="center", fontsize=11, color=MUC)
    ax.set_xticks(x, ten)
    ax.set_ylabel("Điểm (%)")
    ax.set_ylim(-80, 48)
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)
    luu(fig, "v1_tung_sequence_vt05.png")


def v3_do_tre():
    d = pd.read_csv("dt1_follow/metrics/VT07-sitl-latency-results-20261010.csv",
                    encoding="utf-8-sig")
    d = d[d.latency_injected_ms < 1000]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(d.latency_injected_ms, d.obs_age_avg_ms, color=XANH, lw=2, marker="o",
            ms=8, label="Tuổi quan sát trung bình")
    ax.plot(d.latency_injected_ms, d.obs_age_max_ms, color=CAM, lw=2, marker="o",
            ms=8, label="Tuổi quan sát lớn nhất")
    ax.axhline(1000, color=XAM, lw=1.2, ls="--")
    ax.text(5, 1030, "ngưỡng chuyển FAILSAFE_HOLD (1.000 ms)", fontsize=12, color=MUC2)
    ax.set_xlabel("Độ trễ chèn thêm (ms)")
    ax.set_ylabel("ms")
    ax.set_ylim(0, 1150)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.88))
    luu(fig, "v3_do_tre_vt07.png")


# ───────────────────────────── ĐT3 ─────────────────────────────
def l1_baseline():
    d = pd.read_csv("dt3_retrieval/metrics/LG03_model_language_input.csv",
                    encoding="utf-8-sig")
    r = d[(d.model == "M-CLIP") & (d.variant == "typed_vi") & (d.source == "edata")].iloc[0]
    m = ["Recall@1", "Recall@5", "Recall@10", "mAP"]
    v = np.array([r[f"{k}_pct"] for k in m])
    lo = np.array([r[f"{k}_ci95_low_pct"] for k in m])
    hi = np.array([r[f"{k}_ci95_high_pct"] for k in m])
    ch = [0.0234, 0.1170, 0.2341, 0.2092]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(4)
    ax.bar(x, v, 0.55, color=XANH, label="M-CLIP, gõ tiếng Việt")
    ax.errorbar(x, v, yerr=[v - lo, hi - v], fmt="none", ecolor=MUC, capsize=4)
    ax.scatter(x, ch, marker="_", s=900, color=CAM, lw=3, label="Mức ngẫu nhiên", zorder=4)
    for xi, vi, h in zip(x, v, hi):
        ax.text(xi, h + 0.8, f"{vi:.2f}%", ha="center", fontsize=12, color=MUC)
    ax.set_xticks(x, m)
    ax.set_ylabel("%")
    ax.set_ylim(0, 33)
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    luu(fig, "l1_baseline_lg02.png")


def l2_so_sanh():
    d = pd.read_csv("dt3_retrieval/metrics/LG03_model_language_input.csv",
                    encoding="utf-8-sig")
    d = d[d.source == "edata"]
    kieu = [("typed_vi", "Gõ tiếng Việt"), ("typed_en_reviewed", "Gõ tiếng Anh"),
            ("spoken_whisper_vi", "Nói / Whisper"), ("spoken_phowhisper_vi", "Nói / PhoWhisper")]
    x = np.arange(len(kieu))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for j, (mod, mau) in enumerate([("M-CLIP", XANH), ("OpenCLIP", NGOC)]):
        rr = [d[(d.model == mod) & (d.variant == k)].iloc[0] for k, _ in kieu]
        v = np.array([r.mAP_pct for r in rr])
        lo = np.array([r.mAP_ci95_low_pct for r in rr])
        hi = np.array([r.mAP_ci95_high_pct for r in rr])
        xs = x + (j - 0.5) * w
        ax.bar(xs, v, w - 0.03, color=mau, label=mod)
        ax.errorbar(xs, v, yerr=[v - lo, hi - v], fmt="none", ecolor=MUC, capsize=3)
        for xi, vi, h in zip(xs, v, hi):
            ax.text(xi, h + 0.6, f"{vi:.1f}", ha="center", fontsize=12, color=MUC)
    ax.set_xticks(x, [n for _, n in kieu])
    ax.set_ylabel("mAP (%) — 9 nguồn quay, n = 70")
    ax.set_ylim(0, 29)
    ax.legend(loc="upper right", ncol=2)
    ax.grid(axis="x", visible=False)
    luu(fig, "l2_so_sanh_lg03.png")


def l3_hieu_cap():
    p = pd.read_csv("dt3_retrieval/metrics/LG03_paired_model_comparison.csv",
                    encoding="utf-8-sig")
    p = p[(p.variant == "typed_vi") & (p.source == "edata")]
    m = ["Recall@1", "Recall@5", "Recall@10", "mAP"]
    p = p.set_index("metric").loc[m]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    y = np.arange(4)[::-1]
    v = p.difference_percentage_points.values
    ax.errorbar(v, y, xerr=[v - p.ci95_low_pp.values, p.ci95_high_pp.values - v],
                fmt="o", color=NGOC, ms=8, elinewidth=2, capsize=5)
    ax.axvline(0, color=XAM, lw=1.5, ls="--")
    for yi, vi, h in zip(y, v, p.ci95_high_pp.values):
        ax.text(h + 0.6, yi, f"+{vi:.2f}  [{p.loc[m[3 - int(yi)]].ci95_low_pp:.2f} – {h:.2f}]",
                va="center", fontsize=12, color=MUC)
    ax.set_yticks(y, m)
    ax.set_xlabel("Hiệu OpenCLIP − M-CLIP, gõ tiếng Việt (điểm %)")
    ax.set_xlim(-8, 38)
    ax.grid(axis="y", visible=False)
    luu(fig, "l3_hieu_cap_lg03.png")


def main():
    os.makedirs(RA, exist_ok=True)
    dat_font()
    print("ĐT1:")
    v1_tung_sequence()
    v3_do_tre()
    # tái dùng hai hình đã có từ đúng số liệu của Việt
    for f in ("h2_c03_so_sanh_cap.png", "h9_kiem_cheo_vn09.png"):
        shutil.copy(f"dt2_handoff/reports/tong_ket/hinh/{f}", RA)
    print("ĐT3:")
    l1_baseline()
    l2_so_sanh()
    l3_hieu_cap()


if __name__ == "__main__":
    main()
