> **English version below.**

# Notebook 08 — Khảo sát hai hệ số phạt độc lập

Cập nhật ngày 06/10/2026. Nhánh A: Khiêm phụ trách mô hình QUBO/Ising/QAOA; B phụ trách FF/BFD/MILP; C phụ trách tổng hợp và báo cáo. Tài liệu này hướng dẫn đợt pilot tiếp theo sau khi đã review 90 lượt khảo sát P chung. Đây là bước nghiên cứu hai hệ số trong proposal; khảo sát độ sâu p=2/3 và xác nhận bằng seed mới sẽ thực hiện sau khi review pilot.

## 1. Vì sao thực hiện bước này?

Đợt trước dùng cùng P cho cả lỗi gán task và lỗi phương trình tài nguyên. Trên reference, 21/30 lượt tìm thấy placement hợp lệ, nhưng tổng số mẫu hợp lệ chỉ là 33/30.720; tất cả các mẫu đó đạt mục tiêu 2 host. Không có mẫu đo đạt cực tiểu toàn bộ QUBO. Đã chạy xong ma trận P chung, nhưng chất lượng lấy mẫu còn hạn chế.

Khi thay P chung, hai nhóm lỗi cùng đổi trọng số. Ta chưa biết ưu tiên riêng việc gán task hay việc thỏa phương trình tài nguyên có hữu ích hay không. Notebook 08 tách hai trọng số để kiểm tra câu hỏi đó, trong khi giữ nguyên dữ liệu, số qubit, độ sâu, shots, optimizer và bộ mô phỏng. Pilot được giới hạn ở 24 lượt, trước khi cân nhắc nghiên cứu tiếp.

Tỷ lệ gộp của 30 lượt reference trước là 0,107422%, gần baseline lấy mẫu đều 0,097656%. Tỷ lệ gộp mô tả cả đợt với nhiều cấu hình; không phải xác suất của một cấu hình cụ thể. Không sử dụng nó để tuyên bố một cặp penalty chắc chắn tốt hơn baseline.

## 2. Mô hình toán học và ý nghĩa thực hành

Năng lượng mới:

\[
E(x,y,s)=\sum_h y_h
+\lambda_{\mathrm{assign}}\underbrace{\sum_i\left(\sum_hx_{i,h}-1\right)^2}_{V_{\mathrm{assign}}}
+\lambda_{\mathrm{capacity}}\underbrace{\sum_{h,r}\left(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h\right)^2}_{V_{\mathrm{capacity}}}.
\]

- \(x_{i,h}=1\): task i được đặt nguyên vẹn lên host h. Mỗi task phải có đúng một bit x bằng 1 trên hàng của nó.
- \(y_h=1\): host h được bật. Mục tiêu gốc là giảm \(\sum_hy_h\).
- \(s_{h,r}\): phần tài nguyên dư, mã hóa bằng các bit slack; r là CPU hoặc RAM. Slack không chia task thành các phần.
- \(V_{\mathrm{assign}}\): tổng bình phương lỗi gán task. Task bị bỏ sót hoặc được gán hai lần đều tạo lỗi.
- \(V_{\mathrm{capacity}}\): tổng bình phương lỗi phương trình tài nguyên. Lỗi này có thể do placement vi phạm, hoặc do bit slack không biểu diễn đúng phần dư dù placement đã hợp lệ.
- Hai lambda quyết định chi phí của mỗi nhóm lỗi. Chúng thay đổi các hệ số QUBO/Ising, không thêm biến hoặc qubit.

Ví dụ một mẫu có 2 host bật, lỗi gán bằng 1 và lỗi tài nguyên bằng 4: với (3,3), E=2+3×1+3×4=17; với (12,3), E=2+12×1+3×4=26. Cùng một mẫu bị phạt gán task mạnh hơn trong mô hình thứ hai. Vì thang đo khác nhau, không xếp hạng hai cấu hình chỉ bằng năng lượng trung bình thô.

**Bảo đảm toán học và kết quả QAOA là hai điều cần kiểm tra riêng.** Với hai host, dữ liệu nguyên và mã hóa slack hiện tại, một phương án hợp lệ có thể chọn slack đúng và E không quá 2. Mọi mẫu vi phạm có ít nhất một bình phương lỗi nguyên lớn hơn hoặc bằng 1. Vì vậy, min(lambda_assign, lambda_capacity)>2 là điều kiện đủ để mọi cực tiểu toàn cục QUBO hợp lệ, nếu bài toán có nghiệm. Các cặp (3,3), (12,3), (30,3), (3,6), (3,12) đáp ứng điều kiện này. (1,1) là đối chứng thực nghiệm; các cực tiểu được kiểm chứng riêng trên fixture hiện tại, không có bảo đảm chung từ lập luận trên.

QAOA chạy với p=1 và optimizer hữu hạn có thể chưa tìm được các cực tiểu đó. Tăng lambda cũng đổi cảnh quan tối ưu và các pha của mạch; điều này không bảo đảm xác suất nghiệm tăng. Mục đích pilot là đo tác động thực tế.

`LinearEqualityToPenalty` của Qiskit Optimization 0.7 nhận một penalty chung. Module mới dùng converter với lambda_capacity, sau đó cộng phần chênh lệch (lambda_assign−lambda_capacity)×V_assign vào mục tiêu. Nếu hai lambda bằng nhau, phần chênh lệch bằng 0 và hệ số QUBO giữ đúng mô hình cũ. Các kiểm tra đại số bao phủ cả trường hợp lambda_assign nhỏ hơn lambda_capacity.

## 3. Phạm vi và ma trận mặc định

| Thành phần | Giá trị | Lý do |
|---|---|---|
| Input | p1_choice, p0_reference | Choice kiểm tra mục tiêu 1 host; reference kiểm tra ví dụ gốc với nghiệm tối ưu 2 host |
| Số qubit | 20 và 23 | Chỉ đổi trọng số; giữ nguyên x/y/slack |
| Độ sâu | p=1 | Tách tác động penalty khỏi tác động độ sâu |
| Shots | 1024 | Giữ ngân sách lấy mẫu như đợt trước |
| Optimizer | COBYLA, maxiter=35 | Giữ ngân sách tối ưu như đợt trước |
| Seed | 42 | Pilot khám phá có giới hạn |
| Khởi tạo | [0.3,0.7] và [0.3,0.05] | Giữ hai khởi tạo đã dùng; thứ tự tham số hiện tại là beta[0], gamma[0] |
| Backend | Aer CPU statevector | Giữ cách mô phỏng đã xử lý vấn đề bộ nhớ |
| Tài nguyên | 4 threads, aer_memory_mb=2048, tối thiểu 2 GiB khả dụng | Giữ cấu hình hiện tại và đo thử trước khi tối ưu |
| Ngân sách thời gian | 300 giây mỗi lượt | Kiểm tra giữa các lần đánh giá, không phải ngắt cứng đúng giây 300 |

| pair_id | lambda_assign | lambda_capacity | Câu hỏi |
|---|---:|---:|---|
| control_P1 | 1 | 1 | Tái lập đối chứng P=1 bằng bộ mã hiện tại |
| control_P3 | 3 | 3 | Tái lập đối chứng P=3 bằng bộ mã hiện tại |
| assignment_12 | 12 | 3 | Ưu tiên gán đúng task có giúp tăng tỷ lệ one-hot/khả thi không? |
| assignment_30 | 30 | 3 | Phạt gán mạnh hơn nữa có lợi hay gây khó tối ưu? |
| capacity_6 | 3 | 6 | Ưu tiên phương trình tài nguyên ở mức vừa có ích không? |
| capacity_12 | 3 | 12 | Ưu tiên phương trình tài nguyên mạnh hơn có ích không? |

Tổng: 2 input × 6 cặp × 2 khởi tạo × 1 seed = **24 lượt**. So với kế hoạch ban đầu, bổ sung đối chứng (1,1) và chạy mới cả hai đối chứng trong cùng bộ mã để có nguồn gốc trực tiếp. Các báo cáo cũ vẫn là mốc lịch sử. Đối chứng cùng input/cấu hình/seed là tái lập, không được cộng thành những lần lặp độc lập mới của đợt 90 lượt.

`p1_tight` và `p1_infeasible` được dùng trong kiểm thử hồi quy. Không cần thêm chúng vào pilot mặc định. Notebook có thể đọc chúng, nhưng đổi input sẽ tạo một thiết kế/campaign mới.

## 4. Cài đặt các tệp

Chép toàn bộ 12 tệp trong gói vào repo, giữ đúng đường dẫn tương đối. Các tệp cùng tên cần cập nhật để module và notebook tương thích.

| Nhóm | Tệp |
|---|---|
| Module cập nhật | src/qubo.py, src/qaoa_experiment.py, src/penalty_analysis.py |
| Module mới | src/independent_campaign.py |
| Notebook mới | notebooks/08_qaoa_independent_penalties.ipynb |
| Tài liệu mới | docs/qaoa_independent_penalties.md |
| Kiểm thử | tests/test_qubo_penalties.py, tests/test_qaoa_experiment.py, tests/test_penalty_analysis.py, tests/test_independent_campaign.py |
| Tiến độ | tasks/plan.md, tasks/todo.md |

Không có dependency mới trong gói này. Dùng môi trường Conda `nt409-khiem` / Python 3.12 của dự án; Python 3.14 cài ở cấp máy không phải kernel dùng cho notebook. Giữ các instance và toàn bộ báo cáo cũ. Sau khi chép module, **Restart Kernel** trong VS Code để Python nạp mã mới; chỉ chạy lại cell import có thể vẫn dùng module cũ đang lưu trong bộ nhớ.

Nếu muốn chạy kiểm tra phần mềm trước, mở terminal ở thư mục gốc repo và chạy:

```bat
conda activate nt409-khiem
python -m unittest discover -s tests -v
```

Các kiểm tra có một số lượt Aer ngắn; đây là kiểm thử phần mềm, không thay thế 24 lượt thực nghiệm mặc định.

## 5. Chạy notebook và hiểu từng bước

1. **Bước 1 — Môi trường.** In đường dẫn repo, Python/thư viện và hash mã nguồn. Kiểm tra kernel là Python 3.12, repo là thư mục của bạn. Hash ghi nhận các file nguồn phục vụ đối chiếu và resume.
2. **Bước 2 — Thiết kế.** Giữ nguyên cấu hình mặc định và `RESUME_MANIFEST=None` khi chạy lần đầu. Bảng phải có 24 lượt. Cell dựng 12 mô hình và tính tham chiếu chính xác cho từng mô hình; đây là kiểm chứng fixture nhỏ của A, không thay baseline MILP của B.
3. **Bước 3 — Đại số và tham chiếu.** Cần có PASS với 120 vector kiểm chứng. Hai đối chứng có hệ số QUBO bằng lời gọi P chung. Choice có mục tiêu gốc 1, reference có mục tiêu gốc 2; QUBO vẫn có 20/23 biến. PASS chứng minh các biểu diễn khớp trên các phép kiểm tra, không chứng minh QAOA đã giải xong.
4. **Bước 4 — Tài nguyên.** Mỗi mô hình được transpile/lấy mẫu một lần để đo. Bảng in thời gian lấy mẫu, ước tính phần lấy mẫu cho mỗi lượt và RSS. Ước tính không bao gồm chính xác toàn bộ optimizer/hậu xử lý. Một statevector complex128 cần khoảng 16 MiB cho 20 qubit và 128 MiB cho 23 qubit; đó là dung lượng một mảng, không phải toàn bộ tiến trình. `aer_memory_mb` giới hạn bộ nhớ trạng thái lượng tử của Aer, không phải tổng RAM Python. Nếu cell dừng vì chạm ngân sách, xem lại phép đo trước khi chạy Bước 6.
5. **Bước 5 — Manifest.** Tạo file `campaign_....json` và in đường dẫn. Manifest là chỉ mục: giữ thiết kế, input, runtime, mã nguồn, các lượt dự kiến/hoàn tất và đường dẫn báo cáo. Giữ lại đường dẫn này nếu cần tiếp tục sau khi đóng VS Code.
6. **Bước 6 — Chạy QAOA.** Chạy tuần tự 24 lượt. Sau mỗi lượt hoàn tất, lưu JSON mẫu đo rồi cập nhật manifest nguyên tử. `host tốt nhất: None` nghĩa là lượt đó chưa đo được placement hợp lệ; lượt hoàn tất này vẫn được lưu. Lượt bị ngắt/chưa hoàn tất không được ghi thành báo cáo kết quả. Các lượt trước vẫn giữ nguyên.
7. **Bước 7 — Từng lượt.** Xem xác suất gán đúng, khả thi, tối ưu và gap. Ba cột probability trong bảng này đã đổi sang phần trăm; JSON nguồn giữ giá trị từ 0 đến 1. Dùng bảng để biết lỗi đang nằm ở gán task hay ở bước thỏa dung lượng.
8. **Bước 8 — Tổng hợp.** Nhóm theo input/cặp/khởi tạo. Mỗi nhóm mặc định có một seed, vì vậy độ lệch chuẩn giữa seed là NaN. So chất lượng và chi phí với đối chứng cùng input/khởi tạo/ngân sách. Không kết luận cấu hình thắng ổn định từ một seed.
9. **Bước 9 — Mẫu đo thật.** Đổi `INSPECT_RUN_INDEX` để xem một lượt cụ thể: thứ tự tham số, nghiệm hợp lệ tốt nhất, chẩn đoán và năm bitstring phổ biến đầu tiên. Chấm trực tiếp bit đo; không sửa task hoặc slack trước khi chấm.
10. **Bước 10 — Nhất quán và đầy đủ.** Kiểm tra lại manifest và báo cáo nguồn. Đợt chạy đủ phải in `24 / 24` và `Lượt còn lại: 0`, cùng PASS. PASS nhất quán cũng có thể xuất hiện với đợt còn thiếu lượt; luôn đọc thêm số hoàn tất. Chất lượng nghiệm là câu hỏi riêng, đánh giá bằng các bảng Bước 7–9.

## 6. Đọc các chỉ số đúng nghĩa

| Chỉ số | Cách hiểu |
|---|---|
| one_hot_probability | Xác suất tất cả task có đúng một host; chưa yêu cầu thỏa dung lượng |
| feasible_probability | Xác suất placement thỏa gán task và CPU/RAM với host bật; không yêu cầu bit slack đúng |
| optimal_placement_probability | Xác suất placement hợp lệ đạt số host tối ưu của bài toán gốc |
| qubo_ground_state_probability | Xác suất toàn bộ bit x/y/slack đạt năng lượng cực tiểu QUBO |
| observed_best_objective | Số host của mẫu hợp lệ tốt nhất trong lượt; None nếu chưa có mẫu hợp lệ |
| optimality_gap | Số host của nghiệm hợp lệ tốt nhất trừ tối ưu gốc; 0 là đạt tối ưu, None là chưa xác định |
| mean_assignment_error | Trung bình V_assign trên các mẫu đo; thấp hơn cho thấy ít lỗi gán hơn |
| mean_capacity_equation_error | Trung bình V_capacity; có thể lớn do slack sai dù placement hợp lệ |
| valid_runs / optimal_runs | Số lượt tìm thấy ít nhất một placement hợp lệ/tối ưu trong nhóm |
| dominant_bitstring_count | Số bitstring đồng hạng tần suất cao nhất; có thể nhiều hơn một |
| unique_mode_valid | Tính khả thi của bitstring phổ biến nhất nếu duy nhất; None nếu đồng hạng |
| elapsed_seconds | Thời gian tối ưu/lấy mẫu; hậu xử lý và chẩn đoán được ghi riêng |
| process_peak_rss_mib | Đỉnh RSS theo vòng đời tiến trình; có thể gồm hoạt động kernel trước lượt đang xét |

Placement tối ưu và ground state không đồng nghĩa: x/y có thể đã đúng nhưng slack sai. Việc không thấy ground state không tự động có nghĩa chưa tìm được đáp án placement. Ngược lại, chỉ giảm năng lượng trung bình không đủ để kết luận đáp án placement tốt hơn.

Proposal có quy tắc chọn mẫu phổ biến nhất. Module cũng ghi riêng mẫu hợp lệ tốt nhất để đánh giá khả năng lấy mẫu nghiệm; đây là lọc chọn bằng hậu xử lý. C cần công bố hai quy tắc rõ ràng, kể cả đồng hạng. Lượt không tìm thấy nghiệm vẫn nằm trong mẫu thống kê. Nếu input thật sự vô nghiệm, mục tiêu tối ưu/gap/xác suất placement tối ưu là None, không thay bằng 0.

## 7. Tiếp tục một đợt bị gián đoạn

1. Giữ nguyên input, cặp penalty, khởi tạo, seed, ngân sách, mã nguồn và runtime.
2. Restart Kernel, mở notebook và thay `RESUME_MANIFEST=None` bằng đường dẫn đã in ở Bước 5:

```python
RESUME_MANIFEST = "data/reference_results/phase4b_independent_runs/campaign_....json"
```

3. Chạy các cell theo thứ tự. Bước 5 kiểm tra báo cáo đã lưu; Bước 6 bỏ qua các lượt đã nằm trong manifest và chạy phần còn lại.

Chạy lại Bước 6 trong cùng kernel cũng bỏ qua lượt hoàn tất. Nếu chạy lại Bước 5 với `RESUME_MANIFEST=None`, bạn sẽ tạo campaign mới. Nếu sửa thiết kế/mã/runtime, cần tạo campaign mới với `RESUME_MANIFEST=None`; không dùng manifest cũ để trộn dữ liệu. Manifest notebook 06/07 không dùng làm manifest tiếp tục notebook 08. Cập nhật Git làm đổi byte nguồn cũng có thể khiến yêu cầu đối chiếu nguồn không còn khớp.

## 8. Kết thúc pilot và việc tiếp theo

Lưu notebook có output. Gửi notebook này cùng manifest và đủ các JSON được manifest tham chiếu trong `data/reference_results/phase4b_independent_runs/`. Với mặc định hoàn tất, campaign gồm một manifest và 24 JSON báo cáo; thư mục có thể có thêm campaign nếu đã chạy lại. Không cần gửi lại toàn bộ 90 báo cáo cũ cho việc review pilot nếu chúng đã có trong phiên review trước.

Sau review:

- Nếu có tín hiệu cải thiện, giữ tối đa 1–2 cấu hình ứng viên (gồm cặp penalty và khởi tạo) cùng đối chứng, rồi xác nhận trên seed mới dự kiến 45–49 với ngân sách giống nhau. Không dùng kết quả một seed chọn cấu hình để tự xác nhận cấu hình đó.
- Nếu không có tín hiệu rõ, dừng mở rộng ma trận penalty và chuyển sang khảo sát p=1/2/3. Trước mỗi độ sâu mới cần đo tài nguyên; khi tăng maxiter cần có đối chứng p=1 cùng ngân sách.
- B/C tiếp tục baseline và tổng hợp trên cùng JSON gốc. Đánh giá chất lượng, tỷ lệ thất bại, thời gian, RAM và quy tắc chọn đầu ra; không cần QAOA thắng MILP mới hoàn tất nghiên cứu.

Xác nhận seed mới chỉ đo độ ổn định trên fixture đã có, chưa chứng minh khả năng khái quát sang input mới. Quy mô 8 task/4 host trong proposal chưa được triển khai ở notebook này.

## 9. Kiểm chứng bộ mã trước bàn giao

Bộ mã đã qua 23 kiểm tra tự động, gồm hồi quy P chung, công thức/QUBO/Ising độc lập, tham chiếu/lấy mẫu đều, lượt Aer ngắn, báo cáo và resume. Notebook được chạy hết 10 code cell với toàn bộ 24 tổ hợp mặc định trên Linux, giảm ngân sách kiểm thử xuống shots=128/maxiter=4; tiếp tục cùng manifest không chạy lại các lượt đã lưu. Bốn lượt rút gọn khác kiểm tra tight/vô nghiệm, và ba báo cáo Windows P chung cũ được đối chiếu lại.

Các phép kiểm tra này xác minh phần mềm, không phải kết quả thực nghiệm của bạn với shots=1024/maxiter=35. Bộ mã ghi phiên bản runtime/mã nguồn thực tế; không giả định các hệ điều hành hoặc phiên bản thư viện khác nhau tạo cùng kết quả QAOA.

## Nguồn kỹ thuật

- [LinearEqualityToPenalty — Qiskit Optimization 0.7](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html)
- [Mã converter chính thức](https://qiskit-community.github.io/qiskit-optimization/_modules/qiskit_optimization/converters/linear_equality_to_penalty.html)
- [QuadraticProgram.minimize — mục tiêu hằng/tuyến tính/bậc hai](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.QuadraticProgram.html#qiskit_optimization.QuadraticProgram.minimize)

---

# Notebook 08 — Independent assignment and capacity penalties

Updated 6 October 2026. A owns QUBO/Ising/QAOA, B owns FF/BFD/MILP, and C owns analysis/reporting. This bounded pilot follows the reviewed 90-trial common-P campaign. It implements the proposal's independent-penalty question; depth 2/3 and fresh-seed confirmation follow pilot review.

## Motivation and formulation

The previous reference campaign found feasible/optimal placements in 21/30 trials but only 33/30,720 shots, with no observed full-QUBO ground states. Its pooled placement rate, 0.107422%, is close to the 0.097656% uniform baseline and is not the probability of one fixed configuration. Changing common P changes both constraint families together. This pilot tests whether giving assignment or capacity equations greater weight helps while preserving inputs, registers, depth, shots, optimizer and backend.

\[
E=\sum_h y_h+\lambda_{\mathrm{assign}}\sum_i(\sum_hx_{i,h}-1)^2
+\lambda_{\mathrm{capacity}}\sum_{h,r}(\sum_i d_{i,r}x_{i,h}+s_{h,r}-C_{h,r}y_h)^2.
\]

Each task is assigned whole to exactly one host. y denotes activation and slack denotes unused resource; changing weights does not add qubits. Capacity-equation error can reflect incorrect slack even when a placement is feasible. For two hosts with integer data, min(lambda_assign, lambda_capacity)>2 is sufficient for feasible global minima whenever a feasible placement exists: a valid encoding costs at most two, whereas any violation costs more than two. (1,1) is validated separately on current fixtures rather than covered by this guarantee. Finite-depth QAOA with finite optimization is not guaranteed to find those minima or improve when penalties increase.

Qiskit Optimization 0.7's converter takes one multiplier. The implementation converts with lambda_capacity, then adds (lambda_assign−lambda_capacity) times the squared assignment residuals. Equal weights reproduce the previous coefficients exactly. Tests also cover assignment weights below capacity weights.

## Default design

| Dimension | Setting |
|---|---|
| Inputs | p1_choice (20 qubits, optimum 1 host), p0_reference (23 qubits, optimum 2 hosts) |
| Weight pairs (assignment, capacity) | (1,1), (3,3), (12,3), (30,3), (3,6), (3,12) |
| Starts | [0.3,0.7], [0.3,0.05] in the current beta[0], gamma[0] order |
| Seed and depth | Seed 42, p=1 |
| Sampling/optimizer | 1024 shots, COBYLA maxiter=35 |
| Resources | Aer CPU statevector, 4 threads, 2048 MiB Aer state memory budget, at least 2 GiB available |
| Time budget | 300 seconds per trial, checked between evaluations rather than a hard interrupt |

The product has 24 trials. Both common-P controls are rerun in the current source version; identical input/configuration/seed controls are reproductions, not new independent repetitions of the old campaign. Tight/infeasible fixtures are regression tests rather than default pilot inputs. One seed per group is exploratory and leaves across-seed standard deviation undefined.

## Installation and notebook workflow

Copy all 12 package files into their matching repository paths: three updated source modules, new independent_campaign.py, notebook 08, this document, four test files and two task files. Keep existing instances and reports. No new dependency is introduced. Select the project Conda Python 3.12 kernel and restart it after replacing source modules. Optional verification from the repository root: `python -m unittest discover -s tests -v`.

Run steps 1–10 in order:

1. Print the repository, runtime and source hashes.
2. Keep the default design and `RESUME_MANIFEST=None`; expect 24 planned trials and 12 exact model references. A's tiny exact enumeration is a model check, not B's MILP baseline.
3. Verify 120 vectors against formula/QUBO/Ising and common-P coefficient controls. A PASS is software consistency, not evidence that QAOA has solved the instance.
4. Probe each model before optimization. A complex128 statevector array uses approximately 16 MiB at 20 qubits and 128 MiB at 23 qubits; total process memory is larger. Aer state memory limits do not cap total Python RSS. Sampling-time estimates are approximate and exclude some costs.
5. Create or verify a manifest containing design, inputs, runtime, sources, planned/completed trials and report paths.
6. Run sequentially, save each completed report and atomically replace the manifest. Completed zero-feasibility outcomes are retained; interrupted/incomplete trials are not saved as result reports.
7. Inspect per-trial quality and gap. Displayed probability columns are percentages; JSON probabilities remain in [0,1].
8. Compare grouped quality/success/cost, not raw energy across differently weighted models. Standard deviation is NaN for one seed.
9. Inspect measured samples, named parameters, tied frequency modes and the separate best-valid output. No task/slack repair is applied.
10. Verify source reports and manifest. Full default completion requires 24/24 and zero remaining trials as well as PASS. A partial campaign can pass consistency verification while still having work remaining.

One-hot probability requires correct task assignment only; feasibility also requires CPU/RAM capacities; original optimality also requires minimum host count. Full-QUBO ground states additionally constrain the entire encoding, including slack. A missing ground state does not imply no optimal placement was observed. A decreasing mean energy alone does not prove improved placements. Best-valid postselection differs from the proposal's most-frequent-output rule; disclose both, including ties. Missing valid samples or nonexistent original optima produce null gaps, not zero gaps. Lifetime process peak RSS may include earlier kernel activity; solver, decoding and diagnostic costs are recorded separately.

## Resume, handoff and next decision

Keep the exact same input/design/source/runtime. Restart the kernel, set `RESUME_MANIFEST` to the printed notebook-08 manifest path and run cells in order; completed run keys are verified and skipped. Rerunning step 6 in the same kernel also skips them. Rerunning step 5 with None creates a new campaign. Source/runtime/design changes require a new campaign; notebook 06/07 manifests cannot resume notebook 08. Git byte changes may invalidate an existing source identity.

Submit the executed notebook, manifest and all referenced report JSONs. A completed default campaign has one manifest plus 24 source reports; a directory may hold additional campaigns. Preserve the old 90 reports. After review, retain at most one or two candidate weight/start configurations and compare against controls on fresh seeds provisionally 45–49 with matched budgets. If there is no clear improvement, stop widening the penalty grid and test depths 1/2/3 with resource probes and matched depth-1 optimizer-budget controls. Fresh-seed checks measure stability on existing fixtures, not generalization. B/C continue their work on identical input JSONs. An honest comparison does not require QAOA to outperform MILP; the larger 8-task/4-host scale is not implemented in this pilot.

## Software verification and sources

Verification comprises 23 automated tests, all ten code cells and 24 actual Aer combinations at reduced shots=128/maxiter=4 on Linux, exact resume without reruns, four additional tight/infeasible boundary trials and three archived Windows common-P reports. These checks validate software rather than the user's default-budget Windows experimental quality. Actual versions and source identities are recorded.

Primary references: [LinearEqualityToPenalty](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html), [official converter source](https://qiskit-community.github.io/qiskit-optimization/_modules/qiskit_optimization/converters/linear_equality_to_penalty.html), and [QuadraticProgram.minimize](https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.QuadraticProgram.html#qiskit_optimization.QuadraticProgram.minimize).
