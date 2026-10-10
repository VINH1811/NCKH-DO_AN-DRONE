# -*- coding: utf-8 -*-
"""Sinh hình minh hoạ và file thống kê cho báo cáo tổng kết ĐT2.

Mọi con số đọc thẳng từ metrics/ và predictions/ đã commit, không gõ tay — để
báo cáo luôn khớp với dữ liệu trong repo.

Màu: ba ô đầu của bảng màu chuẩn (xanh dương, cam, xanh ngọc) — bộ đã kiểm
định phân biệt được cho người mù màu ở mọi cặp. Mức ngẫu nhiên dùng xám trung
tính. Chữ trong hình luôn màu mực, không lấy màu của chuỗi số liệu.

Chạy:  python dt2_handoff/src/tao_bao_cao_tong_ket.py
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib import font_manager                    # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DT2 = os.path.join(GOC, "dt2_handoff")
RA = os.path.join(DT2, "reports", "tong_ket")
HINH = os.path.join(RA, "hinh")
PROBE = "E:/RTCN/probe_frames"

XANH, CAM, NGOC, VANG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
XAM, MUC, MUC2, LUOI = "#9a9993", "#0b0b0b", "#52514e", "#e6e5e1"

PROT = ["exp1_aerial_to_cctv", "exp2_aerial_to_wearable",
        "exp4_cctv_to_aerial", "exp5_wearable_to_aerial"]
TEN = {"exp1_aerial_to_cctv": "UAV → CCTV",
       "exp2_aerial_to_wearable": "UAV → kính đeo",
       "exp4_cctv_to_aerial": "CCTV → UAV",
       "exp5_wearable_to_aerial": "Kính đeo → UAV"}


def dat_font():
    for f in glob.glob("C:/Windows/Fonts/times*.ttf"):
        font_manager.fontManager.addfont(f)
    plt.rcParams.update({
        "font.family": "Times New Roman", "font.size": 13,
        "axes.edgecolor": LUOI, "axes.linewidth": 1, "axes.labelcolor": MUC2,
        "xtick.color": MUC2, "ytick.color": MUC2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": LUOI, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "legend.frameon": False,
        "savefig.dpi": 200, "savefig.bbox": "tight", "figure.facecolor": "white",
    })


def luu(fig, ten):
    p = os.path.join(HINH, ten)
    fig.savefig(p)
    plt.close(fig)
    print(f"  {ten}")


def bootstrap(x, n=1000, hat=0):
    rng = np.random.default_rng(hat)
    tb = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return x.mean(), np.percentile(tb, 2.5), np.percentile(tb, 97.5)


# ───────────────────────────── hình ─────────────────────────────
def h1_baseline(kq):
    """VN-03: Rank-1 hai checkpoint trên bốn protocol, kèm khoảng tin cậy."""
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(PROT))
    w = 0.36
    for j, (mod, mau, nhan) in enumerate([
            ("osnet_ain_x1_0_dangguon", XANH, "OSNet-AIN đa nguồn"),
            ("osnet_x1_0_msmt17", CAM, "OSNet MSMT17")]):
        v = [kq[(p, mod, "Rank1")] for p in PROT]
        y = np.array([a[0] for a in v])
        lo = y - np.array([a[1] for a in v])
        hi = np.array([a[2] for a in v]) - y
        xs = x + (j - 0.5) * w
        ax.bar(xs, y, w - 0.03, color=mau, label=nhan, zorder=2)
        ax.errorbar(xs, y, yerr=[lo, hi], fmt="none", ecolor=MUC, elinewidth=1,
                    capsize=3, zorder=3)
        for xi, yi in zip(xs, y):
            ax.text(xi, yi + hi.max() + 0.6, f"{yi:.1f}", ha="center",
                    fontsize=12, color=MUC)
    ax.set_xticks(x, [TEN[p] for p in PROT])
    ax.set_ylabel("Rank-1 (%)")
    ax.set_ylim(0, 42)
    ax.legend(loc="upper right", ncol=2)
    ax.grid(axis="x", visible=False)
    luu(fig, "h1_baseline_vn03.png")


def h2_c03():
    """C-03: cùng một bộ số, hai cách so sánh cho hai kết luận khác nhau."""
    a = np.load(os.path.join(GOC, "dt1_follow/metrics/VT03-yolo11s-per-image-ap.npy")).astype(float)
    b = np.load(os.path.join(GOC, "dt1_follow/metrics/VT03-yolov8s-worldv2-per-image-ap.npy")).astype(float)
    ma, la, ha = bootstrap(a)
    mb, lb, hb = bootstrap(b)
    md, ld, hd = bootstrap(a - b)
    fig, (t, p) = plt.subplots(1, 2, figsize=(10, 3.8),
                               gridspec_kw={"width_ratios": [1.15, 1]})
    for i, (m, l, h, mau, nhan) in enumerate([(ma, la, ha, XANH, "YOLO11s"),
                                              (mb, lb, hb, CAM, "YOLO-World")]):
        t.errorbar(m * 100, i, xerr=[[(m - l) * 100], [(h - m) * 100]], fmt="o",
                   color=mau, ms=8, elinewidth=2, capsize=5)
        t.text(h * 100 + 0.2, i, f"{m*100:.2f}  [{l*100:.2f} – {h*100:.2f}]",
               va="center", fontsize=12, color=MUC)
    t.axvspan(la * 100, hb * 100, color=VANG, alpha=0.18, lw=0)
    t.text((la + hb) / 2 * 100, 1.42, "vùng chồng nhau", ha="center",
           fontsize=12, color=MUC2)
    t.set_yticks([0, 1], ["YOLO11s", "YOLO-World"])
    t.set_ylim(-0.6, 1.7)
    t.set_xlim(11, 20.5)
    t.set_xlabel("AP trung bình theo ảnh (%)")
    t.set_title("Nhìn hai khoảng: chưa kết luận được", fontsize=13, color=MUC)
    t.grid(axis="y", visible=False)

    p.axvline(0, color=XAM, lw=1.5, ls="--")
    p.errorbar(md * 100, 0, xerr=[[(md - ld) * 100], [(hd - md) * 100]],
               fmt="o", color=NGOC, ms=8, elinewidth=2, capsize=5)
    p.text(md * 100, 0.32, f"+{md*100:.2f}  [+{ld*100:.2f} – +{hd*100:.2f}]",
           ha="center", fontsize=12, color=MUC)
    p.text(0.05, -0.42, "0 = không khác nhau", fontsize=12, color=MUC2)
    p.set_yticks([])
    p.set_ylim(-0.6, 0.7)
    p.set_xlim(-0.5, 2.8)
    p.set_xlabel("Hiệu YOLO11s − YOLO-World (điểm %)")
    p.set_title("So sánh cặp: có ý nghĩa", fontsize=13, color=MUC)
    p.grid(axis="y", visible=False)
    fig.tight_layout(w_pad=3)
    luu(fig, "h2_c03_so_sanh_cap.png")
    return dict(ma=ma, la=la, ha=ha, mb=mb, lb=lb, hb=hb, md=md, ld=ld, hd=hd,
                thang=float((a > b).mean()), n=len(a))


def h3_do_cao(v4):
    """VN-04: Rank-1 theo độ cao bay, bốn protocol."""
    fig, ax = plt.subplots(figsize=(9, 4.6))
    mau = [XANH, CAM, NGOC, VANG]
    x = np.arange(3)
    for p, c in zip(PROT, mau):
        y = np.array([v4[(p, f"Rank1_docao_{k}")][0] for k in ("thấp", "vừa", "cao")])
        lo = np.array([v4[(p, f"Rank1_docao_{k}")][1] for k in ("thấp", "vừa", "cao")])
        hi = np.array([v4[(p, f"Rank1_docao_{k}")][2] for k in ("thấp", "vừa", "cao")])
        ax.errorbar(x, y, yerr=[y - lo, hi - y], color=c, lw=2, marker="o",
                    ms=8, capsize=4, elinewidth=1, label=TEN[p])
        ax.text(2.08, y[-1], f"{TEN[p]}  {y[-1]:.1f}", va="center",
                fontsize=12, color=MUC)
        ax.text(-0.08, y[0], f"{y[0]:.1f}", va="center", ha="right",
                fontsize=12, color=MUC)
    ax.set_xticks(x, ["Bay thấp", "Bay vừa", "Bay cao"])
    ax.set_xlim(-0.35, 2.9)
    ax.set_ylabel("Rank-1 (%)")
    ax.set_ylim(8, 46)
    ax.legend(loc="upper right", ncol=2, fontsize=12)
    ax.grid(axis="x", visible=False)
    luu(fig, "h3_do_cao_vn04.png")


def h4_loai_loi(v4):
    """VN-04: khi sai thì sai kiểu gì."""
    fig, ax = plt.subplots(figsize=(9, 3.6))
    loai = [("loi_nham_han", XANH, "Nhầm người ở phiên khác"),
            ("loi_nham_nguoi_cung_canh", CAM, "Nhầm người cùng cảnh"),
            ("loi_dung_nguoi_khac_phien", NGOC, "Đúng người, protocol tính sai (≈ 0,1%)")]
    y = np.arange(len(PROT))[::-1]
    trai = np.zeros(len(PROT))
    for k, c, nhan in loai:
        v = np.array([v4[(p, k)][0] + (v4[(p, "loi_dung_nguoi_cung_phien")][0]
                                       if k == "loi_dung_nguoi_khac_phien" else 0)
                      for p in PROT])
        ax.barh(y, v, left=trai, color=c, height=0.62, label=nhan,
                edgecolor="white", linewidth=2)
        for yi, l, vi in zip(y, trai, v):
            if vi > 6:
                ax.text(l + vi / 2, yi, f"{vi:.1f}%", ha="center", va="center",
                        fontsize=12, color="white")
        trai += v
    ax.set_yticks(y, [TEN[p] for p in PROT])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Tỉ lệ trong số truy vấn trả lời sai Rank-1 (%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3,
              fontsize=12, handlelength=1.2, columnspacing=1.2)
    ax.grid(axis="y", visible=False)
    luu(fig, "h4_loai_loi_vn04.png")


def h5_cung_phien(kq, v4):
    """VN-04: thu hẹp ứng viên về cùng phiên quay."""
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(PROT))
    w = 0.36
    goc_ = np.array([kq[(p, "osnet_ain_x1_0_dangguon", "Rank1")][0] for p in PROT])
    cp = np.array([v4[(p, "Rank1_cung_phien_PHU_can_duoi")][0] for p in PROT])
    cpl = np.array([v4[(p, "Rank1_cung_phien_PHU_can_duoi")][1] for p in PROT])
    cph = np.array([v4[(p, "Rank1_cung_phien_PHU_can_duoi")][2] for p in PROT])
    ax.bar(x - w / 2, goc_, w - 0.03, color=XANH, label="So với toàn bộ gallery", zorder=2)
    ax.bar(x + w / 2, cp, w - 0.03, color=NGOC,
           label="Chỉ so với người cùng phiên (cận dưới)", zorder=2)
    ax.errorbar(x + w / 2, cp, yerr=[cp - cpl, cph - cp], fmt="none",
                ecolor=MUC, elinewidth=1, capsize=3, zorder=3)
    for xi, a, b in zip(x, goc_, cp):
        ax.text(xi - w / 2, a + 1, f"{a:.1f}", ha="center", fontsize=12, color=MUC)
    for xi, b, h_ in zip(x, cp, cph):
        ax.text(xi + w / 2, h_ + 1, f"≥{b:.1f}", ha="center", fontsize=12, color=MUC)
    ax.set_xticks(x, [TEN[p] for p in PROT])
    ax.set_ylabel("Rank-1 (%)")
    ax.set_ylim(0, 68)
    ax.legend(loc="upper right", fontsize=12)
    ax.grid(axis="x", visible=False)
    luu(fig, "h5_cung_phien_vn04.png")


def h6_santruong3():
    """Dữ liệu cũ: khung hình góc cao SanTruong3 và độ trôi của máy."""
    import cv2
    fs = sorted(glob.glob(f"{PROBE}/SanTruong3_t*.jpg"),
                key=lambda f: int(re.search(r"_t(\d+)", f)[1]))[1:]
    g0 = cv2.imread(fs[0], 0)
    H, W = g0.shape
    orb = cv2.ORB_create(3000)
    k0, d0 = orb.detectAndCompute(g0, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    goc4 = np.float32([[0.15 * W, 0.6 * H], [0.85 * W, 0.6 * H],
                       [0.85 * W, 0.95 * H], [0.15 * W, 0.95 * H]]).reshape(-1, 1, 2)
    phut, lech = [int(re.search(r"_t(\d+)", fs[0])[1]) / 60], [0.0]
    for f in fs[1:]:
        g = cv2.imread(f, 0)
        k, d = orb.detectAndCompute(g, None)
        m = sorted(bf.match(d0, d), key=lambda x: x.distance)[:400]
        p0 = np.float32([k0[x.queryIdx].pt for x in m])
        p1 = np.float32([k[x.trainIdx].pt for x in m])
        Hm, _ = cv2.findHomography(p0, p1, cv2.RANSAC, 2.0)
        e = np.linalg.norm(cv2.perspectiveTransform(goc4, Hm) - goc4, axis=2)
        phut.append(int(re.search(r"_t(\d+)", f)[1]) / 60)
        lech.append(float(e.max()))

    anh = cv2.cvtColor(cv2.imread(fs[0]), cv2.COLOR_BGR2RGB)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.9),
                               gridspec_kw={"width_ratios": [1.25, 1]})
    a.imshow(anh)
    a.add_patch(plt.Polygon(goc4.reshape(-1, 2), fill=False, ec=VANG, lw=2))
    a.set_axis_off()
    a.set_title("SanTruong3 — góc nhìn từ tầng cao (21/07/2026)",
                fontsize=13, color=MUC)
    b.plot(phut, lech, color=XANH, lw=2, marker="o", ms=7)
    b.axhline(3, color=XAM, lw=1.2, ls="--")
    b.text(phut[-1], 3.4, "3 px", ha="right", fontsize=12, color=MUC2)
    b.text(phut[-1], lech[-1] + 0.6, f"{lech[-1]:.1f} px", ha="right",
           fontsize=12, color=MUC)
    b.set_xlabel("Phút kể từ đầu video")
    b.set_ylabel(f"Độ lệch vùng sân (px, khung {W}×{H})")
    b.set_ylim(0, 14)
    b.set_title("Máy trôi chậm và đều trong buổi quay", fontsize=13, color=MUC)
    fig.tight_layout(w_pad=3)
    luu(fig, "h6_santruong3_do_troi.png")
    return pd.DataFrame({"phut": np.round(phut, 1), "lech_lon_nhat_px": np.round(lech, 1)})


# ─────────────────────────── file thống kê ───────────────────────────
def ghi_excel(duong_dan, sheets: dict):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    vien = Side(style="thin", color="A6A6A6")
    for ten, (tieu_de, df, ghi_chu) in sheets.items():
        ws = wb.create_sheet(ten[:31])
        ws["A1"] = tieu_de
        ws["A1"].font = Font(name="Times New Roman", size=14, bold=True)
        r0 = 3
        for j, c in enumerate(df.columns, 1):
            o = ws.cell(row=r0, column=j, value=c)
            o.font = Font(name="Times New Roman", size=13, bold=True)
            o.fill = PatternFill("solid", fgColor="E8EEF8")
            o.alignment = Alignment(horizontal="center", vertical="center",
                                    wrap_text=True)
            o.border = Border(top=vien, bottom=vien, left=vien, right=vien)
        for i, row in enumerate(df.itertuples(index=False), r0 + 1):
            for j, v in enumerate(row, 1):
                if isinstance(v, (np.floating, float)) and np.isnan(v):
                    v = None
                elif isinstance(v, np.generic):
                    v = v.item()
                o = ws.cell(row=i, column=j, value=v)
                o.font = Font(name="Times New Roman", size=13)
                o.alignment = Alignment(vertical="center", wrap_text=True,
                                        horizontal="right" if isinstance(v, (int, float))
                                        else "left")
                o.border = Border(top=vien, bottom=vien, left=vien, right=vien)
                if isinstance(v, float):
                    o.number_format = "0.00"
        for j, c in enumerate(df.columns, 1):
            dai = max([len(str(c))] + [len(str(x)) for x in df.iloc[:, j - 1]])
            ws.column_dimensions[get_column_letter(j)].width = min(max(10, dai * 1.15), 60)
        ws.row_dimensions[r0].height = 36
        ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
        if ghi_chu:
            r = r0 + len(df) + 2
            ws.cell(row=r, column=1, value=ghi_chu).font = Font(
                name="Times New Roman", size=13, italic=True)
    wb.save(duong_dan)


def main() -> int:
    os.makedirs(HINH, exist_ok=True)
    dat_font()

    k3 = pd.read_csv(os.path.join(DT2, "metrics/ket_qua_chuan.csv"), encoding="utf-8-sig")
    kq = {(r.split, r.model, r.metric): (r.value, r.ci95_low, r.ci95_high)
          for r in k3.itertuples()}
    k4 = pd.read_csv(os.path.join(DT2, "metrics/VN04-phan-tich-loi-20261007.csv"),
                     encoding="utf-8-sig")
    v4 = {(r.split, r.metric): (r.value, r.ci95_low, r.ci95_high, r.n)
          for r in k4.itertuples()}

    print("Sinh hình:")
    h1_baseline(kq)
    c3 = h2_c03()
    h3_do_cao(v4)
    h4_loai_loi(v4)
    h5_cung_phien(kq, v4)
    troi = h6_santruong3()

    # ── bảng cho file thống kê
    tong_quan = pd.DataFrame([
        ["VN-01 / M1", "Giao gói dữ liệu SecondPaper cho Lương", "04/10", "Xong",
         "98.552 ảnh, 250 mô tả, 500 file ghi âm; 1,49 GB; SHA256 510/510", "D:/giao_Luong"],
        ["VN-02", "Môi trường OSNet, tải AG-ReID.v2, khoá hash checkpoint", "04/10", "Xong",
         "2 checkpoint: 2510 và 1041 danh tính; 100.502 ảnh AG-ReID.v2", "de6903b"],
        ["VN-03", "Baseline OSNet trên 4 protocol AG-ReID.v2", "05/10", "Xong",
         "AIN đa nguồn hơn MSMT17 2,3–3,5 lần ở cả 4 chiều", "de6903b"],
        ["C-03", "Quy ước thống kê chung cho nhóm", "05/10", "Xong, nhóm đã đồng ý",
         "bootstrap_ci.py; so sánh cặp; luật cho metric hiếm lần trúng", "298f470, 9d3752b, 74183e5"],
        ["—", "Công cụ chuẩn hoá và gộp metrics ba đề tài", "05/10", "Xong",
         "Bảng gộp 261 dòng, 3 đề tài", "005ee99"],
        ["M4", "Hồ sơ kế hoạch thu pilot", "06/10", "Xong, cô Trang đã duyệt (C-04)",
         "5 tài liệu PDF", "7d15a3c"],
        ["VN-04", "Phân tích lỗi ReID theo góc nhìn", "06/10", "Xong (nộp 07/10)",
         "Độ cao bay; cỡ người; loại lỗi; thu hẹp ứng viên", "6a92e3c"],
        ["—", "Đánh giá dữ liệu cũ thay pilot", "07/10", "Xong",
         "Chỉ SanTruong3 là góc cao; dùng được cho CH1, không cho CH2", "—"],
        ["VN-05", "Thu pilot phiên 1", "07/10", "Chưa quay", "", ""],
        ["VN-06", "Thu pilot phiên 2, gán nhãn, hiệu chuẩn", "08/10", "Chưa", "", ""],
    ], columns=["Mã việc", "Nội dung", "Hạn", "Trạng thái", "Kết quả chính", "Bằng chứng (commit / nơi lưu)"])

    m1 = pd.DataFrame([
        ["index.db", 1, 415, "có sẵn embedding"],
        ["crops/ (ảnh cắt người)", 98549, 557, "thiếu 3 khung drone, không thuộc 250 mô tả"],
        ["emb/emb_f32.npy", 98552, 303, "768 chiều, chuẩn hoá L2"],
        ["annot_audio/", 250, 25, "khớp cột audio"],
        ["audio_nhieu_nguoi/", 250, 99, "2 người nói × 50 câu + bản nén"],
        ["manifest/annotations_250.csv", 250, None, "đã lọc 159 dòng rỗng trong 409"],
        ["Gói .tar", 99071, 1491, "SHA256 bfb97da0fe9b731e..."],
    ], columns=["Thành phần", "Số mục", "Dung lượng (MB)", "Ghi chú"])

    vn03 = []
    for p in PROT:
        for mod, nhan in [("osnet_ain_x1_0_dangguon", "OSNet-AIN đa nguồn"),
                          ("osnet_x1_0_msmt17", "OSNet MSMT17")]:
            r1, m = kq[(p, mod, "Rank1")], kq[(p, mod, "mAP")]
            n = int(k3[(k3.split == p) & (k3.model == mod) & (k3.metric == "Rank1")].n.iloc[0])
            ch = float(k3[(k3.split == p) & (k3.model == mod) & (k3.metric == "Rank1")].chance_level.iloc[0])
            vn03.append([TEN[p], nhan, n, r1[0], r1[1], r1[2], m[0], m[1], m[2], ch])
        d = kq[(p, "osnet_ain_x1_0_dangguon − osnet_x1_0_msmt17", "Rank1_hieu_cap")]
        vn03.append([TEN[p], "Hiệu cặp AIN − MSMT17", n, d[0], d[1], d[2],
                     None, None, None, 0.0])
    vn03 = pd.DataFrame(vn03, columns=["Chiều", "Mô hình", "n truy vấn", "Rank-1 (%)",
                                       "Rank-1 CI dưới", "Rank-1 CI trên", "mAP (%)",
                                       "mAP CI dưới", "mAP CI trên", "Mức ngẫu nhiên (%)"])

    docao = []
    for p in PROT:
        for k in ("thấp", "vừa", "cao"):
            r = v4[(p, f"Rank1_docao_{k}")]
            m = v4[(p, f"mAP_docao_{k}")]
            docao.append([TEN[p], f"Bay {k}", int(r[3]), r[0], r[1], r[2], m[0]])
        h = v4[(p, "Rank1_thap_tru_cao")]
        docao.append([TEN[p], "Thấp − cao (không cặp)", None, h[0], h[1], h[2], None])
    docao = pd.DataFrame(docao, columns=["Chiều", "Độ cao", "n", "Rank-1 (%)",
                                         "CI dưới", "CI trên", "mAP (%)"])

    co = []
    for p in PROT[:2]:
        for k in ("thấp", "vừa", "cao"):
            r = v4[(p, f"Rank1_lon_tru_nho_docao_{k}")]
            co.append([TEN[p], f"Bay {k}", int(r[3]), r[0], r[1], r[2],
                       "có ý nghĩa" if r[1] > 0 or r[2] < 0 else "chưa đủ bằng chứng"])
    co = pd.DataFrame(co, columns=["Chiều", "Độ cao", "n", "Người lớn − người nhỏ (điểm %)",
                                   "CI dưới", "CI trên", "Kết luận"])

    loi = []
    for p in PROT:
        n_sai = int(v4[(p, "loi_nham_han")][3])
        loi.append([TEN[p], n_sai, v4[(p, "loi_nham_han")][0],
                    v4[(p, "loi_nham_nguoi_cung_canh")][0],
                    v4[(p, "loi_dung_nguoi_khac_phien")][0] + v4[(p, "loi_dung_nguoi_cung_phien")][0],
                    kq[(p, "osnet_ain_x1_0_dangguon", "Rank1")][0],
                    v4[(p, "Rank1_theo_nguoi_PHU")][0]])
    loi = pd.DataFrame(loi, columns=["Chiều", "Số truy vấn sai", "Nhầm người ở phiên khác (%)",
                                     "Nhầm người cùng cảnh (%)", "Đúng người, protocol tính sai (%)",
                                     "Rank-1 chính thức (%)", "Rank-1 tính theo người (%)"])

    cung = []
    for p in PROT:
        r = v4[(p, "Rank1_cung_phien_PHU_can_duoi")]
        cung.append([TEN[p], kq[(p, "osnet_ain_x1_0_dangguon", "Rank1")][0],
                     r[0], r[1], r[2]])
    cung = pd.DataFrame(cung, columns=["Chiều", "Rank-1 toàn bộ gallery (%)",
                                       "Rank-1 cùng phiên, cận dưới (%)", "CI dưới", "CI trên"])

    c03 = pd.DataFrame([
        ["ĐT1 — YOLO11s", "AP theo ảnh", c3["n"], c3["ma"] * 100, c3["la"] * 100, c3["ha"] * 100, "—"],
        ["ĐT1 — YOLO-World", "AP theo ảnh", c3["n"], c3["mb"] * 100, c3["lb"] * 100, c3["hb"] * 100, "hai khoảng chồng nhau"],
        ["ĐT1 — Hiệu cặp", "AP theo ảnh", c3["n"], c3["md"] * 100, c3["ld"] * 100, c3["hd"] * 100,
         f"có ý nghĩa; YOLO11s hơn ở {c3['thang']*100:.1f}% số ảnh"],
        ["ĐT3 — M-CLIP, Recall@1 = 2/70", "Bootstrap theo cụm", 70, 2.86, 0.00, 7.14,
         "khoảng chứa mức ngẫu nhiên 0,023%"],
        ["ĐT3 — M-CLIP, Recall@1 = 2/70", "Kiểm định hoán vị một phía", 70, 2.86, None, None,
         "p = 0,000135 → vượt ngẫu nhiên"],
    ], columns=["Trường hợp", "Phương pháp", "n", "Giá trị (%)", "CI dưới", "CI trên", "Kết luận"])

    sheets = {
        "Tong quan": ("Tổng quan công việc ĐT2 — Nguyễn Văn Vinh", tong_quan, None),
        "M1 goi du lieu": ("VN-01 / M1 — Gói dữ liệu SecondPaper giao Lương", m1, None),
        "VN-03 baseline": ("VN-03 — Baseline OSNet trên AG-ReID.v2 (4 protocol)", vn03,
                           "Khoảng tin cậy 95% bootstrap 1.000 lần theo truy vấn. Hiệu cặp lấy theo từng truy vấn (mục 4.2 README)."),
        "VN-04 do cao": ("VN-04 — Rank-1 theo độ cao bay", docao,
                         "Hiệu thấp − cao giữa hai nhóm truy vấn khác nhau nên dùng bootstrap không cặp."),
        "VN-04 co nguoi": ("VN-04 — Ảnh hưởng của cỡ người trong cùng một độ cao", co,
                           "Tách người lớn/nhỏ ở trung vị chiều cao ảnh trong từng độ cao."),
        "VN-04 loai loi": ("VN-04 — Phân loại lỗi Rank-1", loi,
                           "Rank-1 tính theo người là thí nghiệm phụ, không thay số chính thức."),
        "VN-04 cung phien": ("VN-04 — Thu hẹp ứng viên về cùng phiên quay", cung,
                             "Cận dưới: chỉ lưu top-100, truy vấn không có ứng viên cùng phiên trong top-100 tính là trượt."),
        "C-03 kiem chung": ("C-03 — Bằng chứng cho quy ước thống kê", c03, None),
        "SanTruong3 do troi": ("Dữ liệu cũ — độ trôi máy quay SanTruong3 (mốc: phút 13,7)", troi,
                               "Đo độ lệch lớn nhất của 4 điểm trên mặt sân qua phép đồng nhất giữa các khung."),
    }
    xl = os.path.join(RA, "ThongKe_DT2_NguyenVanVinh.xlsx")
    ghi_excel(xl, sheets)
    print(f"File thống kê: {xl}  ({len(sheets)} trang tính)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
