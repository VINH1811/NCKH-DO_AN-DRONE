#!/usr/bin/env python3
"""
VT-07: Thử nghiệm độ trễ, mất quan sát và cơ chế heartbeat độc lập trong SITL.
Đầu ra: Bảng kết quả kiểm thử và log trạng thái chuyển mode.
"""

import time
import threading
from pathlib import Path
import pandas as pd
import numpy as np

class OffboardControllerSim:
    def __init__(self, heartbeat_hz=20.0, timeout_thresh=1.0):
        self.heartbeat_hz = heartbeat_hz
        self.dt = 1.0 / heartbeat_hz
        self.timeout_thresh = timeout_thresh
        
        self.current_setpoint = {'yaw_rate': 0.0, 'vx': 0.0}
        self.last_observation_time = time.time()
        self.is_running = True
        self.mode = "OFFBOARD"
        self.lock = threading.Lock()
        self.log_history = []

    def start_heartbeat(self):
        self.hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.hb_thread.start()

    def _heartbeat_loop(self):
        """Luồng phát heartbeat độc lập chu kỳ cố định."""
        while self.is_running:
            start_t = time.time()
            now = time.time()
            with self.lock:
                obs_age = now - self.last_observation_time
                if obs_age > self.timeout_thresh and self.mode == "OFFBOARD":
                    self.mode = "FAILSAFE_HOLD"
                    self.current_setpoint = {'yaw_rate': 0.0, 'vx': 0.0}
                    print(f"\n[ALERT] Quá thời gian quan sát ({obs_age:.2f}s > {self.timeout_thresh}s)! Timeout Offboard -> Chuyển sang FAILSAFE_HOLD / Manual.")

                self.log_history.append({
                    'timestamp': now,
                    'mode': self.mode,
                    'obs_age_ms': obs_age * 1000.0,
                    'yaw_rate': self.current_setpoint['yaw_rate'],
                    'vx': self.current_setpoint['vx']
                })
            elapsed = time.time() - start_t
            sleep_time = max(0.0, self.dt - elapsed)
            time.sleep(sleep_time)

    def update_observation(self, yaw_rate, vx, injected_delay_ms=0):
        if injected_delay_ms > 0:
            time.sleep(injected_delay_ms / 1000.0)
        with self.lock:
            self.current_setpoint = {'yaw_rate': yaw_rate, 'vx': vx}
            self.last_observation_time = time.time()
            if self.mode == "FAILSAFE_HOLD":
                self.mode = "OFFBOARD"
                print("\n[INFO] Đã khôi phục quan sát mục tiêu -> Kích hoạt lại OFFBOARD.")

    def stop(self):
        self.is_running = False
        if hasattr(self, 'hb_thread'):
            self.hb_thread.join(timeout=1.0)

def run_vt07_experiments():
    print("==================================================")
    print("   BẮT ĐẦU KIỂM THỬ VT-07: ĐỘ TRỄ VÀ TIMEOUT SITL ")
    print("==================================================")
    
    test_latencies = [0, 50, 100, 200, 500]
    results_summary = []
    
    # 1. Thử nghiệm ảnh hưởng của độ trễ
    for lat in test_latencies:
        print(f"\n---> Chạy kịch bản độ trễ nhân tạo: {lat} ms")
        controller = OffboardControllerSim(heartbeat_hz=20.0, timeout_thresh=1.0)
        controller.start_heartbeat()
        
        # Mô phỏng 20 nhịp quan sát
        for step in range(20):
            err_x = np.sin(step * 0.3) * 150.0
            yaw_rate = float(np.clip(0.0015 * err_x, -0.5, 0.5))
            vx = 0.8
            controller.update_observation(yaw_rate, vx, injected_delay_ms=lat)
            time.sleep(0.05) # Chu kỳ nhận diện tiêu chuẩn
            
        controller.stop()
        df_log = pd.DataFrame(controller.log_history)
        avg_age = df_log['obs_age_ms'].mean()
        max_age = df_log['obs_age_ms'].max()
        offboard_maintained = (df_log['mode'] == 'OFFBOARD').all()
        
        results_summary.append({
            'kịch_bản': f"Trễ {lat}ms",
            'latency_injected_ms': lat,
            'obs_age_avg_ms': round(avg_age, 2),
            'obs_age_max_ms': round(max_age, 2),
            'offboard_status': "Duy trì ổn định" if offboard_maintained else "Mất Offboard",
            'failsafe_triggered': not offboard_maintained
        })
        print(f"     Tuổi tín hiệu TB: {avg_age:.1f} ms | Max: {max_age:.1f} ms | Trạng thái: {'OK' if offboard_maintained else 'Timeout'}")

    # 2. Thử nghiệm mất quan sát và cơ chế chuyển quyền điều khiển
    print("\n---> Chạy kịch bản MẤT QUAN SÁT (Target Loss / Occlusion)")
    controller = OffboardControllerSim(heartbeat_hz=20.0, timeout_thresh=1.0)
    controller.start_heartbeat()
    
    # Giai đoạn 1: Quan sát bình thường trong 1.0s
    for _ in range(15):
        controller.update_observation(yaw_rate=0.2, vx=0.8)
        time.sleep(0.05)
        
    # Giai đoạn 2: Giả lập mất dấu hoàn toàn trong 2.0s
    print("     [Sim] Mục tiêu bị che khuất / Mất quan sát trong 2.0s...")
    time.sleep(2.0)
    
    # Giai đoạn 3: Khôi phục lại quan sát
    print("     [Sim] Tìm lại thấy mục tiêu...")
    for _ in range(10):
        controller.update_observation(yaw_rate=0.1, vx=0.8)
        time.sleep(0.05)
        
    controller.stop()
    df_loss_log = pd.DataFrame(controller.log_history)
    failsafe_occurred = (df_loss_log['mode'] == 'FAILSAFE_HOLD').any()
    recovery_occurred = failsafe_occurred and (df_loss_log.iloc[-1]['mode'] == 'OFFBOARD')
    
    results_summary.append({
        'kịch_bản': "Mất quan sát 2.0s",
        'latency_injected_ms': 2000,
        'obs_age_avg_ms': round(df_loss_log['obs_age_ms'].mean(), 2),
        'obs_age_max_ms': round(df_loss_log['obs_age_ms'].max(), 2),
        'offboard_status': "Failsafe Hold -> Khôi phục OK" if recovery_occurred else "Thất bại",
        'failsafe_triggered': failsafe_occurred
    })

    # Lưu kết quả kiểm thử SITL ra CSV
    out_dir = Path("metrics")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_res = pd.DataFrame(results_summary)
    out_csv = out_dir / "VT07-sitl-latency-results-20261010.csv"
    df_res.to_csv(out_csv, index=False)
    
    print("\n==================================================")
    print(f"-> ĐÃ LƯU BẢNG KẾT QUẢ KIỂM THỬ: {out_csv}")
    print("==================================================")
    print(df_res.to_string(index=False))

if __name__ == '__main__':
    run_vt07_experiments()
