> **English version below.**

# Phase 2 — QUBO cho Task Placement

## 1. Phạm vi và giả định

Kế thừa `docs/problem_spec.md` và `src/placement.py` của Phase 1:

- Mỗi task nằm trọn trên đúng một host; không chia nhỏ task.
- CPU/RAM của task và host là số nguyên dương, cùng đơn vị theo từng tài nguyên.
- `x[i,h]` cho biết task i được gán cho host h; `y[h]` cho biết host h được bật.
- Mục tiêu bổ sung của dự án là tối thiểu hóa số host bật: `min sum(y)`.
- Host bật nhưng không có task được phép, nhưng vẫn bị tính vào mục tiêu.

Phase 2 tạo QUBO và kiểm chứng tính đúng của phép chuyển đổi. Ising và QAOA thuộc Phase 3.
Các kết quả exact bên dưới chỉ dùng làm kiểm chứng trên bốn fixture nhỏ, không phải benchmark hiệu năng lượng tử.

## 2. Biến slack: biểu diễn tài nguyên còn dư

Ký hiệu `d[i,r]` là nhu cầu tài nguyên r của task i, `C[h,r]` là dung lượng host h.
Ràng buộc ban đầu:

$$\sum_i d_{i,r}x_{i,h}\le C_{h,r}y_h.$$

Thêm số nguyên slack không âm:

$$\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h=0,
\qquad 0\le s_{h,r}\le C_{h,r}.$$

Ví dụ host bật, CPU tối đa 5, đang dùng 4: slack=1, ràng buộc được thỏa mãn.
Nếu dùng 6 thì phải có slack=-1 mới thỏa mãn, nhưng miền biến không cho phép.
Vì vậy, bình phương biểu thức sau khi thêm slack không phạt việc còn dư tài nguyên.

## 3. Đổi slack nguyên thành bit

Với C nguyên dương, đặt `L = C.bit_length() = ceil(log2(C+1))`.
Chọn các trọng số:

$$[1,2,4,\ldots,2^{L-2}, C-(2^{L-1}-1)].$$

Nếu L=1 thì danh sách chỉ gồm `[C]`.
Mỗi slack là tổng có trọng số của L bit. Các tổng bao phủ toàn bộ số nguyên từ 0 đến C,
không vượt quá C. Đây là cách mã hóa có giới hạn; không phải lúc nào cũng là các lũy thừa 2 thuần túy.

Ví dụ:

| C | Trọng số | Miền giá trị slack |
|---:|---|---|
| 3 | [1, 2] | 0..3 |
| 5 | [1, 2, 2] | 0..5 |
| 6 | [1, 2, 3] | 0..6 |
| 8 | [1, 2, 4, 1] | 0..8 |

Một giá trị slack có thể có nhiều chuỗi bit biểu diễn. Vì vậy số nghiệm bit QUBO
có thể khác số phương án xếp task. Không diễn giải các cách mã hóa slack là các placement mới.

## 4. Hàm năng lượng QUBO

$$E(x,y,s)=\sum_h y_h
+P\sum_i\left(\sum_h x_{i,h}-1\right)^2
+P\sum_{h,r}\left(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h\right)^2.$$

Sau khi thay slack bằng các bit, mọi biểu thức trong ngoặc đều tuyến tính theo bit;
bình phương tạo đa thức bậc tối đa 2. `LinearEqualityToPenalty` thực hiện phép khai triển.
QUBO đầu ra chỉ có biến nhị phân, không còn ràng buộc tường minh.
Ràng buộc gốc được thể hiện thông qua các số hạng phạt trong năng lượng.

Năng lượng bao gồm cả hằng số. `qubo.objective.evaluate(bits)` giữ hằng số này.
Không bỏ hằng số khi so sánh năng lượng với công thức hoặc với mục tiêu Phase 1.

## 5. Vì sao chọn P=m+1?

Trong mô hình này, số host bật nằm trong 0..m. Nếu bài toán có nghiệm, tồn tại một
chuỗi bit hợp lệ với slack đúng và năng lượng không quá m.
Mọi vi phạm phương trình đều có sai số nguyên khác 0, nên bình phương sai số ít nhất là 1.
Vì vậy một chuỗi bit vi phạm có năng lượng ít nhất P. Chọn P>m bảo đảm nó không
thể là cực tiểu toàn cục khi có nghiệm hợp lệ. Bốn fixture có m=2 nên dùng P=3.

Đây là bảo đảm về mô hình toán học và cực tiểu toàn cục. Nó không bảo đảm QAOA
sẽ tìm được cực tiểu đó. Nếu đổi sang nhu cầu thực, mục tiêu có trọng số khác,
hoặc hệ số phạt riêng cho từng ràng buộc, phải xét lại lập luận.

Với phương án hợp lệ và slack đúng, năng lượng bằng số host bật, thường là 1 hoặc 2,
không nhất thiết bằng 0. Với slack sai, cùng một placement hợp lệ có thể mang năng lượng lớn hơn.

## 6. Thứ tự biến và giải mã

Thứ tự cố định:

1. `x_0_0, x_0_1, ..., x_(n-1)_(m-1)` theo task trước, host sau.
2. `y_0, ..., y_(m-1)`.
3. Slack theo host; mỗi host lần lượt CPU rồi RAM; mỗi nhóm theo chỉ số bit k tăng dần.

`decode_qubo()` lấy x,y rồi gọi lại `evaluate_model()` của Phase 1.
Không suy luận tính hợp lệ chỉ từ số host bật hoặc năng lượng một mẫu.
Chưa dùng chuỗi bit đo từ Qiskit trong Phase 2; thứ tự hiển thị kết quả đo sẽ được xử lý ở Phase 3.

## 7. Kiểm chứng exact trên fixture nhỏ

Mỗi fixture có 10 biến x,y. Duyệt toàn bộ `2^10=1024` tổ hợp, bao gồm cả tổ hợp vi phạm one-hot
và kích hoạt host không hợp lệ. Không chỉ duyệt 16 placement vốn đã thỏa one-hot.

Với x,y cố định, mỗi slack chỉ xuất hiện trong một số hạng bình phương độc lập. Giá trị tối ưu là:

$$s^*_{h,r}=\max\left(0,C_{h,r}y_h-\sum_i d_{i,r}x_{i,h}\right).$$

Vì nhu cầu không âm, giá trị này luôn thuộc 0..C và có thể được biểu diễn bởi các bit slack.
Do đó duyệt hết x,y và dùng slack tối ưu tìm được cực tiểu toàn cục của QUBO,
mà không phải duyệt mọi chuỗi bit slack. Phương pháp chỉ thích hợp cho fixture nhỏ.

Ngoài ra, notebook kiểm tra khai triển đa thức ở vector 0, từng vector đơn vị và từng cặp
vector đơn vị. Vì hai biểu thức đều bậc tối đa 2, các điểm này xác định toàn bộ hệ số
của hàm trên miền nhị phân (gộp b_i^2=b_i).

| Instance | Bit x,y | Bit slack | Tổng bit QUBO | P | Năng lượng nhỏ nhất | Mục tiêu gốc | Các (x,y) đạt cực tiểu |
|---|---:|---:|---:|---:|---:|---|---:|
| p0_reference | 10 | 13 | 23 | 3 | 2 | 2 host | 1 |
| p1_choice | 10 | 10 | 20 | 3 | 1 | 1 host | 1 |
| p1_tight | 10 | 8 | 18 | 3 | 2 | 2 host | 4 |
| p1_infeasible | 10 | 10 | 20 | 3 | 5 | Không có nghiệm hợp lệ | 12 |

Các con số chỉ áp dụng cho dữ liệu Phase 1 và cách mã hóa trong `src/qubo.py`.
Với cách ánh xạ trực tiếp một bit thành một qubit ở Phase 3, số qubit sẽ bằng tổng bit QUBO.

QUBO của `p1_infeasible` vẫn có cực tiểu vì có hữu hạn chuỗi bit. Những cực tiểu này
đều giải mã thành phương án không hợp lệ. Số 5 là năng lượng có phạt, không phải 5 host.
Ví dụ một cực tiểu bật 2 host, xếp được 3 task, bỏ sót 1 task: `2 + 3*1 = 5`.
Với bài toán có nghiệm, một mẫu QAOA không hợp lệ không chứng minh bài toán vô nghiệm.

## 8. Điều kiện hoàn thành và bàn giao

- Chạy notebook `03_qubo_model.ipynb` từ kernel mới; tất cả assert đạt.
- Ba fixture có nghiệm giữ đúng mục tiêu tối ưu Phase 1.
- Fixture vô nghiệm không bị công nhận nhầm là có nghiệm.
- Lưu báo cáo `data/reference_results/phase2_qubo.json` do notebook tạo.
- Commit module, notebook có kết quả chạy, tài liệu và báo cáo JSON.
- A dùng module này cho Ising/QAOA ở Phase 3.
- B tiếp tục dùng mô hình x,y và `evaluate_placement` / `evaluate_model`, không cần biến slack QUBO.
- C đối chiếu bằng `instance_id`, ghi rõ objective của bài toán gốc và năng lượng có phạt.

## Nguồn tham khảo

- Đề xuất NT409 Topic 16, mục 2 và mục 3: bài toán, one-hot, dung lượng, QUBO/Ising/QAOA.
- Qiskit Optimization 0.7.0 — Converters:
  https://qiskit-community.github.io/qiskit-optimization/tutorials/02_converters_for_quadratic_programs.html
- API LinearEqualityToPenalty:
  https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html

Lựa chọn P=m+1 và phép kiểm chứng tối ưu slack ở trên được suy ra trực tiếp cho mô hình
min_active_hosts với tài nguyên nguyên của dự án, không phải bảo đảm chung cho mọi bài toán QUBO.

---

# Phase 2 — QUBO formulation for task placement

## 1. Scope and assumptions

This phase builds on `docs/problem_spec.md` and `src/placement.py` from Phase 1:

- Each whole task is assigned to exactly one host; tasks are not split.
- Task demands and host capacities for CPU and RAM are positive integers, using
  the same unit for each resource.
- `x[i,h]` indicates whether task `i` is assigned to host `h`; `y[h]` indicates
  whether host `h` is active.
- The project's additional objective is to minimize the number of active hosts:
  `min sum(y)`.
- An active host with no tasks is permitted but still contributes to the objective.

Phase 2 constructs and validates the QUBO. The Ising conversion and QAOA belong
to Phase 3. Exact results below validate four small fixtures; they are not a
quantum performance benchmark.

## 2. Slack variables for unused resources

Let `d[i,r]` be task `i`'s demand for resource `r`, and `C[h,r]` be the
capacity of host `h`. The original constraint is:

$$\sum_i d_{i,r}x_{i,h}\le C_{h,r}y_h.$$

Introduce a nonnegative integer slack variable:

$$\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h=0,
\qquad 0\le s_{h,r}\le C_{h,r}.$$

For example, an active host with CPU capacity 5 and usage 4 has slack 1, so
the equality holds. Usage 6 would require slack -1, which is excluded. Squaring
the equality therefore does not penalize a host for having unused capacity.

## 3. Encoding integer slack with bits

For a positive integer capacity `C`, set
`L = C.bit_length() = ceil(log2(C+1))` and choose the weights:

$$[1,2,4,\ldots,2^{L-2}, C-(2^{L-1}-1)].$$

For `L=1`, the list contains only `[C]`. Slack is a weighted sum of `L` bits;
the subset sums cover every integer from 0 through `C` and never exceed `C`.
This is bounded-coefficient encoding, not necessarily ordinary powers of two.

| C | Weights | Slack range |
|---:|---|---|
| 3 | [1, 2] | 0..3 |
| 5 | [1, 2, 2] | 0..5 |
| 6 | [1, 2, 3] | 0..6 |
| 8 | [1, 2, 4, 1] | 0..8 |

Different bit strings may encode the same slack value. Hence the number of
QUBO bit solutions may differ from the number of task placements; different
slack encodings are not new placements.

## 4. QUBO energy function

$$E(x,y,s)=\sum_h y_h
+P\sum_i\left(\sum_h x_{i,h}-1\right)^2
+P\sum_{h,r}\left(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h\right)^2.$$

After encoding slack in bits, each expression inside parentheses is linear in
the bits. Squaring gives a polynomial of degree at most two.
`LinearEqualityToPenalty` performs this expansion. The resulting QUBO has only
binary variables and no explicit constraints; the original constraints are
represented by energy penalties.

The energy includes a constant term. `qubo.objective.evaluate(bits)` retains
it. Do not discard the constant when comparing the QUBO energy with this
formula or with the Phase 1 objective.

## 5. Why choose P=m+1?

Here the number of active hosts lies between 0 and `m`. If a feasible placement
exists, it has a correct slack encoding and energy at most `m`. Every violated
equality has a nonzero integer residual, whose square is at least 1. Thus an
invalid bit string has energy at least `P`. Choosing `P>m` prevents it from
being a global minimizer when a feasible placement exists. All four fixtures
have `m=2`, so we choose `P=3`.

This guarantees a property of the mathematical model and its global minimum;
it does not guarantee that QAOA finds that minimum. The argument must be
revisited for real-valued demands, another weighted objective, or different
penalties for different constraints.

With correct slack, a valid placement's energy equals its number of active
hosts, generally 1 or 2 rather than 0. Incorrect slack can increase the energy
of the same otherwise valid placement.

## 6. Variable order and decoding

The fixed order is:

1. `x_0_0, x_0_1, ..., x_(n-1)_(m-1)`: tasks first, then hosts.
2. `y_0, ..., y_(m-1)`.
3. Slack grouped by host, then CPU before RAM, then increasing bit index `k`.

`decode_qubo()` extracts `x,y` and calls Phase 1's `evaluate_model()`. Neither
the active-host count nor a single sample's energy alone establishes original
placement feasibility. Phase 2 does not yet process measured Qiskit bit strings;
their display order is handled in Phase 3.

## 7. Exact validation on small fixtures

Each fixture has 10 `x,y` bits. We enumerate all `2^10=1024` assignments,
including one-hot violations and arbitrary host activation, rather than only
the 16 one-hot task placements.

For fixed `x,y`, each slack appears in a separate squared penalty term. Its
optimal value is:

$$s^*_{h,r}=\max\left(0,C_{h,r}y_h-\sum_i d_{i,r}x_{i,h}\right).$$

Because demands are nonnegative, this value lies in `0..C` and can be encoded
with the slack bits. Enumerating all `x,y` assignments and selecting optimal
slack therefore finds the global QUBO minimum without enumerating every slack
bit string. This exact method is intended only for small fixtures.

The notebook also checks the expanded polynomial at the all-zero vector, at
each unit vector, and at every pair of unit vectors. Since both expressions
have degree at most two on binary bits (where `b_i^2=b_i`), these points
determine every coefficient.

| Instance | `x,y` bits | Slack bits | Total QUBO bits | P | Minimum energy | Original objective | Minimizing `x,y` assignments |
|---|---:|---:|---:|---:|---:|---|---:|
| p0_reference | 10 | 13 | 23 | 3 | 2 | 2 hosts | 1 |
| p1_choice | 10 | 10 | 20 | 3 | 1 | 1 host | 1 |
| p1_tight | 10 | 8 | 18 | 3 | 2 | 2 hosts | 4 |
| p1_infeasible | 10 | 10 | 20 | 3 | 5 | No feasible placement | 12 |

These counts apply to the Phase 1 data and the encoding in `src/qubo.py`.
With the direct one-bit-per-qubit mapping in Phase 3, the qubit count equals
the total QUBO bit count.

The `p1_infeasible` QUBO still has a minimum because it has finitely many bit
strings. All its minimizers decode to invalid placements. Its energy 5 is a
penalized score, not a count of 5 hosts. For example, one minimizer activates
2 hosts, places 3 tasks, and omits 1: `2 + 3*1 = 5`. An invalid QAOA sample
does not prove that a feasible instance has no solution.

## 8. Completion criteria and handoff

- Run `03_qubo_model.ipynb` from a fresh kernel; all assertions must pass.
- The three feasible fixtures must retain the Phase 1 optimal objectives.
- Do not misclassify the infeasible fixture as feasible.
- Save the notebook-generated `data/reference_results/phase2_qubo.json`.
- Commit the module, executed notebook, documentation, and JSON report.
- A uses the module for Ising/QAOA in Phase 3.
- B continues to use `x,y` and `evaluate_placement` / `evaluate_model`; B does
  not need QUBO slack variables.
- C joins results by `instance_id` and distinguishes the original objective
  from the penalized energy.

## References

- NT409 Topic 16 proposal, Sections 2 and 3: the problem, one-hot and capacity
  constraints, and QUBO/Ising/QAOA.
- Qiskit Optimization 0.7.0 — Converters:
  https://qiskit-community.github.io/qiskit-optimization/tutorials/02_converters_for_quadratic_programs.html
- LinearEqualityToPenalty API:
  https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html

The choice `P=m+1` and the optimal-slack validation follow from this project's
integer-resource, `min_active_hosts` model; they are not guarantees for every
QUBO formulation.
