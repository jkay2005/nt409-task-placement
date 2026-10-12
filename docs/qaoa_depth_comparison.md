> **English version below.**

# Notebook 11 — So sánh QAOA p=1 và p=2

Protocol nhánh A, cố định ngày 07/10/2026 trước khi A chạy các lượt Windows mặc định. B tiếp tục FF/BFD/MILP; C tiếp tục tổng hợp kết quả trên cùng JSON đầu vào.

## 1. Mốc đã review và câu hỏi của đợt này

Notebook 10 hoàn tất/review 30 lượt Windows, seed 50–54, shots=1024/maxiter=35 và penalty (3,3). Hai notebook, hai manifest, 30 report và 30.720 mẫu đo đều khớp công thức/QUBO/Ising/thang/gamma/giải mã/bảng.

| Instance | raw_original: tối ưu /5120, lượt thành công | normalized_matched | normalized_common |
|---|---|---|---|
| p1_choice | 5 mẫu, 3/5 lượt | 6 mẫu, 3/5 | 10 mẫu, 5/5 |
| p0_reference | 4 mẫu, 3/5 lượt | 4 mẫu, 4/5 | 3 mẫu, 2/5 |

normalized_common giảm năng lượng trung bình khoảng 42,2% trên choice và 49,7% trên reference, nhưng chưa cải thiện tỷ lệ placement tối ưu đồng thời. Reference/seed52 có một mẫu full-QUBO ground state E=2. Một mẫu cực tiểu không đồng nghĩa khả năng tìm nghiệm ổn định. Chưa có bằng chứng sai quy đổi/giải mã trong kết quả đã kiểm tra.

Đợt tiếp theo hỏi: **thêm một lớp QAOA có tăng khả năng tìm placement tối ưu khi giữ penalty, thang Hamiltonian và ngân sách đánh giá hàm hay không?** Chọn thang chuẩn hóa/khởi tạo chung để có một protocol nhất quán, không tuyên bố đây là khởi tạo tốt nhất cho reference. Đây là phần khảo sát p=1/2/3 trong proposal; bước này chỉ triển khai p=1/2.

## 2. Lý thuyết gắn với thực hành

Mô hình QUBO giữ nguyên:

\[
E(z)=\sum_h y_h+3\sum_i(\sum_hx_{i,h}-1)^2
+3\sum_{h,r}(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h)^2.
\]

Mỗi task vẫn ở đúng một host. x/y/slack, thứ tự bit, dữ liệu và tiêu chí hợp lệ không đổi. Với hai host, dữ liệu nguyên và bài toán khả thi, penalty 3 đủ để mọi cực tiểu QUBO hợp lệ; QAOA vẫn phải tìm được vùng đó.

Thực thi H_execution=H_raw/kappa, kappa là hệ số Pauli khác identity có trị tuyệt đối lớn nhất. Choice: kappa=74.5; reference: 257.5. E_QUBO=kappa*expectation(H_execution)+offset_raw. Chấm tất cả mẫu và lịch sử theo năng lượng QUBO gốc. Beta không đổi; gamma_raw=gamma_execution/kappa.

Một lớp QAOA gồm:

\[
U_C(\gamma)=e^{-i\gamma H_{\mathrm{execution}}},\qquad
U_M(\beta)=e^{-i\beta\sum_j X_j}.
\]

p=1 có hai góc; p=2 có bốn góc. Qiskit sắp tất cả beta trước, sau đó tất cả gamma:

| Độ sâu | Thứ tự | Góc khởi tạo theo H_execution |
|---|---|---|
| p=1 | [beta0,gamma0] | [0.3,1.0] |
| p=2 | [beta0,beta1,gamma0,gamma1] | [0.3,0.0,1.0,0.0] |

Khi beta1=gamma1=0, lớp mới là identity nên hai mạch bắt đầu cùng trạng thái. Các góc thêm vẫn được tối ưu; chúng không bị khóa tại 0. Đây là tái sử dụng góc **khởi tạo cố định** của p=1, không dùng nghiệm p=1 đã học từ cùng seed. Mỗi lượt p=2 không nhận thêm một đợt tối ưu p=1 để tìm điểm xuất phát.

Họ trạng thái p=2 chứa p=1, nên mức năng lượng kỳ vọng nhỏ nhất có thể biểu diễn không cao hơn nếu tìm được tối ưu toàn cục. COBYLA trong ngân sách hữu hạn có thể không tìm được mức đó. Hơn nữa, giảm kỳ vọng năng lượng không bảo đảm tăng xác suất placement tối ưu. Khởi tạo lớp 0 có thể tạo hướng tìm góc khó cho optimizer; nếu protocol này không cải thiện, chưa thể kết luận mọi khởi tạo p=2 kém p=1.

Thêm lớp không thêm biến QUBO. Số qubit vẫn 20/23, còn số tham số và số cổng tăng. Chuẩn hóa toàn H giữ cực tiểu, không chia riêng phương trình tài nguyên.

Nguồn API: [Qiskit Optimization QAOA](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.minimum_eigensolvers.QAOA.html), [COBYLA](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.optimizers.COBYLA.html), [SamplingVQE](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.minimum_eigensolvers.SamplingVQE.html). Phép nhúng lớp 0 là suy luận từ dạng mạch và được kiểm tra trạng thái thực tế, không phải bảo đảm cải thiện do thư viện cung cấp.

## 3. Protocol cố định

| Thành phần | Giá trị |
|---|---|
| Dữ liệu | p1_choice, rồi p0_reference |
| Penalty assignment/capacity | (3,3) trên cả hai |
| Hamiltonian | max_abs, H_raw/kappa |
| Độ sâu | p1_control và p2_embedded |
| Seed mới | 55,56,57,58,59 |
| Shots | 1024 mỗi lần đánh giá và lần lấy mẫu cuối |
| COBYLA | maxiter=80, rhobeg=1 |
| Tài nguyên | Aer CPU, 4 threads, state-memory 2048 MiB, tối thiểu 2 GiB RAM khả dụng |
| Thời gian | max_seconds=300, kiểm tra giữa các lần đánh giá |
| Số lượt | 2 độ sâu × 5 seed = 10 mỗi instance; 20 tổng cộng |

maxiter là giới hạn số lần đánh giá hàm, không phải số qubit hoặc shots. Tăng từ 35 lên 80 cho **cả đối chứng p=1** để p=2 không được hưởng ngân sách riêng. Số đánh giá thực tế có thể khác do dừng sớm; thời gian p=2 cũng có thể dài hơn. Phép so này giữ cùng giới hạn đánh giá/shots, không giữ cùng chi phí cổng hoặc thời gian tuyệt đối.

Chạy ghép seed theo thứ tự p1/55,p2/55,p1/56,p2/56… Không thay khởi tạo sau khi xem kết quả và vẫn gọi là cùng protocol. Seed 42,45–49,50–54 của các đợt trước giữ riêng. Kết quả p1/maxiter35 cũ là mốc lịch sử; đối chứng độ sâu là p1/maxiter80 mới.

Chỉ số chính là optimal_placement_probability trung bình qua seed. Đọc cùng số lượt có nghiệm tối ưu, số mẫu tối ưu trong 5120 shots mỗi độ sâu, tỷ lệ hợp lệ, ground state, biến động và thời gian/RAM. Năm seed trên hai fixture là thăm dò, chưa chứng minh khả năng khái quát hoặc ưu thế lượng tử.

## 4. Chép bảy tệp vào repo

| Tệp | Thao tác và vai trò |
|---|---|
| src/qaoa_experiment.py | Thay bản cũ: bổ sung hash depth module và lưu báo cáo vào thư mục đúng scope |
| src/depth_campaign.py | Thêm: khởi tạo p2, ma trận ghép seed, manifest và xác minh |
| tests/test_depth_campaign.py | Thêm: kiểm chứng trạng thái, bốn góc, ngân sách và resume |
| notebooks/11_qaoa_depth_comparison.ipynb | Thêm: notebook mới với 10 code cell |
| docs/qaoa_depth_comparison.md | Thêm: hướng dẫn song ngữ này |
| tasks/plan.md | Thay bản cũ: ghi review 10 và kế hoạch độ sâu |
| tasks/todo.md | Thay bản cũ: mốc hoàn tất và phần đang chờ |

Gói dùng các module/fixture đã có sau notebook 10. Không thay src/qubo.py hoặc src/ising.py; không cài dependency mới. Chọn kernel Conda nt409-khiem/Python 3.12 trong VS Code rồi Restart Kernel.

## 5. Chạy từng bước và hiểu kết quả

1. **Bước 1 — Môi trường:** xem ROOT, Python/Qiskit/Aer và source hash. ROOT phải là repo của bạn. Restart giúp nạp đúng module vừa chép.
2. **Bước 2 — Thiết kế:** giữ STUDY_INSTANCE="p1_choice", RESUME_MANIFEST=None. Bảng cần 10 lượt, hai độ sâu, seed55–59 và cùng maxiter80/shots1024. Điểm p2 phải là [0.3,0,1,0].
3. **Bước 3 — Kiểm chứng:** cần PASS cho 10 vector năng lượng và ba trạng thái nhúng trên bài 4 qubit. Bảng có p1/p2 cùng số qubit, số góc 2/4. Phần kiểm chứng nhỏ không phải fixture benchmark mới.
4. **Bước 4 — Đo tài nguyên:** có ba hàng: p1_control, p2_embedded và p2_active_layer_probe. Lần đo thêm dùng góc [0.3,0.2,1,0.5] để không chỉ đo lớp 0. Góc này không đổi khởi tạo tối ưu. Ước lượng dùng thời gian p2 lớn hơn, cộng setup và dự phòng 1.5. Nếu guard chạm 300 giây, gửi bảng này để chốt điều chỉnh trước đợt chạy; phép đo không bảo đảm thời gian chính xác.
5. **Bước 5 — Manifest:** ghi lại đường dẫn depth được in. Nó khóa thiết kế, input, code/runtime, scale, góc và seed. None tạo đợt mới; đúng đường dẫn manifest dùng để resume.
6. **Bước 6 — Chạy:** mỗi lượt được lưu ngay khi hoàn tất; đợt chạy theo từng cặp seed. Giữ cả lượt hoàn tất có 0 nghiệm. Lượt bị ngắt/chạm thời gian không được lưu thành JSON kết quả. Có thể tiếp tục các lượt còn lại bằng manifest.
7. **Bước 7 — Từng lượt:** ba cột probability là phần trăm. found_optimal là có ít nhất một mẫu tối ưu trong lượt, khác với tỷ lệ mẫu tối ưu. Mục tiêu/gap thiếu nghĩa chưa có nghiệm hợp lệ, không đổi thành 0.
8. **Bước 8 — Tổng hợp:** bảng chất lượng và chi phí có hai nhóm, mỗi nhóm năm lượt khi đủ. Bảng ghép có năm seed. Delta=p2−p1: dương ở xác suất là tăng, âm ở năng lượng là giảm. Std là độ lệch chuẩn, không phải khoảng tin cậy. Đọc tỷ lệ tối ưu cùng số mẫu/lượt thành công.
9. **Bước 9 — Report thật:** mặc định xem cặp seed55, góc theo tên, góc theo H gốc, mẫu đứng đầu và nghiệm hợp lệ tốt nhất. Không sửa slack/task trước khi chấm. Công bố riêng mode/đồng hạng và best-valid hậu xử lý.
10. **Bước 10 — Nghiệm thu:** cần 10/10, không còn lượt, hai nhóm năm lượt và năm cặp. PASS chỉ xác minh tính nhất quán; nếu còn lượt, notebook báo chưa đủ.

Lưu bản có output thành notebooks/11_qaoa_depth_comparison_choice.ipynb. Sau đó Restart Kernel, đặt STUDY_INSTANCE="p0_reference", RESUME_MANIFEST=None và chạy lại từ Bước 1. Lưu thành notebooks/11_qaoa_depth_comparison_reference.ipynb.

## 6. Tệp sinh ra và tiếp tục sau gián đoạn

Thư mục: data/reference_results/phase4d_depth_runs/.

- Manifest: depth_<instance>_<campaign_id>.json.
- Report: <instance>_<arm>_p<depth>_seed<seed>_<timestamp>.json.
- Mỗi report lưu bits thật, lịch sử/góc theo tên, hai thang gamma, năng lượng QUBO gốc, metrics, chẩn đoán, nguồn/runtime và chi phí.

Resume: Restart Kernel, giữ đúng instance và bộ file/config đã chạy; đặt RESUME_MANIFEST="data/reference_results/phase4d_depth_runs/depth_...json" theo đường dẫn Bước 5, rồi chạy từ Bước 1. Báo cáo đã hoàn tất được kiểm tra/bỏ qua, không chạy lại. Không dùng manifest khác instance hoặc notebook 10.

Runner/source hash thay đổi nên resume 08/09/10 bằng bộ mã mới bị từ chối theo kiểm tra nguồn. Các báo cáo hoàn tất trước đó vẫn giữ nguyên và đọc được; không sửa hash trong manifest để ép resume.

Gửi hai notebook đã chạy, hai manifest depth và **20 JSON nguồn được manifest tham chiếu**. Khi nén theo instance, mỗi ZIP có 10 report; manifest và notebook gửi riêng để tránh thiếu/nhầm tệp.

## 7. Kết luận sau đợt này và giới hạn

Review riêng choice/reference. Nếu p2 tăng tỷ lệ tối ưu nhưng chỉ nhờ một seed, coi là ứng viên cần kiểm tra thêm. Nếu năng lượng giảm mà nghiệm tối ưu không tăng, ghi đúng hai kết quả. Nếu không có cải thiện, kết luận giới hạn của depth/khởi tạo/ngân sách này; sau review mới chọn p3 hoặc một đợt optimizer/khởi tạo khác có đối chứng.

Proposal dùng chuỗi xuất hiện nhiều nhất làm đầu ra. Best-valid trong notebook là hậu xử lý và phải công bố riêng, cùng chi phí của nó. Routines exact nhỏ của A kiểm chứng mô hình, không thay baseline MILP của B. B/C tiếp tục công việc đã bàn giao; phần so sánh cổ điển và quy mô 8task/4host chưa được đánh dấu hoàn tất.

## 8. Kiểm chứng phần mềm trước bàn giao

42 kiểm tra tự động đạt, gồm 34 kiểm tra hồi quy và 8 kiểm tra mới cho trạng thái lớp 0, thứ tự bốn góc, năng lượng gốc, ngân sách, lưu/resume, cấu hình thay đổi và dữ liệu bị sửa. Cả 10 code cell được thực thi trên hai fixture thật với **20 lượt Aer Linux rút gọn shots=64/maxiter=8**, kèm probe lớp p2 hoạt động, bảng ghép seed và resume không chạy lại. Từ chối resume khác input và đổi input/ngân sách giữa đợt. Những lượt kiểm chứng này xác minh phần mềm, không thay kết quả chất lượng Windows shots1024/maxiter80 của A.

---

# Notebook 11 — QAOA depth-one versus depth-two comparison

Protocol fixed on 7 October 2026 before A's default-budget Windows execution. A owns QUBO/Ising/QAOA, B owns FF/BFD/MILP, and C owns comparative analysis.

## Reviewed checkpoint and research question

Notebook 10's thirty Windows trials and all 30,720 shots are consistent with source reports, formula/QUBO/Ising, scaling, gamma conversion and both notebook tables. At shared (3,3), raw/matched/common arms yielded 5/6/10 optimal choice shots and 3/3/5 successful trials, versus 4/4/3 reference shots and 3/4/2 successes. Common initialization reduced mean energy by about 42.2%/49.7%, without improving optimal-placement rates jointly. Reference/seed52 yielded one full-QUBO ground-state sample of energy 2. One rare sample is not stable success.

This exploratory study asks whether another QAOA layer improves optimal-placement sampling at fixed penalties, execution scale and function-evaluation budget. Shared normalized initialization is a consistent test protocol, not a claimed reference winner. This implements depth one/two; depth three and classical comparison remain subsequent work.

## Theory and fixed protocol

The original objective, assignment/resource penalties (3,3), x/y/slack ordering, input and decoding are unchanged. Execute H_raw/kappa, with kappa=74.5/257.5 on choice/reference. Restore raw energy as kappa*expectation(H_execution)+offset_raw and raw gamma as gamma_execution/kappa. Positive global scaling preserves minima; do not normalize resource equations individually.

Each layer applies exp(-i gamma H_execution) then exp(-i beta sum X). Qiskit's parameter order is all betas followed by all gammas. Depth one starts [0.3,1.0]; depth two starts [0.3,0,1.0,0]. The appended zero layer is identity, giving identical initial physical states. Its angles remain free during optimization. This reuses the fixed starting angles, not a learned p1 optimum or an extra p1 tuning stage. The p2 state family contains p1, so its globally attainable minimum expected energy cannot be worse. Finite-budget COBYLA, optimal-placement probability and escaping the zero-layer start have no improvement guarantee. Qubits stay 20/23; parameters rise from two to four.

Both arms use five fresh seeds 55–59, 1024 shots per evaluation/final sampling, COBYLA maxiter80/rhobeg1, CPU Aer/four threads, 2048 MiB quantum-state memory, 2 GiB minimum available RAM and 300 seconds checked between evaluations. Ten runs per fixture, twenty total; run p1/p2 sequentially for each seed. maxiter is a function-evaluation cap. Both arms receive the increased budget; actual counts and wall-clock costs may differ. Notebook 10's different seeds/maxiter35 are historical data rather than matched depth controls. Keep earlier seed campaigns separate.

Primary metric is mean optimal-placement probability, read alongside success counts, optimal shots out of 5120 per arm, feasibility, full-QUBO ground states, variability and resources. Five seeds/two fixtures are exploratory evidence; standard deviation is not a confidence interval or evidence of input generalization/quantum advantage. Expected energy and optimal-placement probability can move differently.

## Install seven files and run

Replace src/qaoa_experiment.py, tasks/plan.md and tasks/todo.md. Add src/depth_campaign.py, tests/test_depth_campaign.py, notebooks/11_qaoa_depth_comparison.ipynb and docs/qaoa_depth_comparison.md. Reuse existing notebook-10 modules/fixtures and dependencies; QUBO/Ising files are unchanged. Select the project Conda Python3.12 kernel and restart.

Run steps 1–10 on choice: environment/source hashes; the fixed ten-trial design; input energy and tiny four-qubit identity-layer/parameter-order checks; resource probes; manifest; sequential trials; individual results; quality/cost/paired-seed tables; source reports; consistency/completeness. Resource probes include both protocol starts and an active p2 point [0.3,0.2,1,0.5], used only for diagnostics rather than optimization. Use the larger p2 sampling time plus setup/1.5 margin as an estimate, not a runtime guarantee. If it reaches the budget guard, review that table before starting the campaign.

Expected completion is 10/10 with zero remaining, two groups of five and five paired rows. Save 11_qaoa_depth_comparison_choice.ipynb, restart, select p0_reference with RESUME_MANIFEST=None, repeat from step1 and save the reference copy. Reports live under data/reference_results/phase4d_depth_runs, with depth_<instance>_<campaign_id>.json manifests and <instance>_<arm>_p<depth>_seed<seed>_<timestamp>.json reports. Submit both executed notebooks, two depth manifests and twenty referenced reports; each instance ZIP contains ten reports.

Resume only the identical design/input/code/runtime using the printed depth manifest. Completed reports are verified/skipped without rerunning; keep completed zero-solution trials, and do not save unfinished runs as results. Changed runner/source hashes reject older 08/09/10 resume; completed historical data remain readable. Do not edit provenance hashes to bypass checks.

## Interpret and verify

Percent columns are percentages; missing objective/gap means no feasible measured solution. best_observed_valid is postselection, separate from most-frequent output and tied modes. Score measured bits without repairing task/slack assignments. The paired contrast is p2 minus p1; positive optimal-probability differences and negative energy differences have distinct meanings. Assess each input and costs independently before choosing depth three or a separately documented optimizer/initialization study. A's exact enumeration checks are not B's MILP baseline; larger-instance experiments and classical comparison are still open.

Authoritative QAOA/COBYLA/SamplingVQE API references appear in the Vietnamese section. Zero-layer embedding is a mathematical circuit construction checked at runtime, not a library performance promise. Software verification passes 42 automated tests (34 regressions/eight new tests) and every code cell on both real fixtures with twenty reduced-budget Linux Aer trials, shots64/maxiter8. Active-layer probes, paired tables, raw-energy scoring, unchanged qubits, resume without reruns and invalid input/budget resume guards are verified. These checks validate software, not A's pending default-budget Windows quality.
