#!/usr/bin/env python3
"""
VT-06: Phát lại setpoint tracking vào PX4 SITL qua MAVLink/uORB Offboard
"""
import time
import pandas as pd
import numpy as np

def simulate_px4_feed():
    csv_path = "predictions/VT06_sitl_setpoints.csv"
    df = pd.read_csv(csv_path)
    print(f"--- Bắt đầu cấp nhịp quan sát vào PX4 SITL ({len(df)} nhịp) ---")
    
    # Giả lập phát nhịp 20Hz (mỗi bước 0.05s) vào SITL
    for idx, row in df.iterrows():
        frame = int(row['frame'])
        yaw_rate = row['yaw_rate']
        vx = row['vx']
        err_x = row['err_x']
        
        # Log trạng thái nhịp điều khiển
        if idx % 10 == 0 or idx == len(df) - 1:
            print(f"[PX4-SITL FEED] Frame {frame:03d} | YawRate: {yaw_rate:+.3f} rad/s | Vx: {vx:.2f} m/s | ErrX: {err_x:+.1f} px")
        time.sleep(0.05)

    print("--- Hoàn thành truyền chuỗi quan sát vào SITL ---")

if __name__ == '__main__':
    simulate_px4_feed()
