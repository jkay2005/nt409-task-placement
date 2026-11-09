# Notebook27 — bắt đầu T4b theo kế hoạch một tháng

Ngày25/10/2026. Chỉ huấn luyện development a3_dev_n5 trên5 task ×3 host/25qubit. Ba case kiểm chứng N26 chưa chạy ở bước này. Đây là gói code/notebook để thực hiện T4b; T4b chỉ được nghiệm thu sau khi người dùng gửi kết quả huấn luyện Windows.

## 1. Cài gói vào repo đang chạy được N26

Giải nén nt409_notebook27_domainwall_training_v1.zip vào thư mục repo hiện tại, giữ cấu trúc src/,notebooks/,tests/. Gói chỉ thêm source mới/test/notebook/docs; không thay dataset,guard hay source N22–26. Không cần cài thêm package. Chọn kernel nt409-khiem như N25/N26; restart kernel nếu vừa cập nhật/import module của gói trước đó.

## 2. Kiểm tra trước khi chạy

Mở notebooks/27_domain_wall_training_development.ipynb. Chạy hai ô code đầu. Output cần có:

- Input a3_dev_n5,25qubit,software_validation=False.
- Sáu stage:standard_x_p1/p2,valid_x_p1/p2,valid_dw_p1/p2.
- Cap100/stage,tổng600 objective evaluations.
- Available RAM ít nhất4GiB. Máy có28GB RAM không có nghĩa còn trống28GB; đóng campaign/kernel QAOA khác trước khi chạy.

Mỗi campaign được giữ bằng data/reference_results/phase5_domainwall_training/N27_ACTIVE.json. Đừng sửa/xóa con trỏ để tạo thêm lần chạy chính. Hướng dẫn này không yêu cầu chạy chế độ software_validation; chế độ đó chỉ dùng QA phần mềm, cap6/stage vẫn cùng5×3/25qubit và không được báo thành kết quả chính.

## 3. Chạy ba nhánh theo thứ tự

Có thể Run All hoặc chạy lần lượt từng ô. Mỗi ô nhánh chạy p1 rồi p2. Chỉ một runner tại một thời điểm. Mỗi10 evaluation in mean-energy; trước eval1 có xây diagonal/compile, có thể mất hàng chục giây hoặc hơn tùy máy.

| Nhánh | Trạng thái đầu | Mixer | Cap p1+p2 |
|---|---|---|---:|
| standard_x | Plus trên25bit | X |100+100|
| valid_x | Uniform legal assignment;auxiliary H | X |100+100|
| valid_dw | Giống valid_x | AB có thứ tự |100+100|

Mỗi p1 bắt đầu[beta,gamma]=[0.3,1.0] trên H/max_abs. Mỗi p2 dùng INTERP từ điểm mean-energy tốt nhất của chính p1 đó. COBYLA rhobeg1,tol1e-4. Không bounds góc, không chọn bằng P_opt, không sửa penalty4. Không lấy kết quả N23/N24 làm p1 miễn phí cho control.

N25 ngoại suy riêng600 simulation calls≈52phút trên Windows,chưa gồm setup,mean-energy scoring,I/O và overhead. N27 còn6final-exact calls và3final-sampling calls nếu mọi stage hoàn tất; tối đa609 lời gọi mô phỏng được cấp, chưa kể chi phí xây mạch/diagonal. Dự trù khoảng một giờ hoặc lâu hơn; không xem đây là benchmark hay cam kết runtime. Giới hạn2400giây/stage tính từ trước setup và kiểm giữa native calls, không ngắt cưỡng bức một lời gọi native đang chạy. RAM guard4GiB cũng kiểm giữa các lời gọi; không phải cam kết peakRAM.

## 4. Đọc bảng đúng cách

Mean-energy là objective huấn luyện. P_domain/P_valid/P_opt ở bảng notebook là phần trăm; P_ground là xác suất dạng khoa học. Trong JSON tất cả P là xác suất0..1. P_valid/P_opt giữ measured y; không repair placement/slack. Exact metrics là chính, final1024shot seed20261025 chỉ minh họa. Cùng seed giữa nhánh giúp tái lập, không tạo thêm mẫu độc lập.

completed nghĩa stage chạy và scoring hoàn tất, không khẳng định optimizer hội tụ. Xem optimizer_stop.success/message/nfev. Hết cap100 thường có success=False; vẫn là một kết quả hợp lệ theo ngân sách đã khóa. p2 là kết quả chính, tổng ngân sách nhánh tính cả p1.

Sum stage elapsed seconds tính setup/training/checkpoint/final scoring bên trong stage; chưa gồm toàn bộ create/identity check/export/GC và thời gian nghỉ giữa các ô. Không gọi số này là wall-clock campaign hoặc dùng một lượt này chứng minh ưu thế tốc độ. Compiled gate counts là số đo Aer,không phải tài nguyên hardware quantum đã ánh xạ.

## 5. Tiếp tục hoặc xử lý lỗi

Mỗi evaluation được ghi in_flight trước mô phỏng rồi completed sau khi có energy; có raw JSON và ledger hash. Điểm scoring chỉ lấy theo mean-energy thấp nhất đã quan sát. Hoàn tất stage mới cho phép p2 dùng điểm p1.

- Chạy lại notebook/ô nhánh: bỏ qua stage đã completed và tiếp tục stage chưa bắt đầu, không tính lại p1.
- Dừng giữa hai stage: có thể tiếp tục từ stage kế tiếp trong cùng môi trường/source/input.
- Stage failed/interrupted/running: giữ nguyên ngân sách đã cấp và dừng để kiểm tra. Không tự khởi động lại stage vì SciPy COBYLA không lưu toàn bộ trạng thái nội bộ; checkpoint mỗi evaluation không có nghĩa resume giữa optimizer được.
- Kernel/PC chết cứng có thể để RUNNING.lock hoặc raw/ledger chưa đồng bộ. Giữ nguyên thư mục và gửi lỗi; nếu export bị guard chặn, nén thư mục campaign bằng Explorer. Không xóa lock/raw/ledger hay giảm guard để ép chạy.
- Không cập nhật package,thêm/sửa module src hoặc chuyển máy trong campaign. Identity ghi runtime và hash tất cả src/*.py; đổi source/runtime chặn resume. Export trước khi nhận gói code tiếp theo.

## 6. Gửi lại bằng chứng

Save notebook đã chạy. Chạy ô export cuối, gửi notebooks/27_domain_wall_training_development.ipynb cùng t4b_<timestamp>.zip có đường dẫn được in. ZIP gồm input/dataset,source snapshot,campaign ledger,raw stage reports,summary và SHA256. Campaign chưa hoàn tất cũng có thể export nếu không có writer đang chạy và dữ liệu còn nhất quán.

Sau N27: đánh giá ba nhánh trên development trước; sau đó T4c dùng nguyên cấu hình cho ba validation case. Giữ các mốc06/11 chốt hướng,13/11 đóng băng kết quả,20/11 bàn giao kỹ thuật. Chưa thực hiện MILP trong N27.
