> **English version below.**

# Notebook 09 — Xác nhận cặp penalty bằng seed mới

Cập nhật ngày 06/10/2026. Đây là bước tiếp theo của nhánh A sau pilot notebook 08 đã chạy và review đủ 24 lượt Windows. Dùng các module hiện tại để xác nhận một ứng viên trước khi khảo sát độ sâu QAOA. B/C tiếp tục baseline và tổng hợp trên cùng JSON đầu vào.

## 1. Câu hỏi cần trả lời

Pilot cho thấy cặp (lambda_assign,lambda_capacity)=(3,12) đáng giữ lại, nhưng chưa đủ bằng chứng cải thiện ổn định:

- Choice: hai khởi tạo của (3,12) có 64 mẫu hợp lệ/4 mẫu tối ưu, so với 59/3 của (3,3).
- Reference: (3,12) có 4 mẫu tối ưu, so với 5 của (1,1). Tất cả placement hợp lệ reference đều tối ưu 2 host.
- Mỗi khởi tạo chỉ chạy seed 42. Tín hiệu có thể phụ thuộc lấy mẫu và quá trình tối ưu hữu hạn.

Notebook 09 hỏi: **với cấu hình đã chọn cố định, kết quả trên seed mới có tiếp tục tốt hơn đối chứng không?** Không chọn thêm cặp penalty, khởi tạo hoặc ngân sách sau khi đã xem các seed xác nhận. Nếu cần tinh chỉnh tiếp, phải gọi đó là một đợt khám phá mới.

## 2. Protocol đã chọn trước khi chạy

| Instance | Ứng viên | Đối chứng | Khởi tạo chung (beta,gamma) | Seed | Số lượt |
|---|---|---|---|---|---:|
| p1_choice | (3,12) | (3,3) | [0.3,0.05] | 45,46,47,48,49 | 10 |
| p0_reference | (3,12) | (1,1) | [0.3,0.7] | 45,46,47,48,49 | 10 |

Giữ p=1, shots=1024, COBYLA maxiter=35, Aer CPU, 4 threads, aer_memory_mb=2048, min_available_gib=2.0 và max_seconds=300. Budget thời gian kiểm tra giữa các lần đánh giá, không phải ngắt cứng. Qubit vẫn là 20 cho choice, 23 cho reference.

Choice chọn gamma_nho vì pilot có ba mẫu tối ưu ở (3,12), so với một ở goc_cu. Reference chọn goc_cu vì có ba mẫu tối ưu ở cả ứng viên và đối chứng (1,1); chưa xem seed mới để quyết định này. Đây là xác nhận lựa chọn từ pilot, không phải chứng minh hai khởi tạo này tốt nhất trong mọi tình huống.

Hai cặp được so cùng seed/input/khởi tạo và ngân sách. Mỗi seed chạy lại cả optimizer lẫn lấy mẫu, vì vậy độ lệch chuẩn phản ánh biến động giữa các lượt tối ưu, không chỉ biến động của một lần đo mạch cố định. Seed 42 thuộc pilot lựa chọn, không gộp vào năm seed xác nhận.

## 3. Tệp và môi trường

Gói có bốn tệp:

| Tệp | Thao tác |
|---|---|
| notebooks/09_qaoa_penalty_confirmation.ipynb | Thêm notebook mới |
| docs/qaoa_penalty_confirmation.md | Thêm tài liệu này |
| tasks/plan.md | Cập nhật mốc notebook 08 đã review và protocol xác nhận |
| tasks/todo.md | Cập nhật checklist đã làm/đang chờ |

Notebook tái sử dụng src/qubo.py, src/qaoa_experiment.py, src/penalty_analysis.py và src/independent_campaign.py của gói notebook 08. Chọn Conda nt409-khiem / Python 3.12 trong VS Code; Restart Kernel trước mỗi instance. Không cần cài dependency mới.

## 4. Chạy choice trước

1. Mở notebook 09 trong repo; chạy Bước 1 để kiểm tra đường dẫn/môi trường.
2. Bước 2 giữ `STUDY_INSTANCE="p1_choice"` và `RESUME_MANIFEST=None`. Notebook tự chọn đúng hai cặp và khởi tạo. Bảng phải có 10 lượt, seed 45–49 ở mỗi cặp.
3. Bước 3 cần PASS với 20 vector đại số/tham chiếu cho hai mô hình. Mục tiêu gốc là 1 host, số qubit là 20.
4. Bước 4 đo thử tài nguyên. Bước 5 tạo/in manifest `confirmation_p1_choice_<campaign_id>.json` riêng; ghi lại đường dẫn.
5. Bước 6 chạy tuần tự/lưu ngay từng lượt. Giữ các lượt hoàn tất có 0 nghiệm. Lượt bị gián đoạn chưa được ghi thành báo cáo kết quả; các lượt đã hoàn tất vẫn được giữ.
6. Bước 7 xem từng seed. Bước 8 xem bảng trung bình/std và bảng ghép seed. Bước 9 xem mẫu đo thật.
7. Bước 10 cần PASS, 10/10 hoàn tất, 0 lượt còn lại. Mỗi cặp có năm lượt; bảng ghép có năm seed. PASS kiểm tra tính nhất quán, không tự kết luận ứng viên tốt hơn.
8. Lưu một bản có output, ví dụ `09_qaoa_penalty_confirmation_choice.ipynb`, để giữ kết quả trước khi chuyển instance.

## 5. Chạy reference sau

Restart Kernel. Dùng notebook 09, đặt ở Bước 2:

```python
STUDY_INSTANCE = "p0_reference"
```

Giữ `RESUME_MANIFEST=None`, rồi chạy Bước 1–10 theo thứ tự. Notebook tự chọn (1,1) làm đối chứng và [0.3,0.7] làm khởi tạo chung. Bước 3 có tối ưu gốc 2 host, 23 qubit. Kết thúc cần 10/10, 0 lượt còn lại; lưu bản có output với tên như `09_qaoa_penalty_confirmation_reference.ipynb`.

Nếu dùng Save As trong VS Code, nhớ lưu bản choice trước và để cả hai bản ở notebooks/ hoặc bên trong repo để cell tìm được ROOT. Khi đổi instance, chạy lại toàn bộ các cell từ kernel mới; đổi biến ở giữa đợt đang chạy có thể khiến trạng thái cũ không còn khớp, và Bước 6 có kiểm tra trường hợp này.

## 6. Đọc các bảng để quyết định

Chỉ số chính là **optimal_pct_mean**: trung bình tỷ lệ đo được placement tối ưu giữa năm seed. Đọc cùng các chỉ số sau:

| Cột | Ý nghĩa |
|---|---|
| completed_runs | Cần bằng 5 ở mỗi cặp trước khi kết luận |
| optimal_runs | Số trong năm lượt tìm được ít nhất một mẫu tối ưu |
| optimal_shots | Tổng số mẫu tối ưu trong 5120 shots của một cặp |
| optimal_pct_std | Độ lệch chuẩn giữa năm seed, không phải khoảng tin cậy |
| feasible_pct_mean/std | Tỷ lệ khả thi và biến động giữa seed |
| onehot_pct_mean | Tỷ lệ gán đúng tất cả task; chưa yêu cầu CPU/RAM hợp lệ |
| mean_solver_seconds | Thời gian QAOA trung bình; đọc cùng số lần đánh giá trong bảng/report từng lượt |
| max_recorded_peak_rss_mib | Đỉnh RSS được ghi trong các báo cáo, có thể gồm hoạt động kernel trước lượt |
| delta_optimal_pct_points | Chênh lệch ứng viên−đối chứng ở cùng seed, tính bằng điểm phần trăm |

Ví dụ nếu đối chứng có 1/1024 mẫu tối ưu và ứng viên có 3/1024, chênh lệch là 0,1953125 điểm phần trăm. Dương nghĩa là ứng viên có nhiều mẫu tối ưu hơn ở seed đó; bằng 0 nghĩa số mẫu bằng nhau.

Review theo thứ tự:

1. Trung bình tỷ lệ tối ưu có tăng không và tăng bao nhiêu mẫu?
2. Số lượt tìm được tối ưu có tăng hoặc duy trì không?
3. Kết quả tốt hơn có xuất hiện ở nhiều seed, hay chỉ do một lượt nổi bật? Bảng in số seed hơn/bằng/kém đối chứng để hỗ trợ đọc.
4. Tỷ lệ khả thi, chi phí và mode/đồng hạng có chấp nhận được không?

Không có một ngưỡng tự động trong notebook để tuyên bố chiến thắng. Với mẫu tối ưu hiếm và chỉ năm seed, kết luận cần giới hạn theo dữ liệu. Tỷ lệ cao hơn một chút hoặc std nhỏ không tự chứng minh ưu thế lượng tử. Năng lượng thô giữa hai cặp khác penalty không dùng để xếp hạng chúng.

Mẫu hợp lệ tốt nhất là lựa chọn bằng hậu xử lý. Proposal cũng có quy tắc lấy bitstring phổ biến nhất; giữ riêng mode/đồng hạng và tính khả thi của nó. Không sửa task/slack trước khi chấm. None/NaN trong mục tiêu/gap là thiếu nghiệm, không thay bằng 0. Lượt hoàn tất không có nghiệm vẫn nằm trong mẫu thống kê.

## 7. Nguồn dữ liệu và tiếp tục đợt chạy

Các báo cáo và manifest vẫn nằm trong `data/reference_results/phase4b_independent_runs/`. Tên manifest xác nhận:

```text
confirmation_p1_choice_<campaign_id>.json
confirmation_p0_reference_<campaign_id>.json
```

Để tiếp tục, Restart Kernel, giữ cùng instance/thiết kế/mã/runtime, đặt `RESUME_MANIFEST` đến đúng đường dẫn được Bước 5 in ra rồi chạy các cell theo thứ tự. Bước 5 xác minh báo cáo cũ; Bước 6 bỏ qua lượt đã có. Chạy lại Bước 6 trong cùng kernel cũng bỏ qua chúng. `RESUME_MANIFEST=None` ở Bước 5 tạo campaign mới. Không dùng manifest choice để tiếp tục reference hoặc manifest pilot để tiếp tục xác nhận.

Về định dạng, schema 3 và scope/hàm lưu hiện có của phase4b được giữ để tái sử dụng các kiểm tra. Phân biệt giai đoạn bằng `design.study` trong manifest và `study` trong mỗi report: `stage="fresh_seed_confirmation"`, protocol_version=1, selection_seed=42, selection_pilot_campaign_id và primary_metric. Hash thiết kế bao gồm study; Bước 10 kiểm tra metadata này. Đọc theo manifest/study, không dựa riêng vào tên thư mục để gộp mọi báo cáo.

## 8. Bàn giao và mốc tiếp theo

Gửi hai notebook có output, hai manifest confirmation và đủ 20 JSON báo cáo được tham chiếu. Giữ 24 báo cáo pilot và 90 báo cáo P chung cũ riêng. Thư mục có thể chứa nhiều campaign; chỉ chọn báo cáo thuộc hai manifest của đợt xác nhận này.

Sau review, chốt cặp penalty/khởi tạo cho khảo sát p=2. Nếu chưa có tín hiệu cải thiện rõ, kết thúc ma trận penalty có giới hạn và chuyển sang nghiên cứu độ sâu với đối chứng p=1. Trước khi tăng p cần đo tài nguyên. Khi tăng maxiter, giữ đối chứng p=1 cùng ngân sách để phân biệt tác động độ sâu với tác động số lần đánh giá.

Đợt này đo ổn định trên hai fixture đang có; chưa mở rộng input hoặc chứng minh khả năng khái quát. B/C tiếp tục so sánh FF/BFD/MILP và tổng hợp, không cần chờ QAOA vượt baseline mới làm báo cáo. Phạm vi này nối từ tinh chỉnh penalty sang thí nghiệm nhiều seed/độ sâu trong proposal.

## 9. Kiểm chứng phần mềm

Notebook được chạy đủ mười code cell trên cả choice/reference với 20 lượt Aer rút gọn trên Linux, shots=64/maxiter=4. Kiểm tra đúng cặp/khởi tạo/seed, bảng năm seed, metadata xác nhận, lưu báo cáo, tiếp tục không chạy lại, từ chối manifest của instance khác và từ chối đổi instance giữa đợt mà chưa dựng lại thiết kế.

Các phép kiểm tra này xác minh workflow, không thay các kết quả Windows shots=1024/maxiter=35 của bạn. Module toán học/runner dùng đúng bộ đã kiểm chứng ở notebook 08.

---

# Notebook 09 — Fresh-seed penalty confirmation

Updated 6 October 2026. This is branch A's next step after the reviewed 24-trial notebook-08 Windows pilot. The candidate (assignment,capacity)=(3,12) produced four optimal choice shots versus three for (3,3), but four optimal reference shots versus five for (1,1), pooled across two starts at seed 42. These small differences require confirmation before the depth study.

## Fixed protocol and installation

| Instance | Candidate | Control | Shared start (beta,gamma) | Fresh seeds | Trials |
|---|---|---|---|---|---:|
| p1_choice | (3,12) | (3,3) | [0.3,0.05] | 45–49 | 10 |
| p0_reference | (3,12) | (1,1) | [0.3,0.7] | 45–49 | 10 |

Keep depth 1, shots 1024, COBYLA maxiter 35, CPU Aer, four threads, 2048 MiB state-memory budget, at least 2 GiB available and a 300-second budget checked between evaluations. Registers remain 20/23 qubits. Starts and pairs were selected from the pilot before examining confirmation seeds; do not retune after viewing them and still call those seeds confirmation. Seed 42 remains selection data rather than an extra confirmation repetition.

Copy the four package files into matching paths: new notebook/docs and updated tasks/plan.md and tasks/todo.md. Existing notebook-08 modules are reused. Use the project Conda Python 3.12 kernel; no new dependency is required.

## Workflow and interpretation

Run choice first with `STUDY_INSTANCE="p1_choice"` and `RESUME_MANIFEST=None`. Execute steps 1–10 in order: environment, fixed design, 20-vector/two-model checks, resource probes, manifest creation, sequential runs, per-seed results, grouped and seed-paired comparisons, sample inspection and consistency verification. Full completion requires 10/10, zero remaining trials, five runs per pair and five paired seeds. Save an executed choice copy. Restart the kernel, select `p0_reference`, keep a fresh manifest and repeat; save an executed reference copy. Both are required for twenty-trial study completion.

Primary metric: optimal-placement probability averaged across seeds. Also inspect optimal/feasible successful runs, optimal shot counts out of 5120 per pair, across-seed standard deviation, paired differences and costs. Each seed reruns optimization as well as sampling. A positive paired difference means more optimal shots at that seed, not a statistically established winner. Standard deviation is not a confidence interval; five seeds do not prove quantum advantage or input generalization. There is no automatic victory threshold. Do not rank raw energies across penalty scales.

Retain completed zero-feasibility trials and missing objectives/gaps as null rather than zero. Score measured bits without repair. Disclose best-valid postselection separately from the proposal's frequency-based output rule, including ties. Lifetime peak RSS may include prior kernel activity; solver/decode/diagnostic times are separate.

## Provenance, resume and next step

Files remain under data/reference_results/phase4b_independent_runs, with manifests named confirmation_<instance>_<campaign_id>.json. Existing schema/helper scope is retained for compatibility; confirmation identity is recorded in design.study and report.study as stage=fresh_seed_confirmation, protocol version 1, selection seed/campaign and primary metric. Design hashing and final checks cover the study metadata. Use manifests/study fields to separate pilot from confirmation rather than pooling a whole folder.

Resume only with the same instance/design/input/source/runtime, restart the kernel and set RESUME_MANIFEST to the printed confirmation path; completed keys are checked/skipped. Re-running step 6 also skips them, while None at step 5 creates a new campaign. Cross-instance/pilot manifests cannot resume this study. Submit two executed notebooks, two manifests and twenty referenced reports.

After review, choose weights/starts for a resource-probed depth-2 study with depth-1 controls. If improvements remain unclear, close the bounded penalty grid and study depth rather than expanding it indefinitely. Match optimizer budgets when testing increased evaluation counts. B/C continue classical baselines and analysis on identical input JSONs.

Software verification executes all ten code cells for both instances using twenty reduced-budget Linux Aer runs (64 shots/maxiter 4), verifies the fixed designs, five-seed summaries, study identity and resume without reruns, and rejects wrong-instance resume and mid-run instance changes. This validates the workflow rather than the user's default-budget Windows quality.
