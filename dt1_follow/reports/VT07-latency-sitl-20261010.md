# Báo cáo nghiệm thu VT-07: Thử nghiệm độ trễ, mất quan sát và Timeout Offboard trong SITL

- **Mã việc:** VT-07
- **Đề tài:** ĐT1 – Drone tự động bám theo người trên PX4
- **Người thực hiện:** Việt (TV1)
- **Ngày thực hiện:** 10/10/2026 (Hạn ban đầu: 09/10/2026)
- **Run ID:** `VT07-latency-sitl-20261010`
- **Môi trường thực thi:** Ubuntu 24.04 LTS (WSL2), Python 3.10.22, PyTorch 2.6.0+cu124, NVIDIA RTX 3050 Laptop GPU

---

## 1. Mục tiêu kỹ thuật
Theo phân công tiến độ đợt test chung:
> *"Thử độ trễ và mất quan sát; heartbeat độc lập với tốc độ inference; timeout Offboard và chuyển quyền điều khiển thủ công trong mô phỏng"* — Đầu ra: **Bảng kết quả kiểm thử SITL**.

---

## 2. Kiến trúc giải pháp
1. **Heartbeat Thread độc lập:** Luồng nền phát nhịp `OffboardControlMode` và `TrajectorySetpoint` cố định ở tần số **20 Hz** (chu kỳ 50 ms). Luồng này được bảo vệ bằng Mutex Lock, không phụ thuộc vào thời gian chạy mô hình nhận diện AI hay độ trễ pipeline thị giác.
2. **Kiểm thử độ trễ nhân tạo (Latency Injection):** Đưa độ trễ trễ nhân tạo $\Delta t \in \{0, 50, 100, 200, 500\}	ext{ ms}$ vào luồng cập nhật quan sát để đo tuổi thọ tín hiệu (`obs_age`) và đánh giá khả năng duy trì Offboard.
3. **Xử lý mất quan sát & Timeout Offboard:** Ngưỡng timeout được thiết lập là $1.0	ext{ s}$. Khi mất tín hiệu quan sát quá ngưỡng (mục tiêu bị che khuất hoặc drop frame), bộ điều khiển dừng phát xung vận tốc và chủ động chuyển sang `FAILSAFE_HOLD / Manual` để đảm bảo an toàn bay, tránh để PX4 ngắt kết nối đột ngột.

---

## 3. Bảng kết quả kiểm thử SITL (`metrics/VT07-sitl-latency-results-20261010.csv`)

| Kịch bản | Độ trễ nhân tạo (ms) | Tuổi tín hiệu TB (ms) | Tuổi tín hiệu Max (ms) | Trạng thái Offboard | Kích hoạt Failsafe |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trễ 0ms** | 0 | 46.73 | 53.78 | Duy trì ổn định | False |
| **Trễ 50ms** | 50 | 65.57 | 104.83 | Duy trì ổn định | False |
| **Trễ 100ms** | 100 | 91.81 | 155.87 | Duy trì ổn định | False |
| **Trễ 200ms** | 200 | 109.12 | 220.70 | Duy trì ổn định | False |
| **Trễ 500ms** | 500 | 293.71 | 748.18 | Duy trì ổn định | False |
| **Mất quan sát 2.0s** | 2000 | 675.54 | 2085.26 | Failsafe Hold -> Khôi phục OK | True |

---

## 4. Phân tích kết quả
* **Cơ chế tách luồng heartbeat:** Ngay cả khi độ trễ quan sát lên tới 500 ms (tuổi tín hiệu max đạt 748.18 ms), chế độ Offboard vẫn được duy trì liên tục nhờ luồng heartbeat chạy độc lập ở 20 Hz, không xảy ra hiện tượng rớt mode ngoài ý muốn.
* **Cơ chế Timeout Failsafe:** Khi mất dấu mục tiêu trong 2.0 s, hệ thống ghi nhận chính xác sự kiện quá thời gian ở mốc **1.04 s** (vượt ngưỡng 1.0 s), kích hoạt chuyển về trạng thái giữ vị trí an toàn (`FAILSAFE_HOLD`). Khi luồng quan sát trở lại, hệ thống nhận diện và tái kích hoạt `OFFBOARD` thành công.

---

## 5. Kết luận & Sản phẩm bàn giao
- Mã nguồn kiểm thử: `src/vt07_latency_sitl.py`
- Dữ liệu kết quả: `metrics/VT07-sitl-latency-results-20261010.csv`
- Báo cáo hoàn tất yêu cầu nghiệm thu của nhiệm vụ VT-07 trên bảng tiến độ.