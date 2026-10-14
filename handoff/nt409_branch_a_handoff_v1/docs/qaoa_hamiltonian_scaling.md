> **English version below.**

# Notebook 10 — Penalty chung, thang Hamiltonian và khởi tạo

Cập nhật ngày 06/10/2026. Nhánh A đã hoàn tất review notebook 09: 20 lượt Windows, 20.480 shots, công thức/giải mã/bảng đều khớp. Choice: (3,12) có 10 mẫu tối ưu so với 6 của (3,3), cả hai thành công 4/5 lượt; reference: (1,1) có 12 mẫu và thành công 5/5, (3,12) có 6 mẫu và thành công 2/5. Các chênh lệch chưa ủng hộ dùng (3,12) cho cả hai input.

Bước tiếp theo giữ **(A,B)=(3,3) cho cả choice/reference, p=1** và kiểm tra thang Hamiltonian/cách tìm gamma. Không thêm dữ liệu đầu vào hoặc ma trận penalty. Đây là đợt chẩn đoán trước khảo sát p=2; không hứa rằng chuẩn hóa sẽ cải thiện chất lượng.

## 1. Lý thuyết gắn với code

Mô hình QUBO gốc vẫn là số host + A × sai số gán task + B × sai số phương trình tài nguyên. Giữ toàn bộ hệ số QUBO, thứ tự x/y/slack và cách kiểm tra placement. Với hai host, dữ liệu nguyên và bài toán có nghiệm, A=B=3 đủ để mọi cực tiểu QUBO hợp lệ.

QAOA dùng U_C(gamma)=exp(-i gamma H). Các hệ số H phụ thuộc CPU/RAM/host/slack, vì vậy cùng penalty không tạo cùng thang H cho hai input. Ta đặt:

```text
kappa = max trị tuyệt đối của các hệ số Pauli khác identity
H_execution = H_raw / kappa
E_QUBO(bits) = kappa * expectation(H_execution, bits) + offset_raw
gamma_execution = kappa * gamma_raw
```

Nếu H chỉ chứa hằng số/zero thì kappa=1. Positive global scaling giữ thứ tự năng lượng và cực tiểu; quy đổi gamma giữ cùng trạng thái mạch, beta không đổi. Không chia riêng các phương trình CPU/RAM: thao tác đó thay đổi trọng số tương đối và cần kiểm chứng mô hình khác.

Qiskit sắp góc theo beta[0..p-1], gamma[0..p-1]. Helper `scaled_qaoa_point` xử lý đúng nửa gamma. Choice có kappa=74.5, reference có kappa=257.5 với (3,3). Chuẩn hóa không đổi số qubit: 20/23.

COBYLA giữ rhobeg=1 trong tọa độ đang thực thi. Sau chuẩn hóa, bước gamma tương ứng theo H gốc nhỏ hơn. Do đó, cùng trạng thái khởi đầu không có nghĩa cùng quỹ đạo tối ưu. Thử nghiệm đo tác động của cách biểu diễn/tìm góc trong ngân sách hữu hạn; không chứng minh phép chia H tự tạo trạng thái tốt hơn. Gamma_execution lớn không tự là lỗi; không tùy tiện lấy modulo 2*pi khi hệ số H đã đổi thang.

Nguồn chính thức: [IBM QAOA tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm), [Qiskit Optimization 0.7 QAOA](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.minimum_eigensolvers.QAOA.html), [COBYLA](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.optimizers.COBYLA.html). Quy tắc chuẩn hóa là thiết kế của dự án suy ra từ dạng toán tử QAOA, không phải bảo đảm cải thiện do thư viện cung cấp.

## 2. Ba cấu hình đã cố định

| Cấu hình | Hamiltonian thực thi | Khởi tạo choice [beta,gamma] | Khởi tạo reference [beta,gamma] |
|---|---|---|---|
| raw_original | H_raw | [0.3,0.05] | [0.3,0.7] |
| normalized_matched | H_raw/kappa | [0.3,3.725] | [0.3,180.25] |
| normalized_common | H_raw/kappa | [0.3,1.0] | [0.3,1.0] |

Giữ A=B=3, p=1, shots=1024, COBYLA maxiter=35, rhobeg=1, Aer CPU/4 threads, state-memory budget 2048 MiB, ít nhất 2 GiB RAM khả dụng và max_seconds=300. maxiter là ngân sách lần đánh giá hàm; số lần thực tế có thể thấp hơn vì điều kiện dừng. Giới hạn thời gian được kiểm tra giữa các lần đánh giá, không ngắt cứng.

Seed 50,51,52,53,54 cho mọi cấu hình. Ba cấu hình × năm seed = 15 lượt mỗi instance, 30 cho cả hai. Protocol được ghi trước khi chạy mặc định. Đây là thăm dò; không tự thay khởi tạo sau khi xem kết quả và vẫn gọi là cùng protocol. Giữ riêng pilot seed 42 và xác nhận seed 45–49.

Hai phép so sánh định trước:

1. normalized_matched − raw_original: cùng trạng thái khởi đầu, đổi đơn vị H/gamma và hình học tìm kiếm.
2. normalized_common − normalized_matched: cùng đơn vị/thuật toán/ngân sách, đổi khởi tạo.

Không gộp các khởi tạo để so một bên có nhiều ngân sách hơn. Không chọn mẫu tốt nhất trong nhiều khởi tạo rồi coi nó là kết quả của một lượt.

## 3. Cài tệp và chạy trên Windows

Gói gồm chín tệp:

| Tệp | Thao tác/vai trò |
|---|---|
| src/ising.py | Cập nhật: helper đổi thang và quy đổi gamma |
| src/qaoa_experiment.py | Cập nhật: thực thi H được chọn, chấm năng lượng gốc, ghi metadata |
| src/scaling_campaign.py | Thêm: ba cấu hình, nguồn dữ liệu, manifest/resume |
| tests/test_hamiltonian_scaling.py | Thêm: năng lượng, trạng thái, hồi quy runner |
| tests/test_scaling_campaign.py | Thêm: ma trận, nguồn dữ liệu và tiếp tục |
| notebooks/10_qaoa_hamiltonian_scaling.ipynb | Thêm notebook mới |
| docs/qaoa_hamiltonian_scaling.md | Thêm hướng dẫn song ngữ |
| tasks/plan.md | Cập nhật review notebook 09 và bước chẩn đoán |
| tasks/todo.md | Cập nhật checklist |

Chép đủ chín tệp vào đúng đường dẫn. Tái sử dụng các module/fixture của notebook 08/09; không cài dependency mới. Chọn kernel Conda nt409-khiem/Python 3.12 rồi Restart Kernel để nạp đúng code.

Chạy choice trước:

1. Bước 1 kiểm tra ROOT/runtime/hash.
2. Bước 2 giữ `STUDY_INSTANCE="p1_choice"`, `RESUME_MANIFEST=None`; bảng cần 15 lượt với ba cấu hình và seed 50–54.
3. Bước 3 cần PASS: mười vector trên input thật và state-equivalence p=1/2 trên bài nhỏ. Bài nhỏ chỉ dùng kiểm chứng, không phải instance benchmark bổ sung.
4. Bước 4 đo tài nguyên và hiển thị năng lượng khởi đầu matched. Chứng minh chính ở Bước 3; mẫu hữu hạn có thể khác nhỏ vì số học/lấy mẫu. Đây không phải kết quả QAOA đã tối ưu.
5. Bước 5 tạo manifest; ghi lại đường dẫn được in.
6. Bước 6 chạy tuần tự, lưu từng lượt và cập nhật manifest. Giữ lượt hoàn tất có 0 nghiệm.
7. Bước 7 xem mỗi seed; Bước 8 xem trung bình/std và hai phép so sánh; Bước 9 đọc mẫu thật/gamma theo hai thang.
8. Bước 10 cần 15/15, không còn lượt, năm lượt mỗi cấu hình và mười hàng ghép. PASS chỉ xác minh tính nhất quán.
9. Lưu bản có output, ví dụ `10_qaoa_hamiltonian_scaling_choice.ipynb` trong notebooks/.

Sau đó Restart Kernel, đặt `STUDY_INSTANCE="p0_reference"`, giữ `RESUME_MANIFEST=None`, chạy Bước 1–10 và lưu `10_qaoa_hamiltonian_scaling_reference.ipynb`. Mỗi lần chỉ xử lý một input để dễ giữ output/tài nguyên.

## 4. Đọc kết quả và giới hạn kết luận

Chỉ số chính `optimal_pct_mean` là trung bình tỷ lệ placement tối ưu qua năm seed. Đọc cùng optimal_runs/valid_runs, tổng optimal_shots trong 5120 shots mỗi cấu hình, feasible_pct_mean, std giữa seed, số lần đánh giá và chi phí. Std không phải khoảng tin cậy. Chênh lệch trong bảng ghép là điểm phần trăm, dương nghĩa nhiều mẫu hơn ở seed đó. Những mẫu tối ưu hiếm cần kết luận thận trọng.

Mọi energy của mẫu, `estimated_qubo_energy` trong lịch sử và `optimizer_estimated_qubo_expectation` vẫn theo QUBO gốc. `execution_hamiltonian_expectation`/`optimizer_estimated_execution_expectation` là giá trị của toán tử đang thực thi; report ghi scale và offset để tái dựng. `optimal_point` dùng gamma_execution; `optimal_point_raw_hamiltonian` dùng gamma_raw. Không so năng lượng theo hai đơn vị mà quên quy đổi.

Placement hợp lệ không bắt buộc slack đúng; ground state toàn QUBO có yêu cầu mạnh hơn. Giữ riêng mode/đồng hạng và best-valid. None/NaN ở mục tiêu/gap nghĩa chưa tìm được nghiệm, không thay bằng 0. Không sửa bit trước khi chấm và không loại lượt hoàn tất có 0 nghiệm khỏi tỷ lệ thành công.

Đối chứng mới đều dùng (3,3). Cải thiện so với raw_original không tự chứng minh vượt (1,1) trên reference hoặc (3,12) trên choice của notebook 09. Muốn kết luận vượt các cấu hình riêng đó phải có đối chứng mới cùng phương pháp/ngân sách/seed. Đánh giá từng input riêng; không lấy trung bình gộp để che việc một input giảm chất lượng. Hai fixture cũng chưa chứng minh khả năng khái quát sang input mới hoặc ưu thế lượng tử.

## 5. Lưu, tiếp tục và bàn giao

Các báo cáo mới nằm trong `data/reference_results/phase4c_scaling_runs/`. Manifest có tên `scaling_<instance>_<campaign_id>.json`; mỗi report có arm_id, study, cấu hình, runtime/source hash và thông tin thang. Tính thống kê từ các báo cáo được manifest tham chiếu.

Nếu gián đoạn: Restart Kernel, giữ cùng input/design/code/runtime, đặt RESUME_MANIFEST đến đúng manifest Bước 5 đã in, chạy các cell theo thứ tự. Báo cáo cũ được xác minh; Bước 6 bỏ qua lượt đã hoàn tất. None ở Bước 5 tạo campaign mới. Không dùng manifest khác instance hoặc manifest 08/09.

Mã ising/runner đã cập nhật nên source hash khác trước. Các notebook cũ tiếp tục dùng nguyên thang khi không truyền tùy chọn mới, nhưng resume cũ bị từ chối theo đúng kiểm tra nguồn. Giữ các báo cáo 08/09 đã hoàn tất như dữ liệu lịch sử; không đổi hash trong manifest để ép tiếp tục.

Gửi hai notebook có output, hai manifest scaling và 30 JSON được tham chiếu. B/C có thể tiếp tục baseline/phân tích trong lúc A chạy. Review xong mới chọn cách tìm góc cho p=2 với đối chứng p=1 cùng ngân sách. Nếu cách chung chưa tốt trên cả hai, kết luận giới hạn này và chuyển sang độ sâu; không mở vô hạn ma trận penalty.

## 6. Kiểm chứng phần mềm trước bàn giao

34 bài kiểm tra tự động đạt, gồm hồi quy cũ, năng lượng/cực tiểu, trạng thái tương đương p=1/2, quy đổi góc, chấm QUBO gốc và kiểm tra manifest. Notebook được thực thi đủ mười code cell trên cả hai fixture với 30 lượt Aer Linux rút gọn, shots=64/maxiter=4. Kiểm tra ba nhóm năm seed, mười hàng ghép mỗi input, lưu nguồn, resume không chạy lại và từ chối manifest khác instance/đổi instance giữa đợt. Các lượt này xác minh workflow, không thay kết quả chất lượng Windows shots=1024/maxiter=35.

---

# Notebook 10 — Common penalties, execution scale and initialization

Updated 6 October 2026. Notebook 09's twenty Windows trials were reviewed against all 20,480 shots and both notebooks. Choice produced ten optimal shots at (3,12) versus six at (3,3), with four successful trials each. Reference produced twelve shots/five successful trials at (1,1) versus six/two at (3,12). A single shared (3,12) is not supported by these results.

This bounded exploratory diagnostic fixes the unchanged QUBO at (3,3) for both fixtures and p=1. For integer two-host feasible inputs, these weights ensure valid global minimizers. No new penalty grid/input or new dependency is introduced. Execution uses H/kappa, with kappa the maximum absolute non-identity coefficient (fallback 1). kappa=74.5/257.5 on choice/reference, with 20/23 qubits. Raw energy is kappa*expectation(H_execution)+offset_raw. Multiply raw gammas by kappa to preserve physical states; beta stays unchanged. Relative penalties/resource equations are not individually normalized.

The three arms are raw_original ([0.3,0.05] choice/[0.3,0.7] reference), normalized_matched ([0.3,3.725]/[0.3,180.25]), and normalized_common ([0.3,1.0] for both). All use shots 1024, maxiter 35, COBYLA rhobeg 1, CPU Aer/four threads, 2048 MiB state-memory budget, at least 2 GiB available and a 300-second budget checked between evaluations. Three arms times seeds 50–54 give fifteen trials per input/thirty total. Keep selection/confirmation seeds from earlier studies separate.

Keeping rhobeg=1 in execution coordinates changes the physical gamma step after normalization, so matched initial states do not imply identical optimization trajectories. The first predeclared contrast is normalized_matched minus raw_original (units/search geometry); the second is normalized_common minus normalized_matched (start only under identical normalized settings). Large normalized angles are not automatically errors; do not apply a naive 2*pi modulus after changing coefficient units. The exact state/energy checks establish equivalence, not a performance promise.

Copy all nine files into matching paths: updated src/ising.py and src/qaoa_experiment.py; new src/scaling_campaign.py, two test files, notebook/docs; updated tasks/plan.md and tasks/todo.md. Restart the project Conda Python 3.12 kernel. Execute steps 1–10 on choice first: environment, fixed design, raw/unit/tiny-state verification, probes, manifest, sequential trials, per-seed tables, grouped/paired contrasts, samples and final consistency. Expect 15/15, zero remaining, three five-run groups and ten paired rows. Save an executed choice copy; restart, select reference with RESUME_MANIFEST=None and repeat/save.

Sample energies, optimizer history and reported QUBO expectations remain in original units; execution expectation fields disclose the scaled values. Reports store the scale, raw offset, actual execution angles and their raw-H conversion. Score measured bits without repair, keep zero-solution trials/missing objectives, and distinguish placements from full-QUBO ground states and best-valid postselection from frequency ties. Primary metric is mean optimal-placement probability across seeds; inspect success counts, feasibility, variability, evaluation counts and costs. Standard deviation is not a confidence interval. Both controls here use (3,3); improvements do not establish superiority over notebook 09's per-instance settings. Analyze inputs separately; two fixtures do not establish generalization or quantum advantage.

New scope/storage: phase4c_hamiltonian_scaling under data/reference_results/phase4c_scaling_runs, with scaling_<instance>_<campaign_id>.json manifests. Provenance includes design/input/QUBO/scale/arms/seeds/runtime/code. Resume only the identical study; completed reports are verified/skipped. Changed source hashes intentionally reject old 08/09 resume while completed historical results remain readable. Submit two executed notebooks, two manifests and thirty referenced reports. Review before selecting a resource-probed p=2 study with matched p=1 budget controls; stop widening tuning matrices if a common treatment does not help both.

Authoritative API references are linked in the Vietnamese section. Global normalization is a project design inferred from the QAOA operator, not a documented guarantee of improved results.

Software verification passes 34 automated tests, including legacy regression, energy/minimizer preservation, p=1/2 state equivalence, angle conversion, raw scoring and manifest checks. All ten code cells execute on both fixtures with thirty reduced-budget Linux Aer trials (shots 64/maxiter 4). Three five-seed groups, ten paired rows per input, persistence and resume without reruns are verified; cross-instance resume and mid-run instance changes are rejected. These tests validate workflow rather than the user's default-budget Windows quality.
