# M9 — Mục tiêu xác minh bàn giao (Vinh → Việt)

**Bản MÔ PHỎNG trên AG-ReID.v2**, vì pilot khuôn viên trường chưa quay. Khi có pilot
thật, file được sinh lại cùng định dạng — mã của Việt không phải đổi.

`muc_tieu_xac_minh.json`: 251 mục tiêu, mỗi mục là một lần ĐT2 đã quyết định bàn giao
(điểm khớp ≥ ngưỡng) ở phiên 2, điều kiện ngoại hình + giới hạn thời gian, chiều
CCTV → UAV.

| Trường | Ý nghĩa |
|---|---|
| `ma_ban_giao` | Mã lần bàn giao, `BG-0001` ... |
| `anh_truy_van_mat_dat` | Ảnh người do camera mặt đất thấy (đường dẫn tương đối trong AG-ReID.v2) |
| `ma_muc_tieu` | Danh tính ĐT2 chọn |
| `anh_mau_muc_tieu_uav` | Tối đa 5 ảnh UAV của mục tiêu — **dùng làm mẫu ngoại hình để drone khoá lại người khi mất dấu** |
| `do_tin` | Cosine giữa ảnh mặt đất và ảnh UAV tốt nhất |
| `nguong` | Ngưỡng bàn giao đã chốt trên phiên 1 (0,7274) |
| `buoi_quay_T`, `do_cao_A` | Buổi quay và mức độ cao bay (0 thấp, 1 vừa, 2 cao) |
| `ket_qua_that_chi_de_danh_gia` | Đúng hay sai theo nhãn thật. **Chỉ để Việt đánh giá, không được đưa vào quyết định bám theo** |

Độ chính xác: 209/251 = **83,3%** là đúng người. Nghĩa là cứ khoảng 6 lần bàn giao thì
1 lần ĐT1 nhận nhầm mục tiêu từ đầu — nên giữ cơ chế xác nhận lại sau khi khoá và
cho phép người điều khiển huỷ.

Chưa có toạ độ mặt đất (AG-ReID.v2 không có). Trường `toa_do` theo bản tin bàn giao sẽ
được thêm khi có hiệu chuẩn homography từ pilot thật.
