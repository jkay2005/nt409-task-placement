# NT409 — Bộ benchmark chung v1

Chốt ngày 10/10/2026 theo yêu cầu thống nhất dữ liệu và cách so sánh từ đầu. Tài liệu này thay kế hoạch 35 lượt và phần mở rộng 5 task/8 task của bản điều chỉnh RAM trước đó. Mã mô hình và dữ liệu nguồn đã kiểm chứng được giữ lại.

## 1. Một bộ benchmark dùng chung cho cả nhóm

Một bộ benchmark gồm nhiều instance cố định. A, B và C đều dùng đúng bộ này; không chọn instance riêng cho từng thuật toán. Phạm vi chính thức là **4 task/2 host**, tối đa 23 qubit cho QAOA.

| Instance | Vai trò | Qubit | Số cách gán khả thi | Số host tối ưu |
|---|---|---:|---:|---:|
| p1_choice | Benchmark: có lựa chọn 1 hoặc 2 host | 20 | 11 | 1 |
| p1_tight | Benchmark: tài nguyên chặt | 18 | 4 | 2 |
| p0_reference | Benchmark: ví dụ gốc của proposal | 23 | 1 | 2 |
| p1_infeasible | Kiểm tra chức năng vô nghiệm, không xếp hạng chất lượng | 20 | 0 | Không tồn tại |

Các con số cách gán trên được tính bằng liệt kê 2^4 cách đặt task, mỗi host có task thì bật; không phải số bitstring x/y/slack. Reference nhỏ này kiểm tra dữ liệu, không thay baseline MILP của B.

Nguồn dữ liệu duy nhất: bốn JSON trong `data/instances/`, được liệt kê trong `data/benchmarks/nt409_benchmark_v1/manifest.json`. Không sửa task/host/capacity/thứ tự để làm một phương pháp chạy dễ hơn. BFD được phép sắp task trong thuật toán theo quy tắc đã chốt nhưng phải ánh xạ kết quả về đúng ID/thứ tự nguồn.

Mỗi instance có SHA256 của JSON canonical: sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False, encode UTF-8. Do đó xuống dòng LF/CRLF và cách thụt lề không làm thay đổi định danh; thay giá trị hay thứ tự task/host thì có. Manifest cũng giữ hash của protocol. Chỉnh dữ liệu hoặc protocol có ý nghĩa phải tạo phiên bản mới; không sửa v1 sau khi bắt đầu campaign chính thức.

Không thêm bộ 5 task hoặc 8/4 vào đợt cuối. Đây là giảm phạm vi kích thước so với proposal, cần công bố với nhóm/GV; không tuyên bố đã đánh giá scaling đến 8/4. Số qubit/capacity khác nhau trong bộ này cũng không phải một nghiên cứu đường tăng trưởng theo số task.

## 2. Cùng bài toán, cùng quy tắc chấm

- Mục tiêu gốc: tối thiểu tổng host được bật. Mỗi task trên đúng một host, CPU và RAM không vượt capacity của host đang bật.
- Mọi đầu ra đều qua validator chung `src/placement.py`. Khi nhận x/y tường minh, giữ y mà thuật toán trả về; không sửa mẫu QAOA trước chấm.
- Nghiệm không hợp lệ không có objective/gap. Heuristic không tìm được nghiệm và QAOA không đo được mẫu hợp lệ không chứng minh instance vô nghiệm.
- Chỉ so cùng instance và cùng quy tắc output. Không so E_QUBO với số host của MILP như cùng một objective.
- Chất lượng chính của một lượt: có trả về placement hợp lệ không; số host của placement trả về; gap so với optimum đã được chứng nhận. Giữ lượt thất bại trong mẫu thống kê.
- Với QAOA, đầu ra giải bài toán là **best-valid trong batch cuối 1024 shots**, không sửa bit, không giải cổ điển thay phần thiếu. Đây là hậu xử lý phải tính chi phí. Khi nhiều mẫu cùng objective tối thiểu: ưu tiên frequency cao hơn, sau đó chuỗi bit little-endian trong thứ tự biến công bố, so từ điển tăng dần để tái lập.
- Báo cáo riêng mode của bitstring đầy đủ, frequency và tập đồng hạng. Không gọi một mode được chọn tùy ý là mode duy nhất; quy tắc best-valid là khác với cách lấy chuỗi xuất hiện nhiều nhất trong proposal.
- QAOA báo thêm P_feasible/P_opt/P_ground đo từ batch cuối, số mẫu thực tế và tỷ lệ lượt thành công. Baseline trả về một placement, không gán cho nó một xác suất mỗi shot giả để đặt ngang P_opt QAOA.

## 3. Protocol QAOA duy nhất cho bảng so sánh cuối

Định nghĩa máy đọc được trong `protocol.json` cùng thư mục manifest:

- Sampled mean-energy, penalty assignment=capacity=3, cùng mô hình x/y/slack và X mixer; Hamiltonian max_abs.
- Aer CPU statevector/double; COBYLA rhobeg=1, tol=1e-4; cap 200 lần đánh giá hàm; training shots=1024, final shots=1024.
- p=1,2,3 trên cả ba instance benchmark; seed tối ưu 70,71,72,73,74; seed đo cuối 100070..100074. Seed được ghép giữa các p trên cùng instance, không gọi các nhánh ghép là quan sát độc lập.
- Điểm đầu theo thứ tự beta trước gamma: p1=[0.3,1.0], p2=[0.3,0,1.0,0], p3=[0.3,0,0,1.0,0,0]. Lớp thêm ban đầu là identity, sau đó được tự do tối ưu; cần kiểm chứng tên/thứ tự tham số và trạng thái đầu tương đương trước chạy.
- Không warm-start từ góc tối ưu đã học. Không đổi objective sang exact/CVaR giữa các instance.
- Ngân sách thời gian mỗi lượt là 600 giây tại các ranh giới đánh giá; không phải ngắt cưỡng bức đúng 600 giây và không bao gồm mọi chi phí ngoài optimizer. Probe p3 có lớp mới hoạt động phải xác minh tính khả thi trước khi chạy campaign.
- Giữ cùng cap đánh giá/shots giữa độ sâu; ghi thời gian, số đánh giá thực tế và chi phí cổng vì các p không có cùng chi phí tuyệt đối.
- Tổng: **3 instance × 3 p × 5 seed = 45 lượt QAOA chính thức**. Lượt dừng sớm vì time/resource/error phải có trạng thái riêng; không loại khỏi sổ thực thi và không ghi completed.
- Không tự tăng cap khi kết quả kém. Nếu probe tài nguyên không đạt, chặn trước campaign và ghi lý do; muốn đổi protocol phải chốt phiên bản mới trước dữ liệu chính thức, không trộn các phiên bản.

Exact diagnostics nếu có chỉ là chẩn đoán sau tối ưu, tách thời gian và nhãn; không dùng exact oracle làm lợi thế thông tin cho thuật toán trong bảng sampled benchmark. Không cần chạy lại CVaR, sweep penalty hoặc mọi notebook cũ.

## 4. Quy tắc baseline để các thành viên thực hiện giống nhau

Các quy tắc sau là lựa chọn thuật toán của benchmark v1; B cần đối chiếu với mã hiện có, không giả định mọi định nghĩa BFD đa tài nguyên đều giống nhau.

**First-Fit:** duyệt task theo thứ tự JSON; chọn host đầu tiên theo thứ tự JSON còn đủ CPU/RAM, bật host nếu cần. Nếu có task không đặt được, trả failure; không bỏ task.

**BFD hai tài nguyên:** đặt `Cmax=max(host.cpu)` và `Rmax=max(host.ram)`; độ lớn task là max(cpu/Cmax,ram/Rmax), sắp giảm dần, hòa thì dùng thứ tự task nguồn. Với mỗi task, ưu tiên các host đang bật còn đủ tài nguyên; nếu không có thì xét host chưa bật. Trong tập ứng viên, chọn host làm nhỏ nhất tổng tỷ lệ CPU và RAM còn dư sau khi đặt, mỗi tỷ lệ chia capacity tương ứng của chính host; hòa thì chọn host theo thứ tự JSON. Đổi công thức này là đổi cấu hình BFD và phải ghi nhận.

**MILP:** cùng x/y, mục tiêu sum(y), cùng ràng buộc gốc. Chốt solver/version/options trước chạy; ngân sách tối đa 600 giây, một process, một thread cho khả năng tái lập. Ghi trạng thái, incumbent, bound/gap khi có; chỉ dùng kết quả chứng nhận optimal làm ground truth của bảng đối chiếu. Trên instance vô nghiệm, cần trạng thái infeasible được chứng nhận, không suy từ timeout.

Ba baseline chạy trên cả ba instance benchmark. FF/BFD xác định không cần nhân năm seed để tạo mẫu chất lượng giả. Có thể đo thời gian lặp có giới hạn nếu cần, nhưng ghi riêng số lần đo timing và không coi đó là năm nghiệm độc lập.

## 5. Kiểm tra vô nghiệm chung

p1_infeasible là fixture kiểm tra chức năng cho mọi phương pháp, nằm ngoài bảng xếp hạng và ngoài 45 lượt chính thức. Không có optimality gap/P_opt đối với một optimum không tồn tại.

- Validator và reference liệt kê xác nhận không có placement hợp lệ.
- FF/BFD phải báo không tìm được placement; MILP cần phân biệt proven infeasible với no incumbent/time limit.
- QAOA chỉ có thể báo không quan sát mẫu hợp lệ; không được suy ra chứng minh vô nghiệm. Kiểm tra trên fixture này một lượt smoke p1/seed70, shots64, finalshots64, cap8 để kiểm tra mã hóa/trạng thái, không dùng vào bảng hiệu năng.

## 6. RAM và thời gian trên máy 28 GB

Giữ trần 23 qubit; available RAM ít nhất 8 GiB trước campaign, giữ available ít nhất 4 GiB trong quá trình chạy, ngưỡng giám sát RSS Python 4 GiB. Aer state memory setting 2048 MiB, bốn luồng, max_parallel_experiments=max_parallel_shots=1. Một campaign/kernel và một instance tại một thời điểm; giải phóng oracle cũ trước chuyển instance. Không chạy MILP nặng song song trên cùng máy.

Đây là chính sách cần triển khai trong bộ chạy mới, chưa tự có hiệu lực vì sửa JSON. Kiểm tra tại ranh giới evaluation không phải hard cap OS. Đo probe p3 với lớp mới thực sự hoạt động, batch cuối và hậu xử lý, đồng thời ghi available/RSS và thời gian. Không dùng toàn bộ 28 GB làm ngân sách mặc định.

## 7. Giữ lại và làm lại

**Giữ:** bốn JSON gốc, đặc tả, validator, QUBO/Ising, kiểm chứng đại số, các hàm giải và report đã audit. Không xóa notebook/report lịch sử.

**Làm lại phần nghiệm thu:** orchestration đọc manifest/protocol chung, kiểm tra hash/version, campaign 45 lượt, baseline khớp protocol và bảng cuối. Runner hiện tại cần bổ sung resource stop/provenance phù hợp; chưa có notebook thực thi benchmark v1 trong gói này.

Notebook 06–15 là dữ liệu thăm dò/chẩn đoán giúp chọn protocol, không trộn vào 45 lượt xác nhận. Các instance đã được sử dụng trong thăm dò, nên đây là xác nhận trên bộ fixture đã biết, không phải test set độc lập hay bằng chứng khái quát sang bài toán chưa thấy.

Nếu baseline B đã chạy đúng cùng hash và đúng quy tắc trên, có thể tái sử dụng sau kiểm tra nguồn và môi trường. Chưa có xác nhận hiện trạng B/C, không tự đánh dấu đã bàn giao hoặc đã hoàn tất.

## 8. Thứ tự nghiệm thu và điểm dừng

1. Chốt manifest/protocol/hashes; A/B/C dùng cùng gói, ghi nhận điều chỉnh proposal. Gói hiện tại đã chốt dữ liệu và thiết kế, chưa xác nhận bên ngoài.
2. Triển khai một bộ chạy chung, probe tài nguyên, kiểm chứng start-state p1/p2/p3, sampling cuối và resume/status.
3. Chạy 45 lượt QAOA, baseline trên ba instance và kiểm tra vô nghiệm riêng; audit dữ liệu nguồn.
4. C/A/B tổng hợp bảng cuối theo instance, báo thất bại và chi phí đầy đủ; đóng Phase 4. Không đặt tiêu chí QAOA phải thắng baseline và không phát sinh sweep mới chỉ vì P_opt thấp.

## English summary

One frozen benchmark suite is shared by all methods: choice, tight and reference for measured comparisons, plus infeasible for functional validation only. The scope is four tasks/two hosts, capped at 23 encoded qubits. The prior five-task and classical-only 8/4 extensions are removed from this acceptance campaign. The final QAOA protocol is sampled mean, penalties (3,3), p=1/2/3, five paired seeds, 200 evaluations and 1024 independent final shots: 45 runs. FF/BFD/MILP must consume identical input hashes and use the stated output/validation rules. Prior notebooks remain exploratory evidence. This package freezes inputs and protocol; it does not yet implement or execute the new runner.
