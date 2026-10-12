> **English version below.**

# Notebook 12: phân biệt nhiễu shots, khởi tạo và hội tụ số học

## Mục đích và vị trí trong kế hoạch

Notebook 11 đã hoàn tất và được review: 20 lượt Windows, seed 55–59, p=1/2, penalty (3,3), shots=1024, giới hạn 80 lần đánh giá. Mô hình và bit đo khớp nhau; tăng p giảm năng lượng trung bình nhưng chưa cải thiện ổn định xác suất placement tối ưu. Không tăng p ngay khi chưa làm rõ tác động của phép đo và optimizer.

Notebook 12 là một bước chẩn đoán nằm trong phần nghiên cứu QAOA của nhánh A. Giữ bài toán task placement, input, mục tiêu số host và các ràng buộc Phase 1/2. B vẫn làm FF/BFD/MILP; C vẫn tổng hợp và báo cáo. Đợt này không thay baseline MILP và không bổ sung tuyên bố lợi thế lượng tử.

Kết quả review trước đợt này cho thấy phép lấy mẫu Aer bằng cùng seed tại cùng mạch/góc có thể lặp lại cùng counts. Runner cũ lấy phân phối cuối từ sampler dùng để tối ưu. Do đó năng lượng cuối có thể lặp lại giá trị mà optimizer vừa chọn; chưa phải một phép đo độc lập. Có thiên lệch chọn điểm: trong nhiều giá trị có nhiễu, optimizer có xu hướng chọn điểm có phần nhiễu thuận lợi.

Trong 20 phép replay lý tưởng tại góc cuối của notebook 11, năng lượng từ batch cũ đều thấp hơn kỳ vọng chính xác. Hai đánh giá góc gần nhau cũng có chênh lệch năng lượng đo lớn hơn chênh lệch thật. Đây là bằng chứng cần sửa quy trình đánh giá, không chứng minh mọi khó khăn đều do shots. Một đối chứng exact có giới hạn trước đó giảm năng lượng nhưng vẫn cho xác suất tối ưu thấp; bỏ nhiễu không bảo đảm giải được bài toán.

## Những file được cập nhật

| File | Vai trò |
|---|---|
| `src/qaoa_experiment.py` | Lấy mẫu cuối bằng seed riêng; thêm thống kê và thông tin dừng; giữ các API cũ |
| `src/qaoa_optimizer.py` | Cùng một wrapper COBYLA cho sampled/exact; giữ kết quả dừng thật của SciPy |
| `src/convergence_diagnostics.py` | Tính năng lượng/kỳ vọng lý tưởng bằng vector số và Aer CPU |
| `src/convergence_campaign.py` | Ma trận đã định, report, manifest và xác minh resume notebook 12 |
| `notebooks/12_qaoa_convergence_diagnostics.ipynb` | Quy trình 10 bước, chạy riêng choice/reference |
| `tests/test_qaoa_sampling_protocol.py` | Kiểm tra seed cuối và counts độc lập |
| `tests/test_convergence_diagnostics.py` | Kiểm tra công thức/bit/scaling, exact và mẫu đo thật |
| `tests/test_convergence_campaign.py` | Kiểm tra ma trận, lưu/resume và từ chối dữ liệu sai |
| `requirements.txt` | Khai báo trực tiếp SciPy >=1.16,<2; SciPy đã có trong môi trường hiện tại |
| `tasks/plan.md`, `tasks/todo.md` | Ghi nhận notebook 11 đã review và bổ sung mốc chẩn đoán |

Mã mới áp dụng phép đo cuối độc lập cho **các lượt chạy mới** gọi runner, kể cả từ notebook cũ. Report đã hoàn tất không bị chỉnh sửa. Giữ chúng làm dữ liệu lịch sử với quy trình lấy mẫu cũ; không gộp trực tiếp với đợt mới như những lần lặp cùng protocol.

Nguồn mã được hash trong design. Sau cập nhật, manifest cũ sẽ không được resume bằng mã mới. Các JSON cũ vẫn đọc được để review lịch sử; muốn tái tạo đợt cũ phải dùng đúng snapshot mã/môi trường cũ. Notebook 12 dùng manifest và thư mục kết quả riêng.

## Lý thuyết liên hệ với thực hành

### 1. Ba mức năng lượng tại một bộ góc

Với bitstring đầy đủ z gồm x, y và slack, mô hình không đổi:

\[
E(z)=\sum_h y_h+3\sum_i(\sum_hx_{i,h}-1)^2
     +3\sum_{h,r}(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h)^2.
\]

QAOA tạo trạng thái phụ thuộc góc theta. Gọi p_theta(z) là xác suất đo z. Kỳ vọng lý tưởng là:

\[
\mu(\theta)=\sum_z p_\theta(z)E(z).
\]

Chạy N shots chỉ ước lượng kỳ vọng đó:

\[
\widehat\mu(\theta)=\frac1N\sum_{k=1}^{N}E(z_k).
\]

Notebook ghi ba số tại **cùng góc cuối**:

| Số | Lấy từ đâu | Dùng để làm gì |
|---|---|---|
| E_train | Giá trị mà optimizer đã dùng để chọn góc | Quan sát quá trình tối ưu; sampled có nhiễu và thiên lệch chọn điểm |
| E_eval | Batch cuối bằng seed riêng | Chấm năng lượng/placement từ phép đo độc lập |
| E_exact | Toàn bộ phân phối lý tưởng tại góc cuối | Chẩn đoán nhiễu và chất lượng của trạng thái |

Trong nhóm exact, E_train là kỳ vọng lý tưởng nên bằng E_exact trong sai số số học. E_eval vẫn có dao động vì vẫn lấy mẫu hữu hạn. Trong nhóm sampled, không bắt buộc E_eval lớn hơn E_train ở mọi lượt; phép đo độc lập có thể dao động theo cả hai hướng.

Hamiltonian thực thi là H_raw/kappa. Runner luôn quy về đơn vị gốc:

\[
E_{\rm QUBO}=\kappa\langle H_{\rm execution}\rangle+\mathrm{offset},
\qquad \gamma_{\rm raw}=\gamma_{\rm execution}/\kappa.
\]

Hai nhóm dùng cùng cách chuẩn hóa, cùng thứ tự [beta,gamma_execution] và cùng phương pháp COBYLA. Không thay hệ số từng ràng buộc hay đổi mục tiêu placement.

### 2. Shots và sai số của trung bình

Nếu độ lệch chuẩn năng lượng của phân phối lý tưởng là sigma, SE của trung bình N shots tại một điểm cố định là:

\[
\mathrm{SE}(\widehat\mu)=\sigma/\sqrt N.
\]

`evaluation_standard_error_exact` dùng sigma tính từ phân phối lý tưởng; `sampling_statistics.evaluation.mean_standard_error` dùng độ lệch chuẩn mẫu, với ước lượng phương sai không chệch. Đây là hai cách ước lượng cùng mức dao động tại một góc cố định. Với chỉ một shot, SE từ mẫu là null vì không đủ dữ liệu ước lượng phương sai.

SE không phải độ chính xác của bộ góc tối ưu, không chứng minh cực tiểu toàn cục và không dùng trực tiếp để tuyên bố cấu hình thắng sau khi đã chọn nó từ nhiều thử nghiệm. Đối chiếu hai điểm training cùng seed cũng không được giả định là hai phép đo độc lập.

`optimization_seed` cố định cho sampler training nhằm tái lập quy trình. `evaluation_seed=optimization_seed+100000` (modulo 2^32) dùng cho batch cuối. Hai seed phải khác nhau. Thay seed cuối không làm đổi quỹ đạo tối ưu. Hai nhóm exact/sampled ghép seed60 có thể dùng cùng seed cuối làm đối chứng ghép; batch đó vẫn tách khỏi sampler training.

### 3. Vì sao exact chưa bảo đảm placement tối ưu?

Optimizer giảm **năng lượng trung bình của cả phân phối**, không tối đa hóa trực tiếp xác suất placement tối ưu. Năng lượng giảm có thể do nhiều bitstring sai bớt vi phạm, trong khi xác suất đúng toàn bộ ràng buộc chưa tăng. Sai số phương trình tài nguyên còn tính cả slack sai; một placement x/y hợp lệ chưa nhất thiết có slack tối ưu.

Mixer X mặc định không giữ mỗi task được gán đúng một host trong suốt quá trình. Do đó tỷ lệ one-hot cần theo dõi. Phép kiểm tra exact chỉ bỏ nhiễu lấy mẫu trong objective; vẫn giữ ansatz hữu hạn p=1, điểm khởi tạo và optimizer cục bộ.

Phân biệt ba câu:

- Optimizer dừng: quá trình kết thúc theo một tiêu chí hoặc hết ngân sách.
- Hội tụ số học: thuật toán thỏa điều kiện dừng nội bộ; đây không phải chứng nhận cực tiểu toàn cục.
- Tìm placement tốt: trong mẫu đo có nghiệm hợp lệ/tối ưu với tỷ lệ và chi phí chấp nhận được.

`optimizer_stop` ghi status, success, message, nfev của SciPy. Không diễn giải mọi status theo một bảng mã cố định giữa các phiên bản; đọc message cùng version. `success=True` chưa chứng minh placement tốt. `success=False` do hết giới hạn đánh giá cũng chưa có nghĩa report bị hỏng. `maxiter` của COBYLA là giới hạn số đánh giá hàm. Hai nhóm dùng rhobeg=1 và tol=1e-4; bounds góc được bỏ qua giống wrapper COBYLA của runner trước.

## Ma trận cố định và phạm vi kết luận

| Thành phần | Cấu hình |
|---|---|
| Input | p1_choice, sau đó p0_reference; đọc đúng JSON hiện có |
| Penalty | lambda_assign=lambda_capacity=3 |
| Độ sâu, mixer | p=1, X mặc định |
| Thang thực thi | max_abs, chấm năng lượng QUBO gốc |
| Khởi tạo | common [0.3,1.0], alternative [0.8,1.2], cố định trước kết quả mới |
| Sampled | 3 seed60/61/62 cho mỗi khởi tạo; shots training=1024 |
| Exact | 1 tối ưu lý tưởng cho mỗi khởi tạo; dùng seed60 cho phép đo cuối/biên dịch |
| Ngân sách | Cùng maxiter80, rhobeg1, tol1e-4, max_seconds600 |
| Batch cuối | 1024 shots, seed riêng, cùng cả hai nhóm |
| Tài nguyên | Aer CPU double, 4 threads, 1 experiment/shot song song, max_memory_mb2048, RAM khả dụng tối thiểu2GiB |
| Số lượt | 8/instance, 16 cho cả hai input |

Seed ảnh hưởng objective sampled. Objective exact là xác định trong mô phỏng lý tưởng; lặp cùng khởi tạo bằng ba seed không tạo ba quỹ đạo tối ưu độc lập. Bảng nhóm vì thế ghi n_runs=3 cho sampled và n_runs=1 cho exact. So ghép hai cách chỉ dùng sampled seed60 và exact tương ứng. Không có đủ số liệu để tuyên bố ưu thế thống kê.

Hai khởi tạo chỉ là một kiểm tra nhỏ về độ nhạy, chưa khảo sát toàn bộ không gian góc. Chưa nghiên cứu p3, mixer giữ ràng buộc hoặc objective khác như CVaR trong đợt này. Các bước đó chỉ được cân nhắc sau khi review số liệu mới.

## Hướng dẫn chạy trong VS Code/Jupyter

1. Giải nén bản cập nhật vào đúng thư mục gốc `nt409-task-placement`, giữ đường dẫn con. Cập nhật 12 file trong bảng trên. Giữ bản notebook/report cũ bằng Git hoặc bản sao trước khi ghi đè runner.
2. Mở terminal Conda tại thư mục dự án, `conda activate nt409-khiem`. Kiểm tra `python --version` và `python -c "import scipy; print(scipy.__version__)"`. Môi trường hiện tại đã có SciPy; không cần tạo lại môi trường. Nếu SciPy dưới1.16, cài theo requirements rồi restart kernel.
3. Chạy `python -m unittest discover -s tests`. Mở notebook12, chọn đúng kernel, restart kernel và chạy Bước1. Nhìn `sys.executable` để kiểm tra interpreter thực tế.
4. Bước2 giữ `INSTANCE_ID="p1_choice"`, `RESUME_MANIFEST=None`; giữ nguyên cấu hình. Bước3 in 8 tổ hợp, số qubit20 và ground energy1.
5. Bước4 đo thử sampled/exact. Nếu ước lượng vượt giới hạn, dừng trước campaign và kiểm tra tiến trình/kernel đang dùng tài nguyên. Không coi 2048MiB là giới hạn toàn bộ RSS Python: đó là tùy chọn bộ nhớ mô phỏng quantum state. Vector năng lượng 23qubit là64MiB, statevector128MiB, nhưng Aer và các vector phụ cần thêm bộ nhớ.
6. Bước5 tạo manifest riêng. Bước6 chạy tuần tự và lưu mỗi lượt hoàn tất. Cho kernel hoạt động đến `8/8`, còn lại0. Mốc 600giây là guard giữa các lời gọi, không phải ngắt cưỡng bức ở đúng600giây; không lưu kết quả bị guard dừng.
7. Bước7–9 đọc bảng năng lượng, chất lượng, trạng thái dừng và audit. Đánh giá lý tưởng tại góc cuối/hai góc cuối là chẩn đoán thêm, có thời gian riêng, không tăng bộ đếm function evaluations của optimizer. Đường sampled trong đồ thị là năng lượng có nhiễu.
8. Bước10 phải PASS8/8. Lưu notebook có output thành `12_qaoa_convergence_diagnostics_choice.ipynb`.
9. Restart kernel, dùng notebook gốc hoặc Save As cho reference. Đổi `INSTANCE_ID="p0_reference"`, để `RESUME_MANIFEST=None`, chạy Bước1–10. Bước3 phải có23qubit và ground energy2. Lưu bản có output thành `12_qaoa_convergence_diagnostics_reference.ipynb`.
10. Để review, cung cấp 2 notebook có output, 2 manifest và16 report JSON được chúng liệt kê. Không cần gửi các report Linux dùng kiểm thử phần mềm; chúng không nằm trong bản cập nhật.

Nếu ngắt giữa đợt, restart kernel, dùng đúng input/cấu hình/mã/môi trường rồi điền `RESUME_MANIFEST` bằng đường dẫn đã in. Chạy Bước1–6; những lượt hoàn tất được xác minh rồi bỏ qua. Không để None khi muốn resume vì None tạo một đợt mới. Khi đã sửa cấu hình, mã nguồn hoặc môi trường, tạo campaign mới; không ép tiếp tục manifest cũ.

Lượt có0 nghiệm vẫn hoàn tất nếu optimizer và batch cuối đã chạy xong. Không sửa bits, chọn lại seed vì kết quả kém hoặc xóa những lượt đó để làm đẹp thống kê. Kết quả nghiệm tham chiếu đã biết dùng kiểm chứng, không được đưa vào ansatz/góc/bit đo cuối.

## Cách quyết định bước kế tiếp từ bảng

| Quan sát | Điều có thể suy ra trong phạm vi này | Bước tiếp theo có điều kiện |
|---|---|---|
| E_train sampled thấp hơn E_exact, E_eval gần E_exact hơn | Có ảnh hưởng nhiễu và lựa chọn điểm trong training | Ước lượng tăng shots/đổi optimizer phù hợp nhiễu; đối chứng ngân sách rõ |
| Exact giảm E tốt hơn nhưng P_opt không tốt hơn | Objective năng lượng và tỷ lệ placement đúng chưa đi cùng nhau | Cân nhắc objective hoặc mixer; không chỉ tăng số đánh giá |
| Hai khởi tạo exact dừng ở E/P_opt khác nhau | Nhạy với khởi tạo/cực tiểu cục bộ | Một đợt nhiều khởi tạo có giới hạn, rồi xác nhận riêng |
| Exact chạm max evaluations và còn giảm | Chưa đủ ngân sách cho cấu hình đó | Chạy đối chứng tăng ngân sách, giữ các yếu tố khác |
| Exact dừng số học thành công nhưng P_opt vẫn thấp | Dừng số học không chứng nhận nghiệm tối ưu | Review objective/ansatz và báo cáo giới hạn; chưa kết luận p1 bất khả thi |
| Có P_opt lý tưởng >0 nhưng batch cuối không gặp nghiệm | Có thể là dao động lấy mẫu hữu hạn | Xem N×P_opt kỳ vọng; không kết luận chương trình sai từ một batch0 |

Không đặt điều kiện nghiệm thu là “tất cả kết quả phải tăng”. Nghiệm thu là nguồn dữ liệu đúng, đủ ma trận, phép đo cuối độc lập, đơn vị nhất quán, lý do dừng rõ, chất lượng và chi phí được tách biệt.

## Xác minh phần mềm và nguồn kỹ thuật

59 kiểm tra tự động đã đạt trên Python3.12.14/Linux, NumPy2.3.5, SciPy1.17.0, Qiskit2.5.2, Aer0.17.2, Optimization0.7.0. Các kiểm tra độc lập đối chiếu mọi basis state của mô hình4qubit với công thức tài nguyên, dùng Statevector kiểm kỳ vọng p1/p2, kiểm counts bằng sampler seed riêng và thử sửa dữ liệu để bảo đảm resume từ chối. Các lượt notebook rút gọn trên input20/23qubit chỉ xác minh quy trình; không thay kết quả Windows mặc định cần thu thập. Log/test giảm ngân sách được giữ ngoài gói cập nhật, không nhập vào dữ liệu nghiên cứu của A.

Nguồn chính thức:

- [Qiskit Optimization QAOA0.7](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.minimum_eigensolvers.QAOA.html)
- [Qiskit Aer SamplerV2](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html)
- [SciPy minimize, method COBYLA](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html)
- [Bài báo QAOA gốc](https://arxiv.org/abs/1411.4028)

---

# Notebook 12: distinguish shot noise, initialization and numerical stopping

## Purpose and scope

Notebook11's twenty Windows trials have been reviewed. Lower mean QUBO energy at p2 did not establish improved optimal-placement sampling. Same-seed Aer repetitions can reproduce the same counts, and the old runner scored its final distribution with the training sampler. The new protocol trains as before but scores a separate, reproducible final batch. Historical reports are preserved and should not be pooled as same-protocol repetitions.

This is a bounded branch-A diagnostic within the existing task-placement project. Inputs, assignment rules, resource constraints and host-count objective remain unchanged. B continues FF/BFD/MILP and C continues analysis/reporting. An ideal-expectation control is not a quantum advantage or hardware result.

The update contains twelve project files: four runner/diagnostic/campaign modules, Notebook12, three focused test modules, this document, requirements.txt, and the two task documents. Three modules are new; qaoa_experiment.py is updated. Existing runner APIs remain available. Direct SciPy use is declared as >=1.16,<2; it is already installed in the current environment.

## Mathematical interpretation

For the unchanged full-bit QUBO, E(z) is active-host count plus assignment and capacity-equation squared penalties, both weighted3. At fixed angles theta, the ideal mean is sum_z p_theta(z)E(z). A finite N-shot batch estimates it by the arithmetic mean of measured energies. The runner records:

- E_train: objective estimate used to select the optimizer's final angles; subject to noise/selection bias for sampled optimization.
- E_eval: mean of an independently seeded final batch, used for measured placement scoring.
- E_exact: ideal expectation at those same angles, used only for diagnostics.

Exact optimization makes E_train agree with E_exact within floating point tolerance. E_eval still fluctuates. The execution Hamiltonian is H_raw/kappa, so reported raw energy equals kappa times its expectation plus offset, and gamma_raw=gamma_execution/kappa. No individual constraint is rescaled.

The fixed-point standard error is sigma/sqrt(N). The oracle uses the ideal energy variance; final-sample statistics use unbiased sample variance. This is not uncertainty in the learned angles or a global-convergence certificate. Training evaluations share a seed, so their difference is not treated as an independent-samples hypothesis test. Evaluation seed defaults to training seed+100000 modulo2^32 and must differ from it. Changing the final seed does not change training. Matched exact/sampled controls may share a final seed while remaining separate from training.

Numerical stopping is distinct from placement success. optimizer_stop records SciPy status, success, message and nfev. Read the message with the recorded version rather than assuming universal status numbers. COBYLA maxiter caps function evaluations; rhobeg1 and tol1e-4 are shared, with ignored angle bounds matching the earlier wrapper. success=True does not certify global optimality. A max-evaluation stop can still produce a completed report.

Mean-energy minimization does not directly maximize optimal-placement probability. Wrong samples can reduce their violations without satisfying all constraints; resource-equation errors include incorrect slack. The default X mixer does not preserve one-hot assignment. Exact expectations remove objective sampling noise but retain the finite-depth ansatz and local optimizer.

## Predeclared matrix

Use existing p1_choice then p0_reference, penalties(3,3), p1, max_abs execution scaling, starts [0.3,1.0] and [0.8,1.2], maxiter80, max_seconds600, training/evaluation shots1024, rhobeg1, tol1e-4. Aer uses CPU double precision, four threads, no parallel statevector experiments/shots, max_memory_mb2048 and a2GiB available-memory guard.

Each input has six sampled trials (two starts × seeds60/61/62) and two exact optimizations (one per start). Exact objectives are deterministic; repeating an identical optimization under three seeds would not create three independent optimization trajectories. Group tables show sampled n=3 and exact n=1; paired method comparisons use sampled seed60 and the corresponding exact control. Sixteen reports across both inputs are required. This is exploratory, not a significance/generalization claim. Depth3, constraint-preserving mixers and alternative objectives remain outside this diagnostic.

## Running and resuming

1. Extract the twelve updated files into the project root with their relative paths. Preserve earlier notebooks/reports using Git or a copy. Activate Conda nt409-khiem; check Python3.12 and SciPy>=1.16. Do not recreate the environment unnecessarily.
2. Run `python -m unittest discover -s tests`. Open Notebook12 in VS Code, select the intended kernel and restart it after updating source files. Step1 prints the actual interpreter/runtime.
3. Keep p1_choice and RESUME_MANIFEST=None. Step3 must show eight trials,20qubits and minimum energy1. Step4 probes sampled/exact cost before creating a campaign; projected costs are approximate and exclude some postprocessing/audit.
4. Step5 creates a separate manifest; Step6 saves each completed trial and its index. A completed zero-solution trial is retained. An interrupted/time-guarded report is not saved. The time guard is checked between costly calls, not a hard wall-clock interrupt.
5. Steps7–9 compare objective estimates, independent means, ideal statistics, measured feasibility/optimality, stopping messages and runtime. Additional ideal audits of final/tail angles have separate costs and are excluded from optimizer evaluation counts.
6. Step10 must verify8/8 and no remaining keys. Save the executed choice notebook. Restart the kernel; change to p0_reference, leave RESUME_MANIFEST=None and repeat. Reference must show23qubits/minimum energy2. Save its executed notebook separately.
7. Provide two executed notebooks, two convergence manifests and the sixteen reports referenced by them for review.

To resume, use the printed Notebook12 manifest path with exactly matching input/configuration/source/runtime. Verification skips completed runs. None creates a new campaign. Configuration or source changes require a new campaign. The update changes source hashes, so old manifests cannot resume under new code; historical JSON remains readable, and exact old-protocol reruns require the old snapshot. New runs through older notebooks also use independent final sampling.

The oracle uses numeric energy/probability vectors rather than a dense2^N×2^N matrix or all-bitstring label dictionary, capped at23qubits. A23qubit energy vector is64MiB and statevector128MiB, with additional working storage. Aer max_memory_mb is not a whole-Python-RSS cap. Restart between inputs and avoid concurrent busy kernels. Do not repair bitstrings, inject reference solutions, discard zero-solution trials or cherry-pick seeds.

## Decision rules and validation

A sampled training-to-ideal gap supports a shot-noise/selection effect; better exact energy without better optimal-placement probability motivates objective/mixer review. Different exact-start outcomes indicate initialization sensitivity. A max-evaluation stop with continued energy improvement can motivate a matched larger-budget test. Numerical success with low P_opt motivates reporting ansatz/objective limits rather than blindly increasing maxiter. A nonzero ideal P_opt and zero measured optimal shots can reflect finite sampling; inspect N×P_opt before diagnosing a coding fault. This small matrix cannot isolate a universal cause or prove p1 impossible.

Acceptance requires correct source evidence, a complete matrix, independent final measurement, consistent units and disclosed quality/costs; improvement in every arm is not required.

Fifty-nine automated tests pass on Python3.12.14/Linux, NumPy2.3.5, SciPy1.17.0, Qiskit2.5.2, Aer0.17.2 and Optimization0.7.0. Independent tests compare basis energies with resource equations, ideal p1/p2 states with Statevector, held-out counts with a separately seeded sampler, and reject altered campaign evidence. Reduced-budget20/23qubit notebook executions validate the workflow; they do not replace A's default Windows experiments. Software-validation reports are excluded from the update package and research results.

Official references: [QAOA](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.minimum_eigensolvers.QAOA.html), [Aer SamplerV2](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html), [SciPy COBYLA](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html), [original QAOA paper](https://arxiv.org/abs/1411.4028).
