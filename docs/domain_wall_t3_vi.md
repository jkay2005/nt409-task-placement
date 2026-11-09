# T3 — Trạng thái đầu và mixer bảo toàn domain-wall

## Phạm vi

Cùng frozen input a3_dev_n5 của Notebook22–24: 5 task × 3 host, 25 qubit, min tổng y, domain/capacity penalty4, Ising offset248.5 và max-abs scale65.5. Không đổi QUBO, slack, cách giải mã hoặc cách chấm P_opt/P_valid. Không dùng đáp án hay góc đã học để thiết kế điểm probe.

## Trạng thái đầu

Với mỗi task, ba mã (u,v) hợp lệ là (0,0), (1,0), (1,1). Tạo chồng chập đều của chúng bằng:

1. RY(2 arccos(1/√3)) trên u.
2. CRY(π/2) từ u sang v.

Khi bắt đầu ở0, biên độ u=0 bằng1/√3, u=1 bằng√(2/3). Cổng CRY chia biên độ u=1 đều cho hai giá trị v, cho ba mã biên độ1/√3 và mã(0,1) biên độ0. Tích năm khối như vậy tạo phân phối đều trên3^5=243 mã assignment hợp lệ. Ba qubit y và12 qubit slack vẫn bắt đầu ở |+> như control.

Trong thứ tự cơ sở Qiskit |v u>, ba mã hợp lệ có chỉ số0,1,3; mã sai có chỉ số2. Không tráo ký hiệu (u,v) với cách in chuỗi bit.

Đây chỉ là trạng thái đầu hợp lệ miền biểu diễn. Rất nhiều thành phần vẫn vi phạm CPU/RAM hoặc có slack chưa khớp.

## Mixer có thứ tự

Đặt:

\[
A_i=X_{u_i}(I+Z_{v_i})/2,\qquad
B_i=X_{v_i}(I-Z_{u_i})/2.
\]

A_i chỉ đổi u khi v=0, nối (0,0) với (1,0). B_i chỉ đổi v khi u=1, nối (1,0) với (1,1). Cả hai để mã(0,1) tách khỏi miền hợp lệ.

Một lớp mixer của implementation là:

\[
U_M(\beta)=\left(\prod_{j=10}^{24}e^{-i\beta X_j}\right)
\prod_{i=0}^{4}\left(e^{-i\beta B_i}e^{-i\beta A_i}\right).
\]

Trong circuit, A chạy trước B. A được thực hiện bằng X(v), CRX(2β;v→u), X(v); B dùng CRX(2β;u→v). 15 qubit y/slack vẫn dùng RX(2β).

A và B cùng một task không giao hoán. Vì vậy đây là **tích các unitary theo thứ tự**, không phải triển khai chính xác exp[-iβ(A+B)] và không được đổi thứ tự mà vẫn gọi là cùng cấu hình.

Mỗi khối giữ miền hợp lệ; cost Hamiltonian chéo chỉ đổi pha nên cũng giữ miền. Từ trạng thái đầu không có mã sai, mọi lớp cost–mixer lý tưởng tiếp theo vẫn nằm trong miền domain-wall hợp lệ. Các cạnh (0,0)↔(1,0)↔(1,1) nối cả ba mã; đồ thị assignment là tích năm đồ thị đường đi. Đây là tính liên thông của đồ thị mixer, không phải chứng minh khả năng tạo mọi trạng thái lượng tử hoặc tìm optimum với p hữu hạn. Một số β đặc biệt có thể không trộn hoặc triệt tiêu chuyển tiếp.

Trạng thái đều trên miền không được mặc định là eigenstate của mixer này. Chuẩn bị nó không yêu cầu dùng đáp án placement.

## Ba cấu hình đối chứng

| ID | Trạng thái đầu | Mixer |
|---|---|---|
| standard_x | H trên25 qubit | X toàn bộ |
| valid_x | Domain đều trên10 assignment bit; H trên15 bit còn lại | X toàn bộ |
| valid_dw | Cùng trạng thái đầu valid_x | Mixer AB trên assignment; X trên y/slack |

Đối chiếu standard_x→valid_x đo ảnh hưởng thay trạng thái đầu. Đối chiếu valid_x→valid_dw đo thay mixer với cùng trạng thái đầu. T3 chỉ xác nhận mạch và chi phí; T4 mới huấn luyện để so chất lượng.

Các beta của mixer khác nhau có ý nghĩa động lực khác nhau; cùng giá trị số beta không phải matched mixer strength hoặc cùng unitary. Một sweep AB là định nghĩa cố định, không tự thay số sweep/Trotter steps để cải thiện kết quả. Số gate và thời gian cần được báo bên cạnh cap evaluation.

## Protocol T3

- p=1 ở điểm beta=.3,gamma_execution=1.
- p=2 ở beta=[.3,.2],gamma_execution=[1,.5].
- Ba cấu hình, tổng sáu lần đánh giá; thêm ba kiểm tra góc0 ở p=1 để xác nhận phân phối đầu.
- Điểm khai báo trước, chưa tối ưu và không nhập từ Notebook23/24.
- So matrix khối cổng với exp(-iβB)exp(-iβA) ở5 beta, kiểm tra unitary/leakage/liên thông.
- Mạch bài toán và tất cả resource probes giữ25 qubit. Khối4×4 là bằng chứng cổng cục bộ, không phải input placement nhỏ hơn.
- Nguồn/input/QUBO hash và runtime được ghi trong probe.json; nguồn y/slack/decoder giữ như trước.

P_domain của standard initial là(3/4)^5≈23.73046875%; valid initial là100%. Ở valid initial, P_valid và P_opt cũng thay đổi do phân phối đầu thay đổi; không diễn giải đó là thành quả huấn luyện.

## Giới hạn và chi phí

- Bảo toàn domain không tự bảo toàn CPU/RAM hoặc slack.
- Backend Aer vẫn mô phỏng statevector25 qubit; miền nhỏ hơn không tự giảm số qubit hoặc RAM cần cấp.
- Gate counts là số cổng sau compile cho Aer, không phải số CNOT của một thiết bị thật.
- Một timed call/cấu hình chưa đủ cho kết luận hiệu năng; setup và thống kê có thời gian riêng.
- Không dùng sáu P_opt tại góc chưa học để chọn winner hoặc tuyên bố tốt hơn mean+INTERP đã huấn luyện.
- Kết quả lý tưởng chưa bao gồm nhiễu phần cứng.

## Nguồn

- Hadfield và cộng sự, From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz, Algorithms12(2),34(2019): https://arxiv.org/abs/1709.03489 . Cơ sở cho mixer theo unitary giữ không gian con; công thức AB cụ thể ở đây được suy ra và kiểm chứng cho encoding của đồ án, không gán là công thức chép nguyên từ bài báo.
- IBM Qiskit QAOAAnsatz API: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.QAOAAnsatz . Hỗ trợ initial_state và mixer_operator dạng circuit. Runtime thực dùng Qiskit2.5.2, Aer0.17.2 và Qiskit Optimization0.7.0; không nâng dependency trong T3.
