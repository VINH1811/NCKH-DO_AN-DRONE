#!/usr/bin/env python3
"""
VT-06: Kịch bản phát lại quỹ đạo quan sát (Replay Observation SITL)
Đầu vào: Chuỗi tracking từ VT-05 (sequence uav0000086_00000_v.txt)
Lưu ý: Kịch bản mô phỏng phát lại quan sát (open-loop replay),
       ghi rõ không phải đánh giá perception vòng kín theo quy định VT-06.
"""

import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

def run_replay():
    pred_file = Path("predictions/VT05-bytetrack-20261007/uav0000086_00000_v.txt")
    if not pred_file.exists():
        print(f"Lỗi: Không tìm thấy {pred_file}")
        sys.exit(1)

    print(f"--- Đang tải dữ liệu quan sát tracking: {pred_file} ---")
    cols = ['frame', 'id', 'bb_left', 'bb_top', 'bb_width', 'bb_height', 'conf', 'x', 'y', 'z']
    df = pd.read_csv(pred_file, header=None, names=cols)

    # Chọn Track ID 1 (mục tiêu chính xuất hiện xuyên suốt sequence 0086)
    track_1 = df[df['id'] == 1].sort_values('frame').reset_index(drop=True)
    n_frames = len(track_1)
    print(f"-> Đã trích xuất Track ID 1: {n_frames} frames quan sát.")

    # Thông số khung hình camera chuẩn VisDrone
    img_w, img_h = 1920, 1080
    cx, cy = img_w / 2.0, img_h / 2.0

    print("\n--- Bắt đầu kịch bản phát lệnh quan sát vào SITL ---")
    print("Mode: Offboard Replay (Open-loop)")
    print(f"{'Frame':<8}{'Target_X':<12}{'Target_Y':<12}{'Error_X':<10}{'YawRate(rad/s)':<16}{'Vx(m/s)':<10}")

    setpoints = []
    # Tần số mẫu: ~20Hz (mỗi bước ~0.05s)
    for idx, row in track_1.iterrows():
        tx = row['bb_left'] + row['bb_width'] / 2.0
        ty = row['bb_top'] + row['bb_height'] / 2.0
        err_x = tx - cx
        err_y = ty - cy

        # Bộ điều khiển tỉ lệ chuyển đổi lỗi pixel sang vận tốc góc quay Yaw và vận tốc tiến Vx
        k_yaw = 0.0015
        yaw_rate = float(np.clip(k_yaw * err_x, -0.5, 0.5))
        vx = 0.8 if row['conf'] > 0.4 else 0.2

        setpoints.append({
            'frame': int(row['frame']),
            'err_x': err_x,
            'err_y': err_y,
            'yaw_rate': yaw_rate,
            'vx': vx
        })

        if idx % 50 == 0 or idx == n_frames - 1:
            print(f"{int(row['frame']):<8}{tx:<12.1f}{ty:<12.1f}{err_x:<10.1f}{yaw_rate:<16.3f}{vx:<10.2f}")

    out_csv = Path("predictions/VT06_sitl_setpoints.csv")
    pd.DataFrame(setpoints).to_csv(out_csv, index=False)
    print(f"\n-> Đã lưu danh sách lệnh điều khiển quan sát: {out_csv} ({len(setpoints)} bước)")
    print("-> Kịch bản sẵn sàng cấp nhịp cho PX4 SITL.")

if __name__ == '__main__':
    run_replay()
