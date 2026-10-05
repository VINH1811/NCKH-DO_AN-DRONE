# Quy ước diễn giải thống kê đề xuất — 05/10/2026

Phạm vi: ĐT3, bản đề xuất để nhóm thống nhất. Chưa sửa README chung của nhóm.
Giữ CSV 17 cột, không chạy hoặc xem kết quả test để hoàn thiện tài liệu này.
Chưa có nguyên văn CH3 của đề tài 7; không khẳng định văn bản này đáp ứng toàn bộ CH3.

## Câu đưa vào quy ước

> Mỗi metric phải báo cáo n, đơn vị lấy mẫu, mức ngẫu nhiên, CI 95% và phương pháp tính.
> Nếu CI hợp lệ đã chọn trước bao gồm mức ngẫu nhiên, ghi rõ: “Chưa đủ bằng chứng rằng metric khác mức ngẫu nhiên với dữ liệu và phương pháp hiện tại”.
> Không diễn giải điều đó thành “mô hình bằng ngẫu nhiên”, “mô hình vô dụng” hoặc “không kết luận được bất kỳ điều gì”.
> Với ít hoặc không có lần trúng, bootstrap percentile có thể cho cận suy biến; phải kiểm tra phương pháp trước khi dùng CI để kết luận.
> Cỡ mẫu cần thiết phải gắn với mục tiêu (độ chính xác ước lượng hoặc power), effect size, alpha, đơn vị độc lập và cách lấy mẫu; không áp dụng một n tối thiểu chung cho mọi metric.

Với các metric chính đã chọn trước: CI hoàn toàn trên chance là bằng chứng vượt baseline ngẫu nhiên theo protocol;
CI cắt chance chưa đủ bằng chứng theo CI đó; CI hoàn toàn dưới chance là bằng chứng kém baseline theo protocol.
Nếu kiểm định nhiều metric/model, phải định trước metric chính hoặc xử lý đa kiểm định.
Vượt ngẫu nhiên không đồng nghĩa độ chính xác đáp ứng nhu cầu vận hành.

## Recall@1 = 2/70: vì sao bootstrap có cận 0?

Baseline hiện tại: 2,857%; bootstrap theo track cho CI [0; 7,353]%; chance = 1/4.272 = 0,023408%.
Một số mẫu bootstrap không chứa track trúng, nên percentile 2,5% bằng 0.
Đây là giới hạn cần chú ý của phương pháp trong trường hợp hiếm lần trúng, không phải lỗi tính rank.

Đối chiếu nếu giả định 70 phép thử Bernoulli độc lập, cùng xác suất:

- Wilson 95%: [0,787; 9,832]%.
- Clopper–Pearson exact 95%: [0,348; 9,943]%.
- Binomial một phía so với p0=1/4.272: p≈0,00013093.

Các số này cho thấy cận bootstrap 0 không tự động chứng minh “n=70 không thể kết luận”.
Nhưng phép tính nhị thức độc lập **không phải kết luận chính thức cho bộ truy vấn có tương quan**:
nhiều câu có thể cùng track, track/camera có thể tương quan và ground truth chỉ có một relevant.
Không đổi phương pháp sau khi xem số chỉ để lấy CI thuận lợi. Cần thống nhất phương pháp và giả định cho các lần đánh giá sau;
có thể trình bày đối chiếu trên dev hiện tại, kèm giới hạn, rồi giữ phương pháp cố định cho test.

Nguồn phương pháp Wilson và exact:
https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm

## Báo cáo 250 câu và vai trò dev/test

Không mở test hiện tại chỉ để tăng n làm đẹp CI. Dev còn dùng so mô hình, ngôn ngữ, cách gộp track và chọn ngưỡng.
Test là đánh giá cuối sau khi khóa mọi cấu hình, không chỉ dành cho đánh giá ngưỡng từ chối.

Giữ lịch:

1. Ngày 05/10: báo cáo dev, n=70 edata và n=6 video; không gọi đó là kết quả toàn bộ 250 câu.
2. Ngày 06–09/10: phát triển/chọn cấu hình trên dev.
3. Ngày 10/10: báo cáo test giữ lại, n=158 edata và n=16 video, theo config cuối đã khóa.
4. Có thể thêm kết quả mô tả toàn bộ 250 câu sau khi chạy cấu hình cố định trên cả dev và test,
   nhưng gắn nhãn “gộp dev+test, có dữ liệu dùng phát triển”, không dùng để ước lượng hiệu năng trên dữ liệu chưa thấy.

250 câu không phải đều thuộc 9 camera: 228 edata và 22 video, gallery khác nhau (4.272 và 32.404 track).
Kết quả chính về 9 camera cần báo cáo edata riêng; nếu thêm tổng hợp phải nêu cách gộp theo truy vấn/source,
chance tương ứng và CI có xử lý nhóm. Không dùng chance=1/4.272 cho toàn bộ 250 câu.
Không lấy trung bình đơn giản giữa các percentile latency của hai nguồn.

Nguồn về nguy cơ chọn cấu hình qua test:
https://scikit-learn.org/stable/modules/cross_validation.html

## Không có n tối thiểu chung

Hai mục tiêu khác nhau cho hai cỡ mẫu rất khác nhau. Ví dụ thiết kế với truy vấn độc lập:

| Mục tiêu | Giả định thiết kế | Cỡ mẫu |
|---|---|---:|
| Phát hiện Recall@1=3% vượt chance=1/4.272 | Kiểm định binomial exact một phía, alpha=0,05, power≥80% | n=53, critical hits=1, power≈80,10% |
| Ước lượng tỷ lệ với sai số xấp xỉ ±2 điểm phần trăm | CI 95%, p thiết kế≈2/70; công thức xấp xỉ chuẩn | n≈267 |
| Ước lượng với sai số xấp xỉ ±1 điểm phần trăm | CI 95%, p thiết kế≈2/70; công thức xấp xỉ chuẩn | n≈1.067 |
| Sai số xấp xỉ ±2 điểm phần trăm khi chưa biết p | Thiết kế bảo thủ p=0,5, CI 95%, công thức xấp xỉ chuẩn | n≈2.401 |

Công thức độ chính xác: n≈ceil(z_0,975² p(1-p)/epsilon²). Đây là con số hoạch định xấp xỉ,
không bảo đảm CI exact/Wilson có đúng độ rộng ấy và không phải khuyến nghị cuối cho dự án.
p thiết kế lấy từ pilot hiếm lần trúng cũng không chắc chắn; cần phân tích nhiều p dự kiến.

Các n trên là số phép thử độc lập, không phải số mô tả sau khi viết lại câu đồng nghĩa.
Nếu gộp theo track/camera phải xét tương quan, số nhóm và lấy mẫu camera/ngày;
có thể hoạch định bằng mô phỏng/resampling theo nhóm từ pilot. Thêm câu cho cùng người không tự động thêm bằng chứng độc lập.
Các metric mAP, chênh lệch giữa hai mô hình, tỉ lệ báo nhầm trên ca không có đáp án và p95 latency cần thiết kế riêng.
Không áp dụng n=53 hay n≈267 cho chúng.

## Cách ghi ngắn cho bảng tiến độ

“Baseline M1 dev: Recall@1=2/70 (2,86%), CI bootstrap theo track=[0–7,35]%, chance=0,0234%.
CI bootstrap bao gồm chance; chưa đủ bằng chứng theo CI đã dùng. Cận 0 cần diễn giải thận trọng vì hiếm lần trúng.
Test n=174 vẫn giữ kín; cỡ mẫu bổ sung chưa chốt vì cần thống nhất mục tiêu độ chính xác/power và đơn vị lấy mẫu.”
