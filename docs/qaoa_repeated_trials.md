> **English version below.**

# Nhánh A sau bàn giao — khảo sát QAOA nhiều lượt có kiểm soát

## 1. Vị trí trong kế hoạch

A xác nhận đã bàn giao cho B/C ngày 05/10/2026. Mốc demo Phase 3 giữ nguyên. Đề cương `nt409-topic16-proposal.pdf`, mục 5, đặt baseline cổ điển/MILP ở tuần 4–5, khảo sát hệ số phạt ở tuần 6 và nhiều seed với p=1/2/3 ở tuần 7. Số tuần là thứ tự kế hoạch, không dùng để xác nhận ngày thực hiện hoặc tiến độ B/C.

Trong lúc B/C làm việc, A chuẩn bị thí nghiệm lặp trên dữ liệu gốc. Tài liệu gọi đợt này là **A1**, tên tổ chức nội bộ; không có nghĩa cả nhóm đã hoàn tất một phase mới. Kết quả của A1 giúp quyết định các khảo sát tiếp theo.

## 2. Vì sao cần nhiều lượt?

QAOA có hai điểm dễ nhầm:

- Thuật toán tối ưu **năng lượng trung bình** của phân phối mẫu, không trực tiếp tối đa hóa số mẫu placement hợp lệ.
- Bộ tối ưu COBYLA bắt đầu từ một vector góc. Những góc khác nhau có thể dẫn đến vùng năng lượng khác nhau; số phép đo hữu hạn cũng tạo biến thiên giữa seed.

Seed không phải lời giải, không phải góc khởi tạo. Runner hiện dùng seed cho lấy mẫu và biên dịch mạch. `initial_point` xác định góc beta/gamma. Với p=1, vector là `[beta_0, gamma_0]`.

Một lượt có 0 mẫu hợp lệ không chứng minh bài toán vô nghiệm. Một lượt có nghiệm tối ưu cũng chưa chứng minh thuật toán ổn định. Vì vậy cần giữ mọi lượt đã hoàn tất và tính tỷ lệ/trung bình theo thiết kế đã chọn trước.

## 3. Thiết kế đã chọn cho đợt A1

| Yếu tố | Giá trị | Lý do |
|---|---|---|
| Dữ liệu mặc định | p1_tight, p1_choice | Dùng lại dữ liệu gốc; lần lượt 18 và 20 qubit |
| Hệ số phạt | P=3 | Giữ nguyên mô hình đã kiểm chứng |
| Độ sâu | p=1 | Giữ nguyên độ sâu của lượt đầu |
| Số phép đo | 1024/lượt lấy mẫu | Có thể đối chiếu với các lượt trước cùng ngân sách |
| COBYLA | maxiter=35 | Giữ cùng ngân sách đánh giá |
| Seed | 42, 43, 44 | Ba lượt cho mỗi điểm khởi tạo |
| Điểm khởi tạo `goc_cu` | [0.3, 0.7] | Điểm đã dùng trước đó |
| Điểm khởi tạo `gamma_nho` | [0.3, 0.05] | Thử một vùng góc bổ sung, không phải góc tối ưu đã được chứng minh |
| Bộ mô phỏng | Aer CPU, statevector double | Dùng bản đã xử lý vấn đề RAM |
| Tài nguyên | 4 luồng; Aer 2048 MiB; RAM khả dụng tối thiểu 2 GiB | Chạy từng lượt tuần tự |
| Thời gian | 300 giây/lượt, kiểm tra giữa các lần đánh giá | Đây không phải ngắt cứng đúng 300 giây |

Mỗi instance có 2 điểm khởi tạo × 3 seed = 6 lượt. Hai instance mặc định có tổng 12 lượt. Thử nghiệm này thay hai yếu tố seed/khởi tạo trong ma trận, nhưng giữ các yếu tố khác; khi tính độ phân tán theo seed phải tách hai điểm khởi tạo thành hai nhóm.

Gamma nhỏ làm thay đổi góc pha của cost layer; đây chỉ là một điểm bắt đầu khác. Không suy ra giảm gamma luôn cải thiện nghiệm, và không so sánh các góc tối ưu một cách đơn giản khi hàm năng lượng/penalty đã đổi.

Đợt p0_reference chạy riêng bằng cùng ma trận, gồm 6 lượt ở 23 qubit. Chưa tăng task/host hoặc dùng dữ liệu lớn hơn trong A1. p1_infeasible là đối chứng tùy chọn: nó không có placement hợp lệ, nên không dùng để đánh giá “QAOA tìm được số host tối ưu”.

## 4. File cần bổ sung và tiền đề

Thêm [notebooks/06_qaoa_repeated_trials.ipynb](../notebooks/06_qaoa_repeated_trials.ipynb) vào repo. Dùng [src/qaoa_experiment.py](../src/qaoa_experiment.py) bản Aer đã bàn giao, cùng [src/qubo.py](../src/qubo.py) và dữ liệu trong [data/instances](../data/instances/).

Không cần thay thế notebook 04/05 hoặc đổi mô hình. Không có thư viện mới. Kernel vẫn là Conda `nt409-khiem`, Python 3.12.14; Python 3.14 cài toàn máy không phải kernel của thí nghiệm.

Tài liệu này và `tasks/plan.md`, `tasks/todo.md` ghi phạm vi và công việc còn lại. Các mục “A chạy trên Windows” chỉ đánh dấu hoàn tất khi có báo cáo thực tế. Bản kiểm thử do trợ lý chạy không thay thế các lượt của A.

## 5. Thực hiện trong VS Code/Jupyter

1. Cập nhật bản repo đã bàn giao, dùng nhánh làm việc hiện tại của A hoặc tạo nhánh mới từ phiên bản bàn giao nếu cần. Kiểm tra `git status` trước khi chuyển nhánh; không bắt buộc tạo thêm nhánh khi đã có nhánh phù hợp.
2. Chép các file mới theo đường dẫn trong gói. Mở notebook 06, chọn kernel `nt409-khiem`, Restart Kernel. Đóng kernel 05 nếu còn chạy.
3. Bước 1 kiểm tra môi trường: in Python/Qiskit/Aer, đường dẫn và RAM khả dụng. Không cần nâng cấp thư viện để chạy A1.
4. Bước 2 giữ cấu hình mặc định: bảng kế hoạch có 12 hàng. Mỗi hàng là một bộ dữ liệu, nhãn khởi tạo và seed.
5. Bước 3 xem kích thước và tham chiếu: tight=18 qubit, tối ưu 2 host; choice=20 qubit, tối ưu 1 host.
6. Bước 4 đo thử: xem thời gian lấy mẫu và RAM trước khi chạy tối ưu. Ước tính chưa gồm mọi chi phí và không bảo đảm thời gian cuối. Nếu chi phí không phù hợp, dừng để xác định nguồn lực/thiết kế trước khi chạy tiếp.
7. Bước 5 chuẩn bị ID đợt và đường dẫn chỉ mục. Đây chưa phải một lượt chạy QAOA. Chỉ mục được ghi sau khi có lượt hoàn tất.
8. Bước 6 chạy tuần tự; báo cáo được lưu ngay sau từng lượt. Lượt chạm ngân sách không có JSON kết quả riêng; đợt dừng, các lượt hoàn tất trước đó vẫn giữ nguyên.
9. Bước 7 đọc 12 hàng kết quả nếu mọi lượt hoàn tất. Bước 8 có bốn nhóm: tight/goc_cu, tight/gamma_nho, choice/goc_cu, choice/gamma_nho.
10. Bước 9 kiểm tra mẫu thô của một lượt; Bước 10 đối chiếu chỉ mục với các báo cáo nguồn. Kết thúc phải có PASS nếu các file khớp.
11. Lưu notebook có đầu ra và gửi C chỉ mục cùng tất cả báo cáo nó tham chiếu.

Nếu chạy lại riêng cell Bước 6, những lượt hoàn tất trong đợt hiện tại được bỏ qua. Nếu chạy lại từ Bước 2 với `RESUME_MANIFEST=None`, bạn đang bắt đầu đợt mới, không phải tiếp tục đợt cũ. Muốn tiếp tục sau khi restart, đặt `RESUME_MANIFEST` bằng đường dẫn chỉ mục cũ và giữ nguyên dữ liệu/cấu hình. Notebook kiểm tra cả các phiên bản thư viện và hệ điều hành của báo cáo cũ. Nếu không khớp, notebook dừng để tránh trộn thiết kế/môi trường.

## 6. Chạy p0_reference sau đợt mặc định

Khởi động lại kernel, sửa Bước 2:

```python
RUN_INSTANCE_IDS = ["p0_reference"]
RESUME_MANIFEST = None
```

Giữ các thông số khác. Chạy tuần tự từ Bước 1 đến 10. Bảng kế hoạch sẽ có 6 lượt. Số qubit vẫn 23. Không chạy đồng thời với một kernel nặng khác.

Có thể đo được nghiệm sau một số khởi tạo, nhưng không có bảo đảm. Nếu cả sáu lượt có 0 mẫu hợp lệ, đây là dữ liệu về chất lượng của cấu hình p=1/P=3/ngân sách 35 lần đánh giá. Kết quả đó là căn cứ cho khảo sát tiếp theo, không phải đáp án gốc và không tự chứng minh sai mô hình.

## 7. Chỉ số cần giải thích đúng

| Cột | Ý nghĩa |
|---|---|
| `completed_runs` | Số lượt hoàn tất trong nhóm; so với `planned_runs` để biết còn thiếu |
| `valid_runs` | Số lượt có ít nhất một mẫu placement hợp lệ |
| `optimal_runs` | Số lượt có ít nhất một mẫu placement tối ưu; N/A cho bộ vô nghiệm |
| `feasible_pct_mean` | Trung bình phần trăm mẫu hợp lệ giữa các seed trong nhóm |
| `feasible_pct_std` | Độ lệch chuẩn mẫu giữa seed, đơn vị điểm phần trăm; một lượt chưa đủ tính |
| `optimal_pct_mean` | Trung bình phần trăm placement tối ưu; không phải xác suất full bitstring đạt cực tiểu QUBO |
| `mean_qubo_energy` | Trung bình năng lượng mẫu cuối giữa các lượt; chỉ so trực tiếp trong cùng mô hình/P |
| `mean_solver_seconds` | Trung bình thời gian bộ giải; giải mã nằm trong trường riêng |
| `uniform_feasible_pct` | Mốc tỷ lệ placement hợp lệ khi lấy mẫu đều, tính chính xác |

Ví dụ: một lượt có 10 mẫu hợp lệ trong 1024 shots thì tỷ lệ mẫu là 10/1024. Nếu hai trong ba lượt có ít nhất một nghiệm thì số lượt có nghiệm là 2/3. Hai số này trả lời hai câu hỏi khác nhau.

`observed_best_objective=None` không đổi thành 0 host. Cực tiểu QUBO yêu cầu cả slack đúng; placement hợp lệ/tối ưu chỉ kiểm tra x,y và mục tiêu gốc. Mẫu phổ biến nhất được báo cáo riêng với nghiệm hợp lệ tốt nhất.

Mỗi nhóm chỉ có ba seed, chưa đủ kết luận thống kê mạnh. So sánh nhóm phải ghi số lượt, seed, điểm khởi tạo và ngân sách; không chỉ dùng lượt tốt nhất. Chọn cấu hình từ A1 là bước khám phá; cần các lượt xác nhận riêng trước khi gọi là hiệu quả ổn định.

## 8. Định dạng bàn giao cho C

- Báo cáo từng lượt nằm trong `data/reference_results/phase3_runs/`, giữ cấu trúc schema 2 của notebook 05: `metrics`, `reference`, `final_samples`, `config`, thông tin đầu vào/môi trường.
- Bổ sung `experiment`: ID đợt, mã băm thiết kế, khóa lượt, nhãn điểm khởi tạo. `scope` của từng báo cáo vẫn là lượt một seed theo runner cũ; phân biệt đợt bằng `experiment`.
- Chỉ mục đợt nằm trong `data/reference_results/phase4a_runs/campaign_...json`, schema 1, scope `phase4a_repeated_qaoa_pilot`.
- Chỉ mục chứa thiết kế, danh sách dự kiến, các lượt hoàn tất và đường dẫn. Không coi chỉ mục/notebook/báo cáo của cùng lượt là các phép thử khác nhau.
- `remaining_run_keys` chỉ cho biết chưa có báo cáo hoàn tất trong đợt; không phân biệt chưa chạy với đã thử nhưng không hoàn tất. C không dùng thư mục báo cáo hoàn tất để suy ra mọi lượt đã thử đều thành công.
- Không trộn với số liệu demo hoặc các lượt notebook 05 khác khi tính nhóm A1. Những lượt đó có thể nằm trong cùng thư mục nhưng không thuộc cùng `campaign_id`.

RAM đỉnh trong báo cáo là đỉnh toàn vòng đời tiến trình Python, gồm các lượt/cell trước. Chạy tuần tự và giải phóng đối tượng giúp hạn chế tích lũy, nhưng không biến số đo này thành RAM tăng thêm riêng từng lượt.

## 9. Điều kiện hoàn thành A1 và bước sau

Phần chuẩn bị hoàn thành khi notebook chạy được, báo cáo/checkpoint truy được nguồn và ví dụ/hướng dẫn rõ ràng. Phần thí nghiệm của A chỉ hoàn thành sau khi A thực sự chạy trên Windows và bàn giao kết quả.

Sau đợt mặc định và p0_reference, xem chất lượng/độ phân tán trước khi chốt khảo sát P. Hiện `build_qubo(instance, penalty=...)` chỉ có một P chung. Nếu nghiên cứu hai hệ số độc lập cho gán task và dung lượng, cần sửa mô hình và kiểm chứng riêng; ký hiệu A/B của penalty không phải hai thành viên A/B.

Tiếp theo mới khảo sát p=1/2/3 với các khởi tạo và ngân sách được định nghĩa. Không tăng P, p, shots, maxiter và đổi dữ liệu cùng lúc rồi quy tất cả cải thiện cho một yếu tố. B/C vẫn tiếp tục baseline và tổng hợp theo phân công. Kỳ vọng của đề cương là đo lường/giải thích trung thực, không có cam kết QAOA thắng MILP hoặc mọi lượt đều ra nghiệm.

---

# Branch A after handoff — controlled repeated QAOA trials

A confirmed the B/C handoff on 5 October 2026. The proposal schedules classical baselines/MILP before penalty and multi-seed/depth experiments. This A1 increment prepares repeated trials while B/C work; it is not the final benchmark or a claim about their completion.

## Design and interpretation

Reuse the original CPU/RAM instances and existing Aer runner. Fix P=3, p=1, 1024 shots, COBYLA maxiter=35, 300 seconds checked between evaluations, four Aer threads, 2048 MiB quantum-state memory and at least 2 GiB available system RAM.

Cross seeds 42, 43, 44 with `goc_cu=[0.3,0.7]` and `gamma_nho=[0.3,0.05]`. The latter is an exploratory initial point, not a known optimum. Seed controls sampling/transpilation randomness; initial_point specifies beta/gamma. QAOA minimizes expected energy, not feasibility directly.

Default: p1_tight (18 qubits) and p1_choice (20), 12 sequential trials. Run p0_reference (23) separately, six trials, with the same settings. Optional p1_infeasible is an infeasibility control. Do not enlarge the input in A1.

## Files and execution

Add notebook 06 and this document; retain notebooks 04/05 and the existing modules. Use Conda Python 3.12 and the dependencies already needed by notebook 05. Restart the kernel and do not run heavy notebooks concurrently.

1. Check environment versions and paths.
2. Fix the design and confirm 12 planned rows.
3. Inspect sizes and independent original/QUBO references.
4. Probe sampling time and memory; estimates are not guarantees.
5. Initialize a campaign or resume its saved manifest.
6. Run sequentially, persisting each completed report and checkpoint immediately.
7. Inspect each observed run, including zero-feasibility completed trials.
8. Aggregate separately by instance and initial-point ID across seeds.
9. Inspect raw samples without repairs.
10. Cross-check reports against the campaign index and hand the outputs to C.

For p0_reference, restart, select only that instance, set RESUME_MANIFEST=None and run the notebook. For a resumed campaign, provide its manifest path and keep the identical design/input, library versions and operating-system environment. Rerunning only the execution cell skips completed trials; rerunning setup with no resume creates a new campaign.

## Metrics and persistence

`valid_runs` counts runs with at least one feasible sample. `feasible_pct_mean` averages sample-level feasibility percentages across seeds. These quantities are different. Sample standard deviation uses ddof=1 and is unavailable for one run. Three seeds provide only a small exploratory sample.

Original optimal placements are distinct from complete QUBO ground states because slack may be wrong. Missing observed objectives remain null, never zero hosts. Report most-frequent validity separately from the best observed feasible solution.

Per-run reports retain schema 2 and nested metrics/reference/final_samples in phase3_runs, with an added experiment object linking campaign/design/run/initial point. The schema-1 campaign index lives in phase4a_runs. Count each run once, not once per report/notebook/index. Remaining keys mean no completed report, without classifying whether a trial was attempted. No interrupted-run result JSON is saved.

The memory peak is process-lifetime RSS, including earlier activity, and the Aer memory setting is not a cap on all Python RAM. Only A's actual Windows outputs establish their experimental result; implementation checks on another machine remain separate.

## Next milestones

Review A1 before designing penalty sweeps. The current API supports one common P; independent assignment/capacity penalties require a separate model change and verification. Depth p=1/2/3 follows with explicitly recorded budgets and initializations. Keep model/input and other factors controlled. The proposal seeks honest quantitative results, not guaranteed optimal samples or quantum advantage.
