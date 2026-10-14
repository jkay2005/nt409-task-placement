> **English version below.**

# Khảo sát hệ số phạt chung sau mốc A1

## 1. Vị trí và phạm vi

A1 đã có đủ 18 lượt Windows: sáu lượt mỗi bộ p1_tight, p1_choice và p0_reference. Đây là số liệu thăm dò, chưa phải benchmark cuối. Văn bản ghi nhận mốc nằm ở `a1_milestone_vi.md` và bản PDF chỉ tiếng Việt.

Theo proposal, tiếp theo cần khảo sát penalty, rồi độ sâu p=1,2,3. Notebook 07 bắt đầu bằng **một P chung**, tương ứng A=B=P cho hai nhóm phạt. Nó dùng nguyên `build_qubo(instance, penalty=P)` và runner Aer đã kiểm chứng. Hai hệ số gán/dung lượng độc lập còn là bước mở rộng riêng; chưa coi khảo sát chung là đã hoàn tất toàn bộ thí nghiệm A/B trong proposal.

Không thay dữ liệu, slack, mixer, optimizer hoặc độ sâu trong đợt này. Nhánh B/C tiếp tục công việc đã phân công.

## 2. Liên hệ lý thuyết với phép đo

Đặt:

- a = tổng bình phương sai số gán task: tổng_i (tổng_h x_i,h - 1)^2.
- c = tổng bình phương sai số phương trình tài nguyên: tổng_h,r (used_h,r + slack_h,r - capacity_h,r × y_h)^2.
- V = a + c; E = tổng_h y_h + P × V.

P quyết định chi phí vi phạm trong mục tiêu mà QAOA tối ưu. P nhỏ có thể làm phương án sai cạnh tranh về năng lượng. P lớn tăng chi phí vi phạm, đồng thời đổi Hamiltonian và bề mặt tối ưu của các góc; không bảo đảm QAOA tìm nghiệm tốt hơn.

Với dữ liệu nguyên, hai host và có nghiệm, **P>2 là điều kiện đủ** để cực tiểu QUBO hợp lệ: một sai số nguyên khác 0 bị phạt hơn chi phí tối đa hai host của nghiệm đúng. Điều kiện này không phải điều kiện cần, cũng không bảo đảm một lượt QAOA hữu hạn tìm được cực tiểu. Với P=1/2, kiểm tra tham chiếu riêng thay vì suy đoán mô hình chắc chắn sai.

Năng lượng thô đổi thang đo khi P đổi. Không chọn P vì `mean_qubo_energy` nhỏ nhất giữa các P. So tỷ lệ placement hợp lệ/tối ưu, số lượt có nghiệm và V trung bình. V có cả slack sai, không chỉ quá tải CPU/RAM. `mean_active_hosts` trong chẩn đoán gồm cả các mẫu sai, không phải số host của đáp án tốt nhất.

## 3. Thiết kế cố định

| Yếu tố | Giá trị |
| --- | --- |
| P chung | 1, 2, 3, 5, 8 |
| Dữ liệu mặc định | p1_tight, p1_choice |
| Độ sâu | p=1 |
| Seed | 42, 43, 44 |
| Khởi tạo | goc_cu=[0.3,0.7]; gamma_nho=[0.3,0.05] |
| Ngân sách | 1024 shots/lần lấy mẫu; COBYLA maxiter=35 |
| Aer | CPU statevector double; 4 luồng; 2048 MiB |
| Giới hạn | 23 qubit; 300 giây kiểm tra giữa các lần đánh giá; RAM khả dụng tối thiểu 2 GiB |

Có 2 × 5 × 2 × 3 = **60 lượt mặc định**. Tổng hợp thành **20 nhóm**, mỗi nhóm ba seed. P=3 được chạy mới cùng đợt để làm đối chứng; không nhập báo cáo A1 vào chỉ mục mới.

P=1/2 thăm dò mức phạt thấp, P=3 giữ mốc đã dùng, P=5/8 thăm dò mức lớn hơn. Dãy này là lựa chọn thực nghiệm ban đầu, không phải dãy tối ưu đã được chứng minh. Giữ cùng giá trị số của góc khởi tạo khi đổi P; Hamiltonian đổi nên ảnh hưởng của góc cũng đổi. Kết quả được hiểu trong thiết kế này.

## 4. File cần chép

| File | Vị trí trong repo | Vai trò |
| --- | --- | --- |
| 07_qaoa_penalty_sweep.ipynb | notebooks/ | Thiết kế, chạy và tổng hợp |
| penalty_analysis.py | src/ | Sai số không nhân P và xử lý đồng hạng |
| test_penalty_analysis.py | tests/ | Kiểm tra sai số, đồng hạng và dữ liệu sai |
| qaoa_penalty_sweep.md | docs/ | Hướng dẫn song ngữ |
| a1_milestone_vi.md | docs/ | Bản văn bản mốc chỉ tiếng Việt |
| plan.md, todo.md | tasks/ | Tiến độ đã xác nhận và việc tiếp theo |

Dùng các module placement/qubo/ising/qaoa_experiment và JSON đã có. Không có thư viện mới, không cần nâng cấp Conda. Chọn kernel `nt409-khiem` Python 3.12.14. Có thể đặt PDF mốc vào docs/ khi muốn lưu trong repo.

## 5. Thực hiện và giải thích từng bước

1. **Chuẩn bị:** lưu notebook 06 có output. Chép các file mới đúng thư mục; mở notebook 07, Restart Kernel. Đóng kernel nặng khác để số đo tài nguyên dễ diễn giải.
2. **Bước 1:** kiểm tra Python/Qiskit/Aer và đường dẫn repo. Đây là xác nhận môi trường của phép đo, không cần nâng cấp thư viện.
3. **Bước 2:** giữ cấu hình mặc định. Bảng kế hoạch phải có 60 hàng. Một hàng là một instance, P, khởi tạo và seed; mã băm ghi nhận toàn bộ thiết kế.
4. **Bước 3:** xem từng instance/P có bao nhiêu qubit, nghiệm gốc, cực tiểu QUBO và mọi cực tiểu có hợp lệ hay không. Số qubit không tăng vì chỉ đổi hệ số, không thêm biến. Tham chiếu chính xác là dụng cụ kiểm chứng cho bộ nhỏ; chưa thay thế baseline MILP của B.
5. **Bước 4:** đo thử từng instance/P. Ước tính chỉ gồm phần lấy mẫu, chưa gồm mọi chi phí chuẩn bị, giải mã và chẩn đoán. Không coi nó là thời gian cam kết.
6. **Bước 5:** tạo đợt mới hoặc tiếp tục chỉ mục đã lưu. Thiết kế, input, phiên bản thư viện và hệ điều hành phải khớp khi tiếp tục.
7. **Bước 6:** chạy từng lượt tuần tự. Mỗi lượt hoàn tất được lưu ngay rồi cập nhật chỉ mục. Lượt hoàn tất nhưng không có nghiệm vẫn được giữ. Lượt dừng do ngân sách không sinh JSON kết quả riêng; đợt dừng và giữ các báo cáo đã hoàn tất.
8. **Bước 7:** đọc kết quả từng lượt. Hai cột probability ở bảng này được đổi sang %. None/NaN trong `unique_mode_valid` nghĩa là nhiều chuỗi đồng hạng, không phải không có placement đúng. Xem cùng hai cột đếm đồng hạng.
9. **Bước 8:** tổng hợp theo instance/P/khởi tạo, mỗi nhóm ba seed. So `feasible_pct_mean`, `optimal_pct_mean`, số lượt có nghiệm, thời gian và sai số. `*_std` dùng độ lệch chuẩn mẫu giữa seed, đơn vị điểm phần trăm; một seed chưa đủ tính.
10. **Bước 9:** xem mẫu thô của một lượt bằng `INSPECT_RUN_INDEX`. Mặc định là lượt đầu, nên None tại đây chỉ mô tả lượt đó. Chẩn đoán không sửa slack hoặc ghép lại task trước khi chấm.
11. **Bước 10:** cần PASS đối chiếu báo cáo nguồn/chỉ mục. Đủ đợt mặc định khi có 60/60 lượt. Lưu notebook có output và gửi C chỉ mục cùng tất cả JSON được tham chiếu.

## 6. Chạy p0_reference riêng

Restart Kernel và sửa Bước 2:

```python
RUN_INSTANCE_IDS = ["p0_reference"]
RESUME_MANIFEST = None
```

Giữ các thông số khác. Có **30 lượt**, **10 nhóm**, vẫn 23 qubit. Chạy Bước 1-10, xem đo thử trước khi tối ưu. Đợt có 0 nghiệm vẫn là kết quả của cấu hình đã chạy, không tự chứng minh instance vô nghiệm.

Muốn tiếp tục đợt đã dừng, dùng `RESUME_MANIFEST` trỏ đến chỉ mục của notebook 07 trong phase4a_penalty_runs và giữ nguyên thiết kế/input/môi trường. Chạy lại riêng cell thực thi bỏ qua các lượt hoàn tất. Chạy lại phần tạo đợt với None sẽ tạo đợt mới.

## 7. Các trường chẩn đoán và lưu trữ

`penalty_analysis` trong báo cáo gồm trung bình số host bật, sai số gán, sai số phương trình tài nguyên, tổng sai số không nhân P, năng lượng dựng lại, số chuỗi có tần suất lớn nhất, số chuỗi hợp lệ trong nhóm đó và tính hợp lệ của mode duy nhất. `penalty_analysis_seconds` là chi phí tính chẩn đoán, tách khỏi thời gian bộ giải và giải mã.

`unique_mode_valid` là null nếu có nhiều mode đồng hạng. Trường cũ `metrics.most_frequent_valid` vẫn giữ tương thích với runner và kiểm tra mẫu đầu sau khi sắp xếp; không dùng nó như kết luận về một mode duy nhất khi có đồng hạng.

Báo cáo từng lượt giữ schema 2 trong `data/reference_results/phase3_runs/`, thêm `experiment.purpose=controlled_common_penalty_pilot` và P. Chỉ mục schema 1 nằm ở `data/reference_results/phase4a_penalty_runs/`, scope `phase4a_common_penalty_pilot`. Khóa lượt có P; không gộp nhầm hai P cùng seed. Không tính một lượt nhiều lần vì có notebook, báo cáo và chỉ mục.

RAM là đỉnh toàn vòng đời tiến trình, không phải mức tăng thêm từng lượt. Ngưỡng Aer không giới hạn toàn bộ RAM Python. Không gộp số liệu kiểm thử của trợ lý vào thí nghiệm Windows của A.

## 8. Tiêu chí kết thúc và bước sau

Chỉ xác nhận A đã hoàn tất khi nhận được các báo cáo thật. Không chọn một seed tốt nhất rồi gọi là cấu hình thắng; giữ mọi lượt hoàn tất và ghi số lượng mỗi nhóm. Ba seed là khám phá ban đầu; xác nhận tính ổn định cần thiết kế riêng.

Sau khi review đợt chung: quyết định khảo sát hệ số gán/dung lượng độc lập theo proposal, rồi độ sâu p=1/2/3 với ngân sách rõ ràng; B/C cung cấp baseline và phân tích. Mọi thay đổi mô hình cần kiểm chứng lại. Không bảo đảm tăng P hoặc p luôn tăng tỷ lệ nghiệm.

Nguồn: proposal NT409 Topic 16, mục 3/5/6; [LinearEqualityToPenalty, Qiskit Optimization 0.7.0](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html). Converter đưa phương trình tuyến tính vào mục tiêu dưới dạng phạt; notebook dùng P do nhóm chọn rõ ràng.

Kiểm chứng bản bàn giao: 11 bài kiểm tra đạt; 20 lượt Aer rút gọn trên tight/choice với đủ năm P và hai khởi tạo; thêm 4 lượt trên reference 23 qubit và bộ vô nghiệm với P=1/8. Đã kiểm tra lưu báo cáo, đồng hạng, chạy lại, tiếp tục và chặn thiết kế không khớp. Các lượt rút gọn dùng 128 shots, maxiter=4 trên môi trường kiểm thử, không phải kết quả Windows với ngân sách chính thức.

---

# Common-penalty sweep after A1

## Scope and theory

A1 contains 18 real Windows trials across tight, choice and reference. Notebook 07 takes the first penalty-study increment: A=B=P, using the existing verified model and Aer runner. Independent assignment/capacity penalties remain a separate model change before completing the proposal's full penalty study. Depth studies follow afterward.

Write E=sum(y)+P×V, with V the sum of squared assignment and resource-equation residuals. V includes incorrect slack, not only overload. With integer residuals and two hosts, P>2 is sufficient for feasible global QUBO minima when the instance is feasible; it does not guarantee a finite QAOA run finds those minima. Smaller penalties require their own exact reference and are not automatically wrong.

Raw energies have different scales across P. Compare original feasibility/optimality, successful-run counts, runtime and unweighted squared errors. Mean active hosts includes invalid samples and is not the returned best objective.

## Design and files

Penalties 1,2,3,5,8; depth 1; shots 1024; COBYLA maxiter 35; seeds 42,43,44; initial points [0.3,0.7] and [0.3,0.05]. Default tight/choice: 60 trials and 20 groups. Reference separately: 30 trials and 10 groups. Fixed numerical initial angles are evaluated under each changed Hamiltonian. No optimizer, input or slack changes in this increment. P=3 is rerun as a contemporaneous control; A1 files are not imported as extra trials.

Add notebook 07, src/penalty_analysis.py, its unittest, this document, the Vietnamese milestone document and updated task documents. Use existing src modules and input JSON. No new dependency or upgrade is required. Keep the Conda Python 3.12 kernel.

## Execution

Save notebook 06 outputs; copy the new files and restart the kernel. Steps 1-10 check environment, fix the design, compute exact references for every P, probe resources, initialize/resume a campaign, execute sequentially with immediate per-run persistence, inspect individual results, aggregate by instance/P/initial point, inspect raw samples and cross-check source reports. Default completion is 60/60.

For reference, set RUN_INSTANCE_IDS=["p0_reference"], RESUME_MANIFEST=None and retain other settings. Expect 30 trials. For resume, use a notebook-07 manifest in phase4a_penalty_runs and preserve design/input/library versions/platform. Rerunning only execution skips completed trials; setup with no resume starts a new campaign. Interrupted trials are not saved as result JSON; completed zero-feasibility trials remain.

## Diagnostics and interpretation

Reports add penalty_analysis with mean active hosts, assignment/resource-equation errors, total squared error, reconstructed energy and counts of tied frequency maxima. unique_mode_valid is null for ties. The legacy most_frequent_valid field still checks the first sorted sample; do not interpret it as a unique mode. Additional diagnostic timing is separate from solver and decoding times.

Per-run reports keep schema 2 in phase3_runs and record controlled_common_penalty_pilot in experiment.purpose. Campaign scope is phase4a_common_penalty_pilot under phase4a_penalty_runs; run keys include P. Count each trial once. OS memory peak covers process lifetime; the time budget is checked between evaluations. Test-machine outputs stay separate from A's experimental data.

Three seeds per group are exploratory. Standard deviations use ddof=1; one seed is insufficient. Preserve every completed trial and missing objectives as null. Inspect-run defaults to the first report, not the campaign's best solution. Review actual Windows reports before choosing penalties, independent-penalty changes or depth studies. Coordinate with B's baselines and C's analysis. Source: the proposal sections 3/5/6 and the official converter documentation linked above.

Delivery validation: 11 tests passed; 20 reduced-budget Aer runs covered all five penalties and both initial points on tight/choice, plus four reference/infeasible boundary runs at P=1/8. Persistence, diagnostics, rerun/resume and design-mismatch guards were verified. Reduced tests used 128 shots and maxiter=4; they are not A's official-budget Windows experiment.
