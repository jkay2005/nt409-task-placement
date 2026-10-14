> **Đã được thay thế về dữ liệu và ma trận chạy:** xem `unified_benchmark_v1.md`. Phương án 5 task, classical-only 8/4 và 35 lượt bên dưới chỉ còn là lịch sử. Chính sách RAM vẫn được kế thừa; kế hoạch hiện hành là 45 lượt trên bộ benchmark chung.

# Phase 4 — Phạm vi điều chỉnh cho máy cá nhân 28 GB RAM

Cập nhật: 10/10/2026. Đây là kế hoạch điều chỉnh theo yêu cầu của Khiêm; chưa phải kết quả của các thí nghiệm còn thiếu. Tài liệu này thay các mục mở rộng quy mô không phù hợp trong kế hoạch cũ. Proposal PDF gốc giữ nguyên để nhóm/GV đối chiếu thay đổi.

## Quyết định phạm vi

- QAOA dùng Qiskit Aer CPU, statevector độ chính xác double, tối đa **23 qubit sau khi cộng đủ x, y và slack**.
- Hai instance chính: p1_choice (4 task/2 host, 20 qubit) và p0_reference (4 task/2 host, 23 qubit). Giữ khảo sát p=1,2,3.
- Bổ sung đúng một instance 5 task/2 host, 22 qubit, để có mở rộng số task trong giới hạn mô phỏng. Chưa chạy QAOA trên instance mới.
- p1_tight (18 qubit), p1_infeasible (20 qubit) và p3_demo (12 qubit) tiếp tục làm fixture kiểm tra; không mở thêm ma trận tinh chỉnh trên chúng.
- Mốc 8 task/4 host chuyển thành phạm vi **baseline cổ điển và đánh giá giới hạn mã hóa**, không phải mục tiêu chạy statevector QAOA trên laptop này.
- So sánh trực tiếp QAOA/FF/BFD/MILP chỉ trên các instance mà các phương pháp cùng được chạy. Kết quả baseline 8/4 nằm ở bảng riêng.
- Không tăng trần qubit để cố tận dụng hết RAM; không đổi precision hoặc backend trong đợt còn lại.

Đây là thay đổi phạm vi so với proposal ban đầu, cần công bố trong báo cáo và trao đổi với nhóm/GV nếu proposal đã được duyệt. Không ghi đã thực nghiệm QAOA 8/4.

## Cơ sở tài nguyên

Với mã hóa hiện tại trong src/qubo.py:

`N = n_task * n_host + n_host + sum(capacity.bit_length() cho từng host và từng tài nguyên CPU/RAM)`.

Một statevector complex128 cần `16 * 2**N` bytes. Đây chỉ là vector trạng thái; tổng RAM còn có interpreter, mạch, probability vector, energy vector, mask, mảng tạm và dữ liệu kết quả.

| Qubit | Bộ nhớ một statevector |
|---|---:|
| 20 | 16 MiB |
| 22 | 64 MiB |
| 23 | 128 MiB |
| 26 | 1 GiB |
| 28 | 4 GiB |
| 30 | 16 GiB |
| 36 | 1 TiB |

RAM cài đặt 28 GB không bằng RAM khả dụng. Lấy `psutil.virtual_memory().available / 2**30` tại lúc chạy để tính bằng GiB; không lấy số free hoặc mặc định toàn bộ RAM máy có thể dùng.

Notebook 15 trên máy của Khiêm đã ghi process lifetime peak RSS khoảng 655,83 MiB và RAM hệ thống khả dụng khoảng 14 GiB trong các lượt. Số này có thể gồm hoạt động kernel trước đó; không phải phép đo RAM riêng của từng nhánh và không bảo đảm p=3 sẽ dùng tương tự. Oracle exact hiện cũng giới hạn 23 qubit. Vì vậy 23 là giới hạn vận hành có cơ sở, không phải tuyên bố RAM 28 GB chỉ mô phỏng được tối đa 23 qubit.

Tăng p không tăng số qubit của cùng QUBO; số lớp/cổng và công việc tối ưu tăng. Vẫn phải đo thời gian và RAM ở p=3 trước campaign.

## Chính sách tài nguyên cho campaign mới

Các ngưỡng sau là lựa chọn thận trọng của dự án, chưa phải giới hạn đã được bổ sung vào runner cũ:

| Tham số/kiểm tra | Giá trị hoặc hành vi |
|---|---|
| max_qubits | 23 |
| method/device/precision | statevector / CPU / double |
| aer_threads | 4; chỉ dùng 2 nếu máy cần dành CPU cho công việc khác, khi đó chốt lại đồng nhất cả campaign |
| max_parallel_experiments / max_parallel_shots | 1 / 1 |
| aer_memory_mb | 2048; giới hạn lưu trạng thái của Aer, không phải giới hạn toàn bộ tiến trình |
| RAM available trước khi tạo oracle/campaign | Ít nhất 8 GiB |
| RAM available cần giữ trong quá trình chạy | Ít nhất 4 GiB |
| Ngân sách RSS của tiến trình Python | 4 GiB, ngưỡng giám sát để dừng thử nghiệm |
| Chạy đồng thời | Một kernel/campaign QAOA; không chạy MILP hoặc campaign QAOA khác song song |

8 GiB là điều kiện bắt đầu có dự phòng, không phải lượng RAM mà một lượt chắc chắn sẽ tiêu thụ. Ngưỡng available đã xét cả các ứng dụng khác đang chạy. Nếu không đạt, dừng trước campaign, đóng kernel nặng không dùng rồi đo lại.

Preflight cho mỗi instance/depth mới phải bao gồm chuẩn bị mô hình/mạch, ít nhất ba lần đánh giá tại các góc có lớp sâu hoạt động, phép đo cuối và hậu xử lý. Không dùng toàn góc zero ở lớp thêm để suy ra chi phí p=3. Theo dõi RSS và available trong probe. Chốt ngân sách đánh giá và thời gian chung trước campaign; chưa có số đo p=3 để hứa thời lượng.

Cần kiểm tra tài nguyên tại ranh giới các lần đánh giá; nếu RSS vượt ngân sách hoặc available dưới 4 GiB, dừng lượt đang chạy và giữ các report đã hoàn tất. Kiểm tra tại ranh giới không phải giới hạn RAM cưỡng bức của hệ điều hành: một lần gọi Aer vẫn có thể tạo đỉnh tạm thời. Probe, khoảng dự phòng và trần 23 qubit là các lớp kiểm soát bổ sung. Không gọi lượt bị dừng là completed, không loại nó khỏi thống kê trạng thái thực thi.

Các notebook/report cũ giữ nguyên config và hash. Không sửa manifest hoặc nâng min_available_gib trong thiết kế cũ để resume. Chính sách mới áp dụng cho campaign mới khi triển khai runner/notebook tiếp theo.

## Instance mở rộng được chọn

Tên dự kiến: p4_scale_5t2h. Lấy p1_choice, thêm task T5 với CPU=1, RAM=1; giữ nguyên hai host.

- Tasks: (1,1), (1,2), (2,1), (1,1), (1,1).
- Hosts: (5,5), (3,3).
- Số qubit: 10 biến x + 2 biến y + 10 slack = **22**.
- Đã kiểm tra cấu trúc bằng build_qubo và liệt kê 32 cách gán: có 16 cách gán khả thi, tối ưu là 2 host. Ví dụ bốn task đầu ở H0, task cuối ở H1.
- Đây mới là kiểm tra mô hình ứng viên trong phiên chuẩn bị; chưa tạo fixture chính thức, chưa có QAOA/FF/BFD/MILP benchmark trên nó.

Năm task có thể dùng ít qubit hơn p0_reference bốn task vì dung lượng host nhỏ hơn nên ít slack. Phải báo cáo cả task/host, capacity và qubit; không dùng hai instance này để tuyên bố đường tăng trưởng theo số task thuần túy.

## Công việc còn lại và tiêu chí nghiệm thu

### R1 — Preflight và lưu trạng thái dừng vì tài nguyên

Triển khai chính sách trên cho campaign mới, kiểm tra p=1/2/3 trước tối ưu và lưu số đo. Không làm thay đổi báo cáo lịch sử.

- Nghiệm thu: thiếu RAM bị chặn trước cấp phát lớn; trạng thái resource/time stop riêng với completed; resume bỏ qua report đã hoàn tất.
- Xác minh: kiểm tra biên bằng mô phỏng số đo RAM và lượt probe thật trên máy Khiêm; không cố làm cạn RAM để test.
- Phụ thuộc: không. Tệp dự kiến: module campaign mới, test tài nguyên/resume, notebook tiếp theo.

### R2 — Khép khảo sát độ sâu

Ma trận giới hạn: 2 instance chính × 3 độ sâu × 5 seed = **30 lượt** sampled-mean. Chốt 5 seed mới và ngân sách cùng các góc đầu theo tên tham số trước khi chạy; final seed tách training. Không lặp optimizer exact cùng góc chỉ bằng cách đổi seed để tạo pseudo-replicate.

- Nghiệm thu: đủ kết quả hoặc trạng thái không hoàn tất của 30 lượt; so p1/p2/p3 cùng protocol mới, có số shots, số lần đánh giá, thông báo dừng và chi phí thực tế.
- Xác minh: kiểm tra ma trận/report/counts và mẫu trạng thái khởi tạo; probe lớp mới hoạt động. Giữ notebook 11 làm lịch sử có giới hạn protocol.
- Phụ thuộc: R1. Tệp dự kiến: module campaign độ sâu mới, test, notebook và hướng dẫn tương ứng.

### R3 — Mở rộng số task có giới hạn

Đưa p4_scale_5t2h vào fixture chính thức và đo ở p=1, cùng protocol và 5 seed của R2: **5 lượt mới**. Dùng p1_choice/p1 trong R2 làm mốc cùng protocol; không nhân toàn bộ nghiên cứu CVaR/penalty/depth lên instance mới.

- Nghiệm thu: fixture/mô hình đúng 22 qubit và nghiệm tham chiếu 2 host; 5 trạng thái chạy được ghi nhận; dữ liệu source không thay thế p1_choice cũ.
- Xác minh: đếm qubit, kiểm tra khả thi/optimum, preflight và audit report.
- Phụ thuộc: R1 và protocol R2. Tệp dự kiến: một JSON instance, test fixture, cấu hình chạy mở rộng.

Tổng mặc định còn lại: **35 lượt QAOA mới**, không gồm probe. Nếu tài nguyên không đạt, giữ trạng thái bị chặn và báo cáo giới hạn; không tự giảm số seed hoặc bỏ p=3 rồi đánh dấu đủ ma trận. Không mở thêm sweep sau khi thấy kết quả.

### R4 — Baseline và đối chiếu

B chạy FF/BFD/MILP trên cùng các fixture nhỏ; có thể thêm 8/4 ở nhánh cổ điển với giới hạn thời gian/bộ nhớ riêng và cùng chính sách tránh chạy đồng thời. Không giả định MILP luôn đạt tối ưu: ghi trạng thái solver, incumbent/bound nếu có.

- Nghiệm thu: kiểm tra nghiệm và bảng so sánh cùng input; tách mẫu phổ biến nhất khỏi best-valid; dữ liệu 8/4 chỉ có classical không được trình bày như benchmark đối đầu QAOA.
- Xác minh: input hashes, validator chung, đối chiếu objective và chi phí. Trạng thái B hiện chưa xác nhận.
- Phụ thuộc: dữ liệu B và R2/R3 cho bảng cuối. Tệp dự kiến: kết quả B, bảng tổng hợp, tài liệu phân tích.

### R5 — Tổng kết và bàn giao

C cùng A tổng hợp các nghiên cứu đã có và R2/R3, công bố phạm vi mới, giới hạn lịch sử đo cuối và nguồn dữ liệu. Không yêu cầu QAOA phải thắng baseline để nghiệm thu.

- Nghiệm thu: bảng số liệu truy ngược được; checklist hoàn tất/không hoàn tất rõ; code/môi trường/hướng dẫn/report đủ để kiểm tra và tái lập.
- Xác minh: đối chiếu artifact và test suite trước bàn giao; không tự xác nhận B/C đã nhận hoặc hoàn tất.
- Phụ thuộc: R4. Tệp dự kiến: docs tổng kết, README, manifest và gói bàn giao.

Checkpoint sau R1: tài nguyên p=3 đã được đo và budget được cố định trước dữ liệu. Checkpoint cuối R5: đóng Phase 4 theo phạm vi đã điều chỉnh; không gắn việc đóng phase với một ngưỡng P_opt tự đặt sau thí nghiệm.

## Nguồn

- src/qubo.py: cách đếm x/y/slack; src/qaoa_experiment.py: cấu hình Aer và giới hạn hiện có.
- Notebook 15 Windows: campaign mean 20261010T022352464276Z và CVaR 20261010T022352499157Z; số đo tài nguyên đã audit từ report người dùng.
- [Qiskit AerSimulator — max_memory_mb, precision, parallel options](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html), đối chiếu 10/10/2026.
- Proposal Topic 16, mục 3/5/6: phạm vi gốc, độ sâu, baseline và kết quả kỳ vọng; điều chỉnh này không sửa ngược tài liệu gốc.
