# -*- coding: utf-8 -*-
"""VN-06 (CH1) — MÔ PHỎNG sai số định vị bằng homography khi chưa có pilot.

Chưa có bảng điểm mốc đo bằng thước (M5) nên chưa đo được sai số THẬT. Thay vào
đó mô phỏng đúng quy trình VN-06 sẽ làm ngoài sân: hiệu chuẩn bằng 4 điểm mốc,
rồi đo sai số tại các điểm KHÔNG dùng để hiệu chuẩn. Kết quả là NGÂN SÁCH SAI SỐ
— cho biết nguồn sai nào đáng lo trước khi ra sân — không phải sai số thực địa.

Đầu vào đo được từ dữ liệu thật của đề tài:
  - độ rung điểm chân giữa các khung: 0,39% chiều cao người
    (trung vị 4 video SecondPaper, ~2.500 track, phần dư sau trung bình trượt 5 khung)
  - độ trôi máy quay SanTruong3: 11,6 px sau ~2 giờ, dưới 3 px trong 30 phút đầu,
    trên khung 640 px -> nhân 3 cho khung 1920 px

Đầu vào GIẢ ĐỊNH (ghi rõ trong báo cáo):
  - điện thoại 1920x1080, góc ngang 69 độ (ống kính chính thường gặp)
  - sai số thước dây 2 cm, sai số bấm điểm trên ảnh 1,5 px
  - sai lệch hệ thống của điểm chân 0 / 3 / 6% chiều cao người
  - hai cấu hình máy: chân máy nâng 2,5 m và tầng cao 15 m

Chạy:  python dt2_handoff/src/vn06_mo_phong_dinh_vi.py
"""
from __future__ import annotations

import csv
import io
import os
import sys
from datetime import date

import cv2
import numpy as np

DT2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ID = "VN06-mo-phong-dinh-vi-20261010"
W, H = 1920, 1080
FX = (W / 2) / np.tan(np.radians(69 / 2))
CAO_NGUOI = 1.65
RUNG_CHAN = 0.0039                     # đo được
TROI_30P, TROI_2H = 3 * 3.0, 3 * 11.6  # px trên khung 1920 (đo trên 640, nhân 3)
SAI_THUOC, SAI_BAM = 0.02, 1.5
N_THU, N_DIEM = 2000, 200

CAU_HINH = {
    # tên: (độ cao m, nhìn trúng mặt đất ở khoảng cách m, vùng hiệu chuẩn X, Z)
    "Chân máy 2,5 m": (2.5, 12.0, (-3.0, 3.0), (5.0, 20.0)),
    "Tầng cao 15 m": (15.0, 20.0, (-10.0, 10.0), (11.0, 35.0)),
}


def chieu(X, Z, Y, h, th):
    """Điểm (X, Y, Z) trong hệ mặt đất -> pixel. Máy ở độ cao h, chúc xuống góc th."""
    vy = Y - h
    yc = -vy * np.cos(th) - Z * np.sin(th)
    zc = -vy * np.sin(th) + Z * np.cos(th)
    return np.stack([W / 2 + FX * X / zc, H / 2 + FX * yc / zc], -1)


def mot_lan(rng, h, th, vx, vz, he_thong, troi, ngoai_suy, rung=True):
    goc = np.array([[vx[0], vz[0]], [vx[1], vz[0]], [vx[1], vz[1]], [vx[0], vz[1]]])
    anh = chieu(goc[:, 0], goc[:, 1], 0.0, h, th)
    anh_do = anh + rng.normal(0, SAI_BAM, anh.shape)
    goc_do = goc + rng.normal(0, SAI_THUOC, goc.shape)
    Hm = cv2.getPerspectiveTransform(anh_do.astype(np.float32), goc_do.astype(np.float32))

    if ngoai_suy:      # điểm nằm NGOÀI vùng hiệu chuẩn, sâu thêm 50%
        Z = rng.uniform(vz[1], vz[1] + 0.5 * (vz[1] - vz[0]), N_DIEM)
    else:
        Z = rng.uniform(*vz, N_DIEM)
    X = rng.uniform(*vx, N_DIEM)
    chan = chieu(X, Z, 0.0, h, th)
    dau = chieu(X, Z, CAO_NGUOI, h, th)
    cao_px = np.abs(chan[:, 1] - dau[:, 1])
    p = chan.copy()
    p += rng.normal(0, 1, p.shape) * ((RUNG_CHAN if rung else 0.0) * cao_px)[:, None]
    p[:, 1] += rng.normal(0, 1, N_DIEM) * he_thong * cao_px
    if troi > 0:
        g = rng.uniform(0, 2 * np.pi)
        p += troi * np.array([np.cos(g), np.sin(g)])
    uoc = cv2.perspectiveTransform(p.reshape(-1, 1, 2).astype(np.float32), Hm).reshape(-1, 2)
    return np.hypot(uoc[:, 0] - X, uoc[:, 1] - Z)


def main() -> int:
    rng = np.random.default_rng(0)
    kich_ban = [
        ("1. Chỉ sai số hiệu chuẩn (thước + bấm điểm)", 0.0, 0.0, False, False),
        ("2. + rung điểm chân (đo được)", 0.0, 0.0, False, True),
        ("3. + sai lệch điểm chân 3%", 0.03, 0.0, False, True),
        ("4. + sai lệch điểm chân 6%", 0.06, 0.0, False, True),
        ("5. Như 3 + máy trôi 30 phút", 0.03, TROI_30P, False, True),
        ("6. Như 3 + máy trôi 2 giờ", 0.03, TROI_2H, False, True),
        ("7. Như 3, điểm NGOÀI vùng hiệu chuẩn", 0.03, 0.0, True, True),
    ]
    hang = []
    for ten_ch, (h, nhin, vx, vz) in CAU_HINH.items():
        th = np.arctan2(h, nhin)
        goc = chieu(np.array([vx[0], vx[1]]), np.array([vz[0], vz[0]]), 0.0, h, th)
        assert (goc[:, 0] > 0).all() and (goc[:, 0] < W).all(), "vùng hiệu chuẩn tràn khung"
        print(f"\n=== {ten_ch} (chúc {np.degrees(th):.1f}°, vùng {vx[1]-vx[0]:.0f}×{vz[1]-vz[0]:.0f} m) ===")
        for ten_kb, ht, troi, ngoai, co_rung in kich_ban:
            sai = []
            for _ in range(N_THU):
                sai.append(mot_lan(rng, h, th, vx, vz, ht, troi, ngoai, rung=co_rung))
            sai = np.concatenate(sai)
            med, p95 = np.median(sai), np.percentile(sai, 95)
            print(f"  {ten_kb:<46} trung vị {med:5.2f} m   p95 {p95:5.2f} m")
            for metric, v in (("sai_so_dinh_vi_trung_vi_m", med), ("sai_so_dinh_vi_p95_m", p95)):
                hang.append({"run_id": RUN_ID, "date": date.today().isoformat(), "commit": "",
                             "task_id": "VN-06", "dataset": "mo phong (khong phai thuc dia)",
                             "split": f"{ten_ch} | {ten_kb}", "model": "homography 4 diem",
                             "checkpoint_sha256": "", "precision": "fp64", "metric": metric,
                             "value": round(float(v), 4), "ci95_low": "", "ci95_high": "",
                             "n": len(sai), "chance_level": "", "hardware": "CPU",
                             "notes": "rung chan 0,39% va do troi la so do; con lai la gia dinh"})
    ra = os.path.join(DT2, "metrics", f"{RUN_ID}.csv")
    with io.open(ra, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(hang[0].keys()))
        w.writeheader()
        w.writerows(hang)
    print(f"\nĐã ghi {len(hang)} dòng -> {ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
