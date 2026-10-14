> **English version below.**

# Phase 3 — Ising và thử QAOA trên mô phỏng

## Tiền đề và giới hạn

Sử dụng lại [mô hình Phase 1](problem_spec.md) và [QUBO Phase 2](qubo_formulation.md).
`build_qubo()` sinh QUBO từ một instance, `build_ising()` dùng `qubo.to_ising()`.
Không thay đổi ý nghĩa của task: mỗi task được gán vào đúng một host.

Các instance gốc cần 18–23 qubit vì đã tính cả bit `x`, `y` và slack. Việc giữ
statevector mô phỏng 23 qubit đòi riêng `2**23` biên độ phức (khoảng 128 MiB
cho một mảng complex128), chưa kể bộ nhớ tạm của mạch và vòng tối ưu nhiều lượt.
Vì vậy notebook 04 kiểm chứng Ising trên cả bốn fixture nhưng chỉ chạy QAOA trên
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

Không dùng số liệu demo 12 qubit để tuyên bố lợi thế lượng tử.

## Mở rộng: dùng lại dữ liệu Phase 1–2

Notebook `05_qaoa_original_instances.ipynb` và module `src/qaoa_experiment.py`
chạy cùng mô hình trên bốn JSON gốc. Không cần tạo instance mới hoặc chạy lại
notebook 00–04. Dùng kernel Conda hiện tại. Notebook 05 dùng Aer SamplerV2
và psutil (đã có trong requirements-lock hiện tại); `requirements.txt` khai báo
psutil trực tiếp để đo RAM. Notebook 04 vẫn là demo ban đầu.

| Thứ tự | Instance | Qubit | Một statevector complex128 | Số host tối ưu gốc | Cực tiểu QUBO |
|---|---|---:|---:|---:|---:|
| 1 | `p1_tight` | 18 | 4 MiB | 2 | 2 |
| 2 | `p1_choice` | 20 | 16 MiB | 1 | 1 |
| 3 | `p1_infeasible` | 20 | 16 MiB | Không tồn tại | 5 |
| 4 | `p0_reference` | 23 | 128 MiB | 2 | 2 |

Kích thước một mảng là `16 * 2**N` byte, không phải tổng RAM chương trình.
Với Qiskit 2.5.2 và NumPy 2.5.3, đường lấy mẫu cũ
`StatevectorSampler → Statevector.sample_memory → _index_to_ket_array`
tạo nhãn cho mọi trạng thái trước khi lấy mẫu. Phép đổi mảng int64 sang
Unicode dùng dtype `<U21` (84 byte/phần tử): với 23 qubit, bảng trung gian
`23 * 2**23 * 84` byte tương đương **15,09 GiB**, chưa kể các mảng khác.
Đây là tính toán kích thước từ mã thư viện/dtype, không phải phép đo tổng RAM
trên máy người dùng. Giảm shots không loại bỏ bảng nhãn này.

Notebook 05 dùng **Aer SamplerV2, CPU, statevector, double precision** để tránh
đường cấp phát nhãn trên. QAOA và COBYLA vẫn là các lớp của Qiskit Optimization.
Mạch được transpile một lần trước vòng tối ưu. Không dựng ma trận Hamiltonian
đặc và không xuất toàn bộ statevector/phân phối `2**N` về Python.

### Cách chạy lại trên VS Code / Windows

1. Chép bản mới của `src/qaoa_experiment.py`, notebook 05, tài liệu này,
   `tests/test_qaoa_experiment.py` và `requirements.txt` vào đúng đường dẫn.
2. Dừng lượt cũ, Restart Kernel, chọn Conda `nt409-khiem`. Tắt các kernel
   notebook khác đang giữ nhiều RAM; chỉ đóng tab có thể chưa dừng kernel.
3. Nếu thiếu dependency, chạy trong terminal của môi trường Conda:
   `python -m pip install "qiskit-aer>=0.17,<0.18" "psutil>=7,<8"`, rồi Restart Kernel.
4. Chạy Bước 1–5. Mặc định kiểm tra lại đúng instance gây chậm:

```python
RUN_INSTANCE_IDS = ["p0_reference"]
CONFIG = {
    "seed": 42, "shots": 1024, "reps": 1, "maxiter": 35,
    "initial_point": [0.3, 0.7], "max_qubits": 23, "max_seconds": 300,
    "aer_threads": 4, "aer_memory_mb": 2048, "min_available_gib": 2.0,
}
```

5. Chạy Bước 5b để đo một lần lấy mẫu tại góc khởi tạo, đọc thời gian và RAM.
   Ước tính `sampling_seconds * (maxiter + 1)` chỉ tính phần lấy mẫu; không bảo đảm
   thời gian toàn bộ optimizer. Nếu đã gần/vượt 300 giây, dừng ở đây để xem lại.
6. Chạy Bước 6–8. Chỉ lượt hoàn tất được lưu JSON và đưa vào manifest.
   Lượt dừng sớm chỉ thông báo trong output, không lưu báo cáo timeout.
   Nếu muốn bỏ hai file timeout cũ, xóa đúng báo cáo
   `p0_reference_p1_seed42_20261003T010712873163Z.json` và manifest chỉ chứa lượt đó
   `manifest_20261003T010713278064Z.json` trong `data/reference_results/phase3_runs/`.

Aer dùng tối đa 4 luồng CPU, một mạch tại một thời điểm, tắt chạy song song
nhiều shot. `aer_memory_mb=2048` giới hạn lưu trạng thái lượng tử, **không giới
hạn cứng tổng RAM Python**. Kiểm tra còn ít nhất 2 GiB RAM khả dụng trước khi
bắt đầu. RSS đỉnh được hệ điều hành ghi nhận trong toàn bộ vòng đời tiến trình Python,
bao gồm cả cell/lượt chạy trước. Restart Kernel để đo từ đầu. Cách này ghi nhận
cả các cấp phát trong mã native của Aer mà polling thread có thể bỏ sót. Giá trị đo chính xác trên máy bạn
mới là căn cứ chọn cấu hình tiếp theo.

`max_seconds` vẫn được kiểm tra sau mỗi lần đánh giá; không ngắt một lần đang
chạy. Giữ giới hạn 300 giây để kiểm chứng tối ưu thực sự. `completed` chỉ có
nghĩa optimizer kết thúc và có mẫu cuối, không chứng minh cực tiểu toàn cục.
Tối ưu tốc độ/bộ nhớ không tự động cải thiện chất lượng nghiệm QAOA.

Mỗi lượt hoàn tất được lưu riêng trong `data/reference_results/phase3_runs/`.
Schema 2 ghi thêm phiên bản Aer, backend options và phép đo bộ nhớ; giữ nguyên
đầu vào, SHA-256, thứ tự biến, đáp án đối chứng, cấu hình, lịch sử và mẫu cuối.
Không ghi đè báo cáo demo. Cùng seed giữa hai backend có thể cho mẫu khác nhau;
không gộp các lượt như thể chúng có cùng backend. Đổi `RUN_INSTANCE_IDS` thành
`INSTANCE_IDS.copy()` để chạy cả bốn tuần tự khi lượt riêng đã phù hợp.

### Kiểm chứng bản tối ưu (2026-10-03)

Đo trên môi trường Linux của bên kiểm tra, không phải máy Windows của bạn.
Python 3.12.14, Qiskit 2.5.2, Aer 0.17.2, Qiskit Optimization 0.7.0.
Cùng mạch đã transpile của `p1_tight` 18 qubit, góc `[0.3, 0.7]`, 1024 shots,
seed 42; mỗi phép đo dùng tiến trình mới, ba lần mỗi backend:

| Phép đo trung vị | StatevectorSampler | Aer CPU |
|---|---:|---:|
| Một lần lấy mẫu | 2.428 s | 0.029 s |
| RSS đỉnh toàn tiến trình do OS ghi nhận | 1332.7 MiB | 174.0 MiB |

Kết luận thực nghiệm: giữ thay đổi backend; cải thiện rõ rệt về thời gian và
bộ nhớ trong phép đo này. Không dùng tỷ lệ này để cam kết tốc độ trên Windows.

Toàn bộ code cell notebook 05 cũng đã chạy từ đầu tới cuối với
`p0_reference` **23 qubit**, p=1, 1024 shots, maxiter=35, max_seconds=300:
**completed**, 32 lần đánh giá, solver 29.40 s,
RSS đỉnh 301.2 MiB. Có batch mẫu cuối và lưu
JSON/manifest thành công. Tám test vượt qua, gồm kiểm tra trạng thái QAOA trước/sau
transpile ở p=1, p=2, kiểm tra không gọi đường `Statevector.sample_memory`,
và từ chối lưu báo cáo timeout. Các số này là kiểm chứng triển khai, không
thay thế kết quả thí nghiệm do người dùng chạy.

### Mốc lấy mẫu đều trên fixture lớn

Không duyệt tất cả 8.388.608 chuỗi của instance 23 qubit. Phần tham chiếu vẫn
chính xác bằng cách duyệt 1024 vector `x,y` và đếm cách mã hóa slack:

- Placement hợp lệ phụ thuộc `x,y`; mọi cách chọn slack vẫn cho cùng placement.
  Xác suất hợp lệ là số vector `x,y` hợp lệ chia cho `2**base_count`.
- Với mỗi vector `x,y` đạt cực tiểu QUBO, đếm mọi cách mã hóa slack tối ưu.
  Trọng số như `[1, 2, 2]` có thể cho nhiều chuỗi cùng giá trị slack; không
  được đếm mỗi giá trị chỉ một lần. Tổng số chuỗi cực tiểu chia cho `2**N` là
  xác suất ground state QUBO khi lấy mẫu đều.
- Khi các bit slack độc lập, đều 0/1, `E[s]=sum(weights)/2` và
  `Var(s)=sum(w*w)/4`. Với `a=usage-C*y`,
  `E[(a+s)**2]=(a+E[s])**2+Var(s)`. Lấy trung bình các năng lượng có điều kiện
  trên `x,y` cho năng lượng trung bình chính xác.

Thuật toán tham chiếu giới hạn 16 bit `x,y`; nó phục vụ fixture nhỏ, không
thay thế MILP khi tăng quy mô task/host. Mốc lấy mẫu đều không thay thế
First-Fit, Best-Fit hoặc MILP của B.

### Đọc đúng trường hợp vô nghiệm và lượt chưa tìm được nghiệm

`p1_infeasible` có đáp án gốc `None`. Tỷ lệ placement tối ưu là `None`/`N/A`,
tỷ lệ khả thi bằng 0. QUBO vẫn có cực tiểu bằng 5, nhưng các mẫu đạt năng lượng
này vi phạm bài toán gốc. Ground state QUBO không trở thành nghiệm placement.
Với fixture có nghiệm, `best_observed_valid=None` chỉ nghĩa lượt QAOA chưa đo
được nghiệm hợp lệ, không chứng minh instance vô nghiệm.

Lượt một seed, p=1 chỉ kiểm chứng luồng trên đầu vào chung. Benchmark nhiều
seed, nhiều p và đối chiếu baseline của B là thí nghiệm tiếp theo. Khi đổi p,
`initial_point` phải có đúng `2*p` góc. Test tham chiếu chạy bằng:

```bash
python -m unittest discover -s tests
```

## Nguồn

- [Qiskit Aer: statevector, CPU, parallelism and quantum-state memory options](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html).
- [Qiskit Aer SamplerV2](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html).

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
buffers and repeated optimizer evaluations. Therefore, notebook 04 checks the
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

Do not claim a quantum advantage from the 12-qubit pilot data.

## Extension: reuse the Phase 1–2 inputs

Notebook `05_qaoa_original_instances.ipynb` and module `src/qaoa_experiment.py`
run the same model on the four original JSON files. No new instance or rerun
of notebooks 00–04 is required. Reuse the current Conda kernel. Notebook 05
uses Aer SamplerV2 and psutil (both already present in the current lock file).
`requirements.txt` explicitly declares psutil for memory measurements.
Notebook 04 remains the original demo.

| Order | Instance | Qubits | One complex128 statevector | Original optimal hosts | Minimum QUBO energy |
|---|---|---:|---:|---:|---:|
| 1 | `p1_tight` | 18 | 4 MiB | 2 | 2 |
| 2 | `p1_choice` | 20 | 16 MiB | 1 | 1 |
| 3 | `p1_infeasible` | 20 | 16 MiB | Does not exist | 5 |
| 4 | `p0_reference` | 23 | 128 MiB | 2 | 2 |

One array occupies `16 * 2**N` bytes, not the total process memory.
With Qiskit 2.5.2 and NumPy 2.5.3, the old sampling path
`StatevectorSampler → Statevector.sample_memory → _index_to_ket_array`
builds labels for all outcomes before sampling. Converting the int64 array to
Unicode produces dtype `<U21` (84 bytes per element). At 23 qubits, that
intermediate table alone needs `23 * 2**23 * 84` bytes, or **15.09 GiB**, before
other arrays. This is a size calculation from library code and dtype, not a
measurement of total RAM on the user's machine. Reducing shots does not remove
this table.

Notebook 05 uses **Aer SamplerV2, CPU, statevector, double precision** to avoid
that allocation path. QAOA and COBYLA remain Qiskit Optimization classes.
The circuit is transpiled once before optimization. No dense Hamiltonian or
full statevector/probability dictionary is exported to Python.

### Rerunning in VS Code / Windows

1. Copy the updated `src/qaoa_experiment.py`, notebook 05, this document,
   `tests/test_qaoa_experiment.py`, and `requirements.txt` into their locations.
2. Stop the old run, Restart Kernel, and select Conda `nt409-khiem`. Shut down
   other memory-heavy notebook kernels; closing a tab may leave its kernel alive.
3. If dependencies are missing, run in the Conda terminal:
   `python -m pip install "qiskit-aer>=0.17,<0.18" "psutil>=7,<8"`, then Restart Kernel.
4. Execute Steps 1–5. The default retries the affected instance:

```python
RUN_INSTANCE_IDS = ["p0_reference"]
CONFIG = {
    "seed": 42, "shots": 1024, "reps": 1, "maxiter": 35,
    "initial_point": [0.3, 0.7], "max_qubits": 23, "max_seconds": 300,
    "aer_threads": 4, "aer_memory_mb": 2048, "min_available_gib": 2.0,
}
```

5. Run Step 5b for one initial-angle sampling evaluation. Inspect time and RAM.
   `sampling_seconds * (maxiter + 1)` estimates sampling work only, not total
   optimizer runtime. If it approaches/exceeds 300 seconds, pause to investigate.
6. Run Steps 6–8. Only completed runs produce JSON reports and manifest entries.
   An interrupted run only prints a diagnostic; no timeout report is written.
   To remove the old timeout output, delete exactly
   `p0_reference_p1_seed42_20261003T010712873163Z.json` and its single-run manifest
   `manifest_20261003T010713278064Z.json` from `data/reference_results/phase3_runs/`.

Aer uses up to four CPU threads, one circuit at a time, without parallel shots.
`aer_memory_mb=2048` limits quantum-state storage, **not total Python memory**.
The runner checks for at least 2 GiB available RAM before starting. The OS records peak process RSS over the entire Python process lifetime,
including earlier cells/runs. Restart the kernel for a clean measurement.
This captures allocations inside native Aer code that a polling thread may miss. Measurements on the user's machine determine the
appropriate configuration.

`max_seconds` is still checked after each evaluation; it cannot interrupt a
running evaluation. Keep the 300-second budget to verify the performance fix.
`completed` means optimization returned and final samples exist, not proof of
the global minimum. Faster/lighter simulation does not itself improve QAOA
solution quality.

Each completed run is saved separately in `data/reference_results/phase3_runs/`.
Schema 2 adds Aer version, backend options, and memory measurements, retaining
input, SHA-256, variable order, references, settings, history, and final samples.
The original demo report is preserved. Identical seeds across different
backends can produce different samples; retain backend identity in comparisons.
Set `RUN_INSTANCE_IDS = INSTANCE_IDS.copy()` to run all four sequentially after
the single-instance check.

### Optimization verification (2026-10-03)

Measured in the reviewer's Linux environment, not the user's Windows machine.
Python 3.12.14, Qiskit 2.5.2, Aer 0.17.2, Qiskit Optimization 0.7.0.
Identical transpiled 18-qubit `p1_tight` circuit, angles `[0.3, 0.7]`, 1024 shots,
seed 42; fresh process per measurement, three measurements per backend:

| Median measurement | StatevectorSampler | Aer CPU |
|---|---:|---:|
| One sampling evaluation | 2.428 s | 0.029 s |
| OS-recorded lifetime peak process RSS | 1332.7 MiB | 174.0 MiB |

Verdict: retain the backend change; it materially reduces time and memory in
this experiment. These ratios are not a Windows performance guarantee.

Every code cell in notebook 05 also executed sequentially with **23-qubit**
`p0_reference`, p=1, 1024 shots, maxiter=35, max_seconds=300:
**completed**, 32 evaluations, 29.40 s solver time,
301.2 MiB lifetime peak RSS. Final samples,
JSON, and manifest were produced successfully. Eight tests passed, including
QAOA state equivalence before/after transpilation for p=1 and p=2, avoiding
`Statevector.sample_memory`, and refusal to save timeout reports. These are
implementation checks, not replacements for the user's experimental results.

### Uniform baseline for larger fixtures

Do not enumerate all 8,388,608 strings of the 23-qubit case. Exact references
enumerate the 1,024 `x,y` vectors and count slack encodings instead:

- Placement feasibility depends on `x,y`; every slack string has the same
  decoded placement. Feasibility probability is the number of feasible
  `x,y` vectors divided by `2**base_count`.
- For each `x,y` vector attaining the QUBO minimum, count every encoding of
  its optimal slack. Weights such as `[1, 2, 2]` can encode one slack value
  in multiple ways; counting each value once would be incorrect. The total
  number of minimizing full strings divided by `2**N` gives the uniform
  QUBO ground-state probability.
- For independent uniform slack bits, `E[s]=sum(weights)/2` and
  `Var(s)=sum(w*w)/4`. With `a=usage-C*y`,
  `E[(a+s)**2]=(a+E[s])**2+Var(s)`. Averaging conditional energies over
  `x,y` gives the exact uniform mean energy.

The reference algorithm is limited to 16 `x,y` bits. It supports tiny
fixtures and does not replace MILP for larger task/host counts. Uniform
sampling also does not replace B's First-Fit, Best-Fit, or MILP baselines.

### Infeasible instances and runs without a feasible sample

`p1_infeasible` has no original optimum (`None`). Optimal-placement
probability is `None`/`N/A`, and feasibility probability is zero. Its QUBO
still has minimum energy 5, but minimizing samples violate the original
problem. A QUBO ground state is not an original feasible placement here.
On a feasible instance, `best_observed_valid=None` only means that the QAOA
run did not observe a feasible sample; it does not prove infeasibility.

A single seed with p=1 validates the workflow on shared inputs. Multiple
seeds, depths, and comparison with B's baselines require a subsequent
benchmark. When changing p, `initial_point` must contain `2*p` angles.
Run the reference tests with:

```bash
python -m unittest discover -s tests
```

## References

- [Qiskit Aer: statevector, CPU, parallelism and quantum-state memory options](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html).
- [Qiskit Aer SamplerV2](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html).

- NT409 Topic 16 proposal, Section 3: QUBO → Ising → QAOA.
- [Qiskit Optimization 0.7.0: QUBO → Ising, offset, QAOA](https://qiskit-community.github.io/qiskit-optimization/tutorials/03_minimum_eigen_optimizer.html).
- [IBM Quantum: QAOA cost/mixer layers and classical optimization loop](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm).
