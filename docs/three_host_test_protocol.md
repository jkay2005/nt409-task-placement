# Phase 4A — Notebook 20: test ba host đã khóa

Ngày 12/10/2026. Tiếp tục Notebook 19, chỉ nhánh A.

## Câu hỏi và phạm vi

Với mã hóa domain-wall, mean-energy, X mixer và COBYLA giữ nguyên, chất lượng
placement, lift và chi phí thay đổi thế nào giữa các case 4/5 task, 3 host?
Đây là 6 case test nhỏ đã đóng băng, không chứng minh scaling tổng quát hoặc
quantum advantage. Dữ liệu hai host Notebook 16–18 là lịch sử riêng, không là
đối chứng chỉ thay số host. FF/BFD/MILP chưa triển khai trong gói A20.

Checkpoint C2 đã có 8 probe và 14 trial Windows hoàn tất. Ngoại suy theo median
development là 4,39 giờ cho 90 trial. Nfev development 28–71, chưa chạm cap200;
test có thể tốn nhiều hơn. Không cam kết 90 lượt sẽ xong trong 6 giờ.

## Đầu vào và cấu hình cố định

Parent dataset: `data/benchmarks/nt409_three_host_v2`, giữ nguyên cả 10 input,
manifest và protocol pilot. Notebook 20 chỉ đưa 6 instance role `test` vào QAOA:
`a3_test_n4_1..3`, `a3_test_n5_1..3`. Không chọn lại input theo chất lượng pilot.
Notebook 19 và kết quả cũ không bị sửa bởi module mới.

Protocol test riêng: `data/benchmarks/nt409_three_host_test_v1/protocol.json`.
Hash canonical: `ba470c6e96a8b8c560eaaa92463b27b36a22de8ac29ba76d615c5e03433c9266`.

| Thành phần | Giá trị |
|---|---|
| Mã hóa | Hai bit/task: 00→h0,10→h1,11→h2; 01 invalid; giữ y/slack |
| Penalty | Domain4, capacity4; không sửa bit/y sau đo |
| Độ sâu | p1,p2,p3 báo ngang nhau, không chọn p từ development |
| Training | Mean QUBO energy, X mixer, max_abs normalization |
| Optimizer | COBYLA, cap200, rhobeg1,tol1e-4 |
| Shots | Training1024, final1024 với sampler/seed riêng |
| Seed tối ưu | 200,201,202,203,204 |
| Seed final | 100200,100201,100202,100203,100204 |
| Initial point | Beta=[.3,0,...], gamma=[1,0,...]; named parameters kiểm tra |
| Resource | ≤25q, Aer4threads/2048MiB, available ban đầu≥8GiB, reserve≥4GiB, RSS≤4GiB |
| Guard mỗi attempt | Tối đa2400s; bị thu ngắn theo ngân sách còn lại nếu cần |

Năm seed không phải năm initial point. Không gọi đây là multistart.

Thứ tự cố định gồm 5 vòng seed. Mỗi vòng có18 trial, đủ 6 instance×3p. Trong
mỗi nhóm6 lượt, ghép n4/n5 cùng chỉ số và xoay p theo cặp/seed. Không đổi thứ tự
theo chất lượng hoặc thời gian đã quan sát. Nếu hết ngân sách, dừng tại lượt
tiếp theo trong thứ tự đã định; dữ liệu thiếu không được xem là ngẫu nhiên.

## C2, provenance và audit

Trước khi tạo campaign mới, kiểm tra ZIP pilot 19: checksum, manifest/context,
14 trial/8probe, raw counts, semantics, ledger và nguồn code modulo LF/CRLF.
Runtime Windows của pilot được giữ trong evidence, không bị thay bằng runtime
Linux QA. Nguồn 19 phải khớp hiện tại. Campaign test khóa context, protocol,
runtime và hash nguồn gồm 19 modules được kế thừa cùng 2 modules mới.

Các trial vẫn dùng runner 19 nên field scope của report mô tả họ runner
`phase4k_three_host_pilot_v2`; envelope/campaign scope chính thức là
`phase4l_three_host_test_v1`. Input, config và role test trong envelope mới xác
định study. Không sửa report cũ để đổi scope.

18 probe riêng, một cho mỗi instance/p, phải passed trước training. Probe là
kiểm tra tài nguyên, không chọn p và không tính vào success rate test. Mẫu
probe không dùng làm đáp án hoặc training initial point.

Mỗi report completed được audit bit order, Ising/QUBO, physical decoding,
named parameters, seed final, callback/nfev, shot accounting và đầu ra best
valid trong final batch. Có thể thấy placement tối ưu mà không thấy ground
QUBO do slack chưa khớp. Giữ thêm most-frequent/mode diagnostics để minh bạch
quy tắc đầu ra khác chuỗi phổ biến nhất trong đề cương.

## Ngân sách tích lũy và resume

Limit toàn campaign:21600s. Reserve export:60s. Các stage mở campaign, C2 audit,
preprocessing, classical timing, probe, training, verification, analysis/plot
và nén dữ liệu xuất được tính bằng monotonic time; thời gian import/load của
notebook được truyền vào stage mở. Thời gian người dùng nghỉ giữa các stage
đã đóng và render bảng notebook không được tính là thời gian thuật toán.
Một vài thao tác ghi receipt/metadata cuối sau khi đóng timer bị loại khỏi
phép đo, tương tự việc ghi kết quả đo thời gian. Không nén lại toàn bộ ZIP ngoài
timer. Đây là ngân sách tính toán có boundary guard, không phải hard timeout OS.

Admission trước trial: còn đủ `export_reserve + min(2400, probe_cap200_estimate)`.
Admission trước probe: còn đủ120s (60s reserve+60s admission). Đây là quy tắc
bảo thủ được khóa trước test, không phải chứng nhận runtime. Nếu estimate
probe vượt2400s vẫn giữ probe passed về tài nguyên, trial bị guard2400s và
có thể timeout. Không tự nâng guard để cứu lượt đó.

`planned_config` giữ max_seconds2400. `execution_config` chỉ đổi max_seconds
theo min(2400,remaining−60), lưu atomically cùng active attempt. Các tham số
tác động đến chất lượng nghiệm không đổi. Guard này được runner kiểm tra ở
các boundary, kể cả callback; native call đang chạy có thể vượt deadline.
Analysis/export luôn được phép để lấy báo cáo khi hết ngân sách; chúng vẫn
được ghi thời gian nên tổng charged có thể vượt21600s.

Mỗi stage giữ OS lock và lưu checkpoint. `Ctrl+C` được runner ghi interrupted,
timer đóng bằng finally; có thể resume bằng đúng RESUME_DIR. Lượt completed
không chạy lại. Retry interrupted giữ cùng seed/config. Lỗi khác không retry
mặc định; toàn bộ attempts được giữ khi chủ động bật `RETRY_FAILED=True`.

Nếu kernel/process chết mà không chạy finally, chưa biết lúc dừng thật. Resume
ghi interrupted/recover orphan rồi tính bảo thủ wall gap từ checkpoint cuối
đến lúc resume, có thể gồm thời gian máy nghỉ. Khoản này được ghi riêng
`unconfirmed_wall_seconds`. Nếu clock wall lùi, tính hết ngân sách còn lại.
Không trừ/đặt lại khoản này để tự cấp thêm thời gian. Hệ quả: crash có thể làm
campaign hết ngân sách sớm; báo cáo partial là kết quả đúng. Đây là cách giữ
ngân sách trung thực khi chưa có native hard timeout hoặc watchdog độc lập.

Có thể đặt `MAX_NEW_TRIALS=18` để chạy một vòng seed trong mỗi phiên. Tham số
này chỉ ngắt phiên, không giảm90 planned runs hoặc đặt lại ngân sách. Source,
input, shots, seed và protocol thay đổi sẽ bị từ chối resume.

## Phân tích và đầu ra

Mỗi row CSV là một planned trial, kể cả pending, interrupted hoặc failed.
Summary có18 nhóm instance/p, mean/SD trên completed seed runs và coverage
riêng. Zero observed P_opt không bị thay bằng missing. SD theo seed chỉ là
biến thiên mô tả, không là CI theo instance. Không dùng P_opt gộp nhiều mạch
để tính batch success bằng công thức IID.

Controls cùng input gồm uniform encoded domain-wall+y (slack marginal), random
host assignment y inferred/no overload repair, và solver vét cạn81/243
placement. Có lift/difference với cả uniform encoded và random placement.
Lift encoded dương không chứng minh cạnh tranh classical. Classical timing
là warm-process, loại import/calibration/reference prep, còn QAOA trial timing
gồm optimization/final sampling/postprocessing; nêu phạm vi khi so sánh.

ZIP gồm campaign/clock ledger, frozen context, raw reports,90rowCSV, summary,
model validation, controls, classical timing, plot, checksum và byte nguồn21
modules. Không xuất secrets hoặc toàn bộ repository. `complete` chỉ khi90
trial completed; `partial` khi còn pending/interrupted; `finished_with_failures`
khi mọi planned row đã terminal nhưng có failure. Trạng thái complete vẫn
không chứng nhận chất lượng hoặc quantum advantage.

## Điều kiện kết thúc phần nghiên cứu ba host

Có kết quả test trong phạm vi thực sự đã chạy, audit/provenance, đối chứng và
kết luận về chất lượng/chi phí/giới hạn. Giữ các failure và dữ liệu thiếu.
Không tuning sau khi xem test rồi gọi cùng một study đã đăng ký trước.
Nếu đổi mixer/objective/encoding, tạo study/version riêng và giữ study này
làm baseline. Toàn đề cương còn cần phần FF/BFD/MILP do phân công nhóm; A20
không thay thế phần đó.
