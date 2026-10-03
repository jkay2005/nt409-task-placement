> **English version below.**

# Phase 3 — Ising và thử QAOA trên mô phỏng

## Tiền đề và giới hạn

Sử dụng lại [mô hình Phase 1](problem_spec.md) và [QUBO Phase 2](qubo_formulation.md).
`build_qubo()` sinh QUBO từ một instance, `build_ising()` dùng `qubo.to_ising()`.
Không thay đổi ý nghĩa của task: mỗi task được gán vào đúng một host.

Các instance gốc cần 18–23 qubit vì đã tính cả bit `x`, `y` và slack. Việc giữ
statevector mô phỏng 23 qubit đòi riêng `2**23` biên độ phức (khoảng 128 MiB
cho một mảng complex128), chưa kể bộ nhớ tạm của mạch và vòng tối ưu nhiều lượt.
Vì vậy notebook kiểm chứng Ising trên cả bốn fixture nhưng chỉ chạy QAOA trên
`data/instances/p3_demo.json` gồm 2 task, 2 host, 12 qubit. Đây là cùng mô hình
CPU/RAM và cùng hàm `build_qubo`, không phải bài Max-Cut không liên quan.

## Phép đổi biến

Với một bit QUBO `b[k]`, đặt `b[k] = (1-Z[k])/2`:

- Bit 0 tương ứng eigenvalue Z bằng +1.
- Bit 1 tương ứng eigenvalue Z bằng -1.
- Một tích `b[i]*b[j]` trở thành tổ hợp I, Z[i], Z[j], Z[i]Z[j].

Qiskit trả về `(H, offset)` với phương trình:

`E_QUBO(bits) = <bits|H|bits> + offset`.

Không bỏ `offset` khi so sánh năng lượng. Nó không ảnh hưởng bit tối ưu hay
động lực học QAOA vì là một dịch chuyển hằng số. Biến thứ k của QUBO ứng với
qubit k. Trong chuỗi bit theo cách in của Qiskit, qubit 0 nằm bên phải; helper
`integer_to_bits` đổi mẫu đo trở lại thứ tự biến trong `qubo.variables`.

Notebook `04_ising_qaoa.ipynb` kiểm tra hàm năng lượng tại vector 0, mọi bit
đơn lẻ và mọi cặp bit. Do cả hai hàm đều bậc tối đa 2 trên biến nhị phân, tập
điểm đó kiểm tra toàn bộ hệ số; một nghiệm Phase 2 được kiểm tra thêm để dễ đọc.

## QAOA thử nghiệm

Mạch với `reps=1` áp một cost layer `exp(-i gamma H)` và một mixer layer
`exp(-i beta sum X)`. `StatevectorSampler` lấy 1024 shots/lượt trên mô phỏng;
COBYLA giới hạn 35 lần đánh giá hàm mục tiêu (`maxiter`), không bảo đảm hội tụ.
QAOA tối ưu kỳ vọng năng lượng, không bảo đảm mẫu phổ
biến nhất là hợp lệ hay tối ưu. Chỉ tính `objective` của bài toán gốc cho mẫu
được `decode_qubo()` công nhận hợp lệ.

Trong báo cáo của nhánh A, ghi `feasible_probability` của placement (kiểm tra x,y),
`optimal_placement_probability` của placement dùng 1 host và
`qubo_ground_state_probability` của toàn bộ bit QUBO, gồm cả slack. Một placement
hợp lệ có thể có bit slack sai: khi ấy vẫn tính vào tỷ lệ placement hợp lệ, nhưng
năng lượng QUBO bị phạt và không tính vào xác suất cực tiểu QUBO.
Ghi thêm nghiệm hợp lệ tốt nhất đã quan sát, seed, shots, số layer và phiên bản thư viện.
`p3_demo` có đáp án chính xác 1 host; đáp án này chỉ là đối chứng, không được
chép vào kết quả QAOA. Mẫu vô nghiệm vẫn được giữ trong phân phối kết quả.

Notebook còn tính mốc lấy mẫu đều trên toàn bộ 4096 chuỗi bit của demo. Báo cáo
lưu cấu hình từ `CONFIG`, lịch sử tối ưu và mọi mẫu ở batch cuối để C kiểm tra
lại. Kỳ vọng của batch cuối được tính từ chính phân phối đó; ước lượng của
optimizer có thể khác vì dùng batch đo khác. Một lần chạy, một seed hoặc một
mẫu tối ưu chưa đủ kết luận QAOA tốt hơn mốc lấy mẫu đều.

## Thực hiện và điều kiện hoàn thành

1. Trên `main` đã cập nhật, tạo nhánh A; kiểm tra tài liệu Phase 1 có đường dẫn
   `docs/problem_spec.md`.
2. Dùng kernel Conda Phase 2 (`nt409-khiem`, Python 3.12); không cần thêm package.
3. Trong VS Code mở `notebooks/04_ising_qaoa.ipynb` và chạy các cell theo thứ tự.
4. Bước kiểm tra Ising phải in `PASS` cho cả năm instance.
5. Chạy QAOA trên `p3_demo`, đọc tỷ lệ khả thi và tỷ lệ tối ưu; không ép chúng
   bằng 1 hoặc giả định QAOA luôn cho nghiệm.
6. Lưu notebook có output và `data/reference_results/phase3_ising_qaoa.json`.
7. Gửi C cùng schema đầu vào và báo cáo; B đối chiếu `p3_demo` bằng baseline.

Chạy QAOA trực tiếp trên 18–23 qubit là công việc mở rộng sau khi đo thời gian
và bộ nhớ. Không dùng số liệu demo 12 qubit để tuyên bố lợi thế lượng tử.

## Nguồn

- Đề xuất NT409 Topic 16, mục 3, các bước QUBO → Ising → QAOA.
- [Qiskit Optimization 0.7.0: QUBO → Ising, offset, QAOA](https://qiskit-community.github.io/qiskit-optimization/tutorials/03_minimum_eigen_optimizer.html).
- [IBM Quantum: cấu trúc cost layer, mixer layer và vòng tối ưu QAOA](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm).

---

# Phase 3 — Ising and a simulated QAOA pilot

## Prerequisites and limits

Reuse the [Phase 1 problem specification](problem_spec.md) and the
[Phase 2 QUBO formulation](qubo_formulation.md). `build_qubo()` constructs the
QUBO from an instance; `build_ising()` calls `qubo.to_ising()`. The meaning of
a task remains unchanged: each task is assigned in full to exactly one host.

The original instances require 18–23 qubits after including `x`, `y`, and slack
bits. A 23-qubit simulated statevector alone contains `2**23` complex
amplitudes (about 128 MiB for one complex128 array), excluding circuit work
buffers and repeated optimizer evaluations. Therefore, the notebook checks the
Ising transformation on all four original fixtures but runs QAOA only on
`data/instances/p3_demo.json`, with 2 tasks, 2 hosts, and 12 qubits. It uses
the same CPU/RAM model and `build_qubo()` function, not an unrelated Max-Cut
example.

## Variable substitution

For a QUBO bit `b[k]`, substitute `b[k] = (1-Z[k])/2`:

- Bit 0 corresponds to Z eigenvalue +1.
- Bit 1 corresponds to Z eigenvalue -1.
- A product `b[i]*b[j]` becomes a combination of I, Z[i], Z[j], and Z[i]Z[j].

Qiskit returns `(H, offset)` such that:

`E_QUBO(bits) = <bits|H|bits> + offset`.

Keep `offset` when comparing energies. It is a constant shift, so it changes
neither the optimal bit string nor the QAOA dynamics. QUBO variable `k` maps
to qubit `k`. In a printed Qiskit bit string, qubit 0 is on the right;
`integer_to_bits` maps measured samples back to `qubo.variables` order.

The notebook `04_ising_qaoa.ipynb` checks the energy at the all-zero vector,
all single-bit vectors, and all pairs of bits. Both energy functions have
degree at most two on binary variables, so these inputs check every
coefficient. A Phase 2 reference minimizer is checked as an additional
readable example.

## QAOA pilot

With `reps=1`, the circuit applies one cost layer `exp(-i gamma H)` and one
mixer layer `exp(-i beta sum X)`. `StatevectorSampler` samples 1024 shots per
evaluation, while COBYLA is limited to 35 objective-function evaluations
(`maxiter`); reaching this budget does not establish convergence. QAOA minimizes
expected energy; the most frequent sample is not guaranteed to be feasible or
optimal. Only samples accepted by `decode_qubo()` receive an original-problem
`objective` value.

A's report records `feasible_probability` for the placement (`x,y`),
`optimal_placement_probability` for a valid one-host placement, and
`qubo_ground_state_probability` for the entire QUBO bit string, including
slack. A placement may satisfy the original constraints while its slack bits
are wrong; it then contributes to placement feasibility but receives a QUBO
penalty and does not contribute to QUBO ground-state probability. Also record
the best valid sample observed, seed, shots, layer count, and library versions.

The exact optimum for `p3_demo` is one host. This is a reference for comparison,
not a result to insert into QAOA's measured output. Invalid samples remain in
the observed distribution.

The notebook also calculates a uniform-sampling baseline over all 4096 demo
bit strings. The report records settings from `CONFIG`, optimization history,
and all samples in the final batch so C can recalculate the metrics. The final
batch mean is computed from that distribution; the optimizer estimate may
differ because it uses a separate sampling batch. A single run, seed, or
optimal sample does not establish an improvement over uniform sampling.

## Procedure and completion criteria

1. From an updated `main`, create A's branch and confirm the Phase 1 document
   is `docs/problem_spec.md`.
2. Use the Phase 2 Conda kernel (`nt409-khiem`, Python 3.12); no new package
   is needed.
3. Open `notebooks/04_ising_qaoa.ipynb` in VS Code and run the cells in order.
4. The Ising check must print `PASS` for all five instances.
5. Run QAOA on `p3_demo` and inspect feasibility and optimality rates; do not
   assume either is 1 or that QAOA always produces a solution.
6. Save the notebook with outputs and
   `data/reference_results/phase3_ising_qaoa.json`.
7. Share the input schema and report with C; B can use `p3_demo` for a
   classical baseline.

Running QAOA directly on 18–23 qubits is a later extension after measuring
runtime and memory use. Do not claim a quantum advantage from the 12-qubit
pilot data.

## References

- NT409 Topic 16 proposal, Section 3: QUBO → Ising → QAOA.
- [Qiskit Optimization 0.7.0: QUBO → Ising, offset, QAOA](https://qiskit-community.github.io/qiskit-optimization/tutorials/03_minimum_eigen_optimizer.html).
- [IBM Quantum: QAOA cost/mixer layers and classical optimization loop](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm).
