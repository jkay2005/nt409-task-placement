# Đối chứng mã hóa hai host — nhánh A, Notebook 17

Giữ nguyên dữ liệu benchmark v1.1 và kết quả Notebook 16. Mã hóa mới dùng
`x_i,0 = 1-z_i`, `x_i,1 = z_i`, giữ y và slack; chỉ áp dụng đúng hai host.
Mục tiêu và capacity CPU/RAM không đổi. Đây là phép thử ảnh hưởng mã hóa,
không phải đề xuất thuật toán mới hay bằng chứng quantum advantage.

Nghiệm thu mô hình: ánh xạ một-một tới không gian one-hot cũ; năng lượng
QUBO mới bằng năng lượng cũ trên mọi vector đã ánh xạ; kiểm tra cả y sai,
slack sai và instance vô nghiệm. Ground state được tính độc lập trên z/y.
Đối chứng uniform phải tính lại cho từng mã hóa, gồm bội số biểu diễn slack.

Ma trận kế thừa: choice/tight/reference × p1/2/3 × seed70–74, 45 lượt mới;
negative smoke tách riêng. Mean, X mixer trên biến mới, P_capacity=3,
max_abs, 1024 training/final shots, final seed+100000, COBYLA cap200,
rhobeg1/tol1e-4, time guard2400 và chính sách RAM giữ từ v1.1.
Góc đầu giống về tọa độ nhưng trạng thái đầu và Hamiltonian khác giữa mã
hóa. Mỗi Hamiltonian chuẩn hóa max_abs riêng: phép thử đánh giá cả cách
biểu diễn với quy tắc chuẩn hóa chung, không cô lập riêng hiệu ứng số qubit.

Kết quả đầu ra: best-valid ở batch cuối độc lập, không sửa bits. Báo
P_feasible/P_opt/P_ground, lift so với uniform riêng, nfev, tổng shots,
thời gian và RAM. So sánh chất lượng dùng cùng instance/p/seed; không xem
các shots thuộc nhiều seed là các lần huấn luyện độc lập. Chỉ so sánh thời
gian trực tiếp khi môi trường phù hợp và không suy ra lợi thế lượng tử.

Điểm dừng: đủ ma trận và audit, hoặc công bố PARTIAL/failure. Không thay
ngân sách/seed để chọn kết quả đẹp. Giữ mọi lần thất bại và resume theo
trạng thái; không chạy lại completed. Không triển khai công việc B/C.

Triển khai theo bốn bước: kiểm thử/mô hình; runner đo thật; lưu-resume và
nhập baseline có audit; Notebook 17, kiểm thử toàn bộ và gói bàn giao.
Các module lịch sử giữ nguyên để không làm thay đổi nguồn Notebook 16.

Cơ sở: [Bucher et al., 2025, mục IV và chú thích one-hot hai lựa chọn](https://arxiv.org/abs/2506.03115v2).
Giảm bốn qubit chỉ bảo đảm kích thước một statevector giảm 16 lần; chất
lượng nghiệm phải đo. Uniform mã hóa mới cũng tăng P_opt 16 lần do giới
hạn one-hot, nên mức tăng tuyệt đối đó không tự chứng minh QAOA hiệu quả.
