# NT409 — Nhánh B và Notebook 21

Cập nhật ngày 22/10/2026: protocol B v1.1 sửa tương thích Python 3.14. Bộ thuật toán: **First-Fit (FF), Best-Fit Decreasing (BFD), MILP qua OR-Tools/SCIP**. Không chạy Best-Fit riêng, theo yêu cầu mới nhất. Nhánh B bổ sung đối chứng classical đúng bài toán task placement; không chạy lại QAOA và không sửa các campaign A.

## 1. Chúng ta đang làm gì?

Nhánh A đã mô hình hóa và giải task placement bằng QUBO/Ising/QAOA, có tối ưu mã hóa và các thí nghiệm hai/ba host. Nhánh B trả lời câu hỏi còn thiếu: trên **chính các input đó**, các thuật toán placement chạy trên máy cổ điển trả nghiệm nào, chất lượng ra sao, mất bao lâu?

Có hai nhóm đối chứng khác nhau. Vét cạn và lấy mẫu đều có sẵn ở A giúp biết optimum và xác suất nền. FF/BFD/MILP mới ở B là những phương pháp thực sự giải bài toán placement, không thay thế bằng lấy mẫu bitstring QUBO. MILP là một mô hình tối ưu toán học; SCIP là solver dùng để giải mô hình đó.

Kết quả có ích dù QAOA không thắng: ta phân biệt chất lượng nghiệm, khả năng trả nghiệm, chi phí thực thi và giới hạn của từng phương pháp. Không coi phần mềm chạy đúng là chứng minh ưu thế lượng tử.

## 2. Dữ liệu và phạm vi đã chốt

| Nhóm | Instance | Vai trò |
|---|---|---|
| Hai host | p1_choice, p1_tight, p0_reference | 3 input so sánh chính, đối chiếu Notebook 17 |
| Ba host, 4 task | a3_test_n4_1, a3_test_n4_2, a3_test_n4_3 | 3 input so sánh chính, đối chiếu Notebook 20 |
| Ba host, 5 task | a3_test_n5_1, a3_test_n5_2, a3_test_n5_3 | 3 input so sánh chính, đối chiếu Notebook 20 |
| Controls | p1_infeasible, a3_one_host, a3_infeasible | Kiểm tra vô nghiệm và trường hợp có thể dùng một host |

Tổng cộng **12 × 3 = 36 kết quả chất lượng**, gồm **27 chính + 9 controls**. Hai instance dev của Notebook 19 không nằm trong bảng xếp hạng B. Không nhân seed cho FF/BFD để tạo mẫu chất lượng giả. Không mở rộng kích thước hoặc tăng RAM/qubit.

`data/benchmarks/nt409_classical_b_v1_1/protocol.json` là protocol B mới, chứa đầy đủ đường dẫn và canonical SHA256 của từng input, quy tắc thuật toán, solver và ngân sách. Protocol A/handoff v1 vẫn giữ nguyên, kể cả template cũ.

Canonical JSON dùng `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`, `allow_nan=False`. Khác xuống dòng/thụt lề không đổi định danh; đổi dữ liệu hoặc thứ tự task/host sẽ bị chặn. Mã validator chung cũng được kiểm tra hash văn bản chuẩn hóa LF. Protocol B v1 cũ giữ nguyên; v1.1 khóa OR-Tools mới. Protocol hiện hành không được sửa giữa campaign; thay thiết kế cần phiên bản mới.

Đây là bộ fixture nhỏ đã biết và đã chạy A. B không biến chúng thành test set mới độc lập; không suy ra kết quả khái quát trên mọi bài toán placement.

## 3. First-Fit làm gì?

1. Lấy task lần lượt theo thứ tự JSON.
2. Xét host theo thứ tự JSON; chọn host đầu tiên còn đủ **cả CPU và RAM**.
3. Trừ tài nguyên đã dùng, bật host nếu cần và tiếp tục.
4. Nếu không host nào nhận được một task, trả `no_placement_found`. Không bỏ task, không quay lui, không gọi MILP để sửa nghiệm.

FF nhanh vì quyết định cục bộ đơn giản. Nhưng task nhỏ đặt trước có thể chiếm chỗ của task lớn. Việc FF thất bại không chứng minh bài toán vô nghiệm.

Ví dụ hai host có CPU/RAM lần lượt (4,4) và (6,6), ba task (2,2), (4,4), (4,4): FF đặt task đầu lên host thứ nhất, task thứ hai lên host thứ hai rồi không còn chỗ cho task cuối. Bài toán vẫn có nghiệm nếu đặt task (2,2) cùng một task (4,4) lên host (6,6).

## 4. Best-Fit Decreasing khác thế nào?

BFD dùng đúng định nghĩa đa tài nguyên đã chốt trong `docs/unified_benchmark_v1.md`:

- Gọi Cmax là CPU capacity lớn nhất và Rmax là RAM capacity lớn nhất của các host.
- Độ lớn task i: `size(i) = max(cpu_i/Cmax, ram_i/Rmax)`.
- Sắp task theo size giảm dần; hòa thì giữ thứ tự task nguồn.
- Với mỗi task, ưu tiên các host đang bật và đủ CPU/RAM. Chỉ khi không có host đang bật phù hợp mới xét host chưa bật.
- Trong tập ứng viên, tối thiểu hóa `CPU_còn_dư_sau_đặt/CPU_capacity + RAM_còn_dư_sau_đặt/RAM_capacity`.
- Hòa điểm thì chọn host xuất hiện trước trong JSON.
- Trả placement về đúng thứ tự task gốc.

Mã dùng phân số hữu tỉ để các trường hợp hòa điểm không phụ thuộc sai số float. Chi phí này được tính vào thời gian BFD. Không có thuật toán Best-Fit độc lập trong campaign.

Trong ví dụ FF thất bại ở trên, BFD xử lý hai task (4,4) trước rồi đặt task (2,2) vào chỗ còn lại, nên tìm được nghiệm. Tuy nhiên **BFD không được bảo đảm tốt hơn FF**: host có capacity khác nhau và cả hai ràng buộc tài nguyên có thể làm lựa chọn cục bộ không có lợi. Không áp dụng máy móc bảo đảm xấp xỉ của bin packing một chiều với bin đồng nhất cho bài toán này.

## 5. MILP: mô hình và chứng nhận

Với task i, host h, tài nguyên r thuộc {CPU, RAM}:

- `x[i,h] ∈ {0,1}`: task i được đặt trên host h.
- `y[h] ∈ {0,1}`: host h được bật.
- Mục tiêu: tối thiểu `sum_h y[h]`.
- Mỗi task đúng một host: `sum_h x[i,h] = 1`.
- Tài nguyên: `sum_i demand[i,r] * x[i,h] <= capacity[h,r] * y[h]`.

Demand dương nên ràng buộc tài nguyên đã buộc task chỉ nằm trên host đang bật. Không cần biến slack hoặc penalty QUBO trong MILP. Đầu ra giữ nguyên x/y của solver, không tự tắt host dư để làm objective đẹp hơn.

Cấu hình: **OR-Tools 9.15.6755**, MPSolver backend **SCIP**, một luồng, giới hạn **600 giây cho Solve**, seed shift 0, relative/absolute gap limit 0. Backend version thực tế được ghi từ `SolverVersion()` trước campaign. Không cấp nghiệm/optimum vét cạn làm warm start, hint hoặc cutoff. Vét cạn chỉ dùng cho hậu kiểm.

`optimal` là solver chứng nhận tối ưu trong dung sai số học; `infeasible` là chứng nhận vô nghiệm. `feasible_not_proven` có incumbent nhưng chưa chứng nhận tối ưu. `no_incumbent` không có nghiệm; trạng thái này không tự chứng minh đã timeout hoặc bài toán vô nghiệm. Các trạng thái bất thường được giữ riêng.

Giá trị gần 0/1 trong dung sai 1e-6 được quy về bit; giá trị phân số như 0.5 bị từ chối. Raw giá trị từ solution proto được giữ lại. Sau đó `evaluate_model` kiểm tra ràng buộc bằng số nguyên và objective đối chiếu với solver. Đây là xử lý sai số số học, không sửa placement.

Nguồn API: [OR-Tools MIP example](https://developers.google.com/optimization/mip/mip_example), [MPSolver Python reference](https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Solver.html), [gói OR-Tools 9.15.6755](https://pypi.org/project/ortools/9.15.6755/). Bản khóa hỗ trợ Python >=3.9, nhưng wheel tùy phiên bản Python/nền tảng; nếu pip không có wheel tương thích, gửi lỗi để xử lý môi trường, không tự đổi solver/version trong protocol.

## 6. Kiểm tra và đo thời gian

Mọi nghiệm đều qua validator `src/placement.py`. Với instance rất nhỏ này, liệt kê độc lập toàn bộ 2^4, 3^4 hoặc 3^5 cách gán cho phép kiểm tra optimum và trường hợp vô nghiệm. Nó không nằm trong solver timing và không thay baseline MILP.

Mỗi cặp instance/thuật toán:

1. Chạy một lượt chính để lấy kết quả chất lượng và thời gian lần đầu trong process.
2. Nếu kết thúc với trạng thái bình thường và total dưới 10 giây: chạy một warm-up rồi năm phép đo thời gian. Nếu không, giữ kết quả chính và bỏ các lượt đo phụ, để tránh nhân nhiều lần một lượt khó/timeout.
3. Mỗi lượt đo cũng qua validator; trạng thái/objective phải khớp lượt chính. Không chọn kết quả tốt nhất trong sáu/bảy lần chạy.
4. Ghi toàn bộ raw reports, không chỉ median. Năm phép đo là lặp timing, **không** phải năm mẫu độc lập về chất lượng.

Các thành phần:

| Cột | Ý nghĩa |
|---|---|
| build_seconds | Kiểm tra/chuyển input, chuẩn bị trạng thái hoặc dựng mô hình MILP |
| solve_seconds | Quyết định heuristic (gồm sort BFD) hoặc gọi SCIP Solve |
| check_seconds | Lấy kết quả, kiểm tra x/y/placement và trạng thái |
| total_seconds | Tổng phạm vi từ đầu hàm giải đến kết thúc kiểm tra |
| quality_total_seconds | Thời gian lượt chất lượng chính |
| total_seconds_median | Trung vị năm lần đo warm, gồm build + solve + check |
| campaign_wall_seconds | Cả campaign: gồm thêm vét cạn, đọc/ghi file và tổng hợp |

Import thư viện, đọc/ghi file, export LP, vét cạn và phân tích không nằm trong total từng lượt. Thời gian rất nhỏ chịu ảnh hưởng overhead Python/OS; không xếp hạng rộng chỉ từ chênh lệch vài microsecond. Không tính thời gian ngủ của máy là compute thuần; giữ wall time gốc và ghi chú gián đoạn. Không chạy song song campaign/tác vụ nặng khi đo chính thức.

## 7. Notebook 21 gồm bảy bước

1. Nhận diện repo/kernel/runtime và in version SCIP.
2. Kiểm tra protocol/hash, hiển thị 12 instance và vai trò.
3. Chạy test nhánh B. Test bao gồm fixture nhỏ, kiểm tra MILP đối chiếu vét cạn, thử campaign trong thư mục tạm và phát hiện sửa dữ liệu.
4. Chạy 36 kết quả, in tiến độ và ghi raw sau mỗi cặp.
5. Bảng chất lượng, controls và ảnh `classical_quality.png`.
6. Ghép bảng A/B theo input hash và p. Dùng Notebook 17 cho hai host, Notebook 20 cho ba host; giữ riêng cả p1,p2,p3.
7. Audit đọc lại và xuất ZIP có SHA256 từng file. Lưu notebook đã chạy bằng Ctrl+S.

Campaign ngắn nên không triển khai resume phức tạp. Mỗi lần chạy bước 4 tạo thư mục mới; thư mục partial/error giữ để chẩn đoán. Không trộn các lần chạy hoặc ghi đè campaign cũ.

## 8. Cách đọc kết quả đúng

- `found_valid`: có nghiệm hợp lệ không.
- `objective`: số host bật của nghiệm đó; thất bại để trống, không ghi 0.
- `reference_optimum`: optimum vét cạn; input vô nghiệm để trống.
- `found_optimal`: nghiệm trả về đạt optimum khi hậu kiểm. FF/BFD có thể True mà không có khả năng tự chứng nhận.
- `solver_certified_optimal`: chỉ True khi MILP trả optimal và kiểm tra khớp reference.
- `optimality_gap = (objective - optimum)/optimum`: 3 thay vì 2 host là 50%; không tính gap cho thất bại hoặc input vô nghiệm.
- `solver_bound`: cận dưới solver cho bài toán min; `solver_gap` là gap tính từ incumbent và cận này, khác gap tới optimum reference.
- `status=PASS` của audit: dữ liệu và bảng khớp raw; xem thêm `milp_certificates_complete=True` để biết tất cả 12 input có chứng nhận cần thiết.

Bảng `comparison_a_b.csv` có **27 hàng**, mỗi instance × p. Nghiệm classical lặp lại theo p để tiện đọc, không tăng cỡ mẫu classical. QAOA: tỷ lệ lượt có ít nhất một nghiệm tối ưu trong batch 1024 shots qua năm seed; classical: một placement. Không coi P_opt mỗi shot QAOA là cùng đại lượng với `found_optimal` baseline.

Thời gian A là dữ liệu Windows lịch sử, A20 có sleep được người chạy xác nhận. Phạm vi trial A khác total B. Giữ cả hai con số nhưng **không tính speedup** hoặc tuyên bố quantum advantage từ bảng này. Nếu muốn nghiên cứu thời gian cạnh tranh chính thức, cần một giao thức timing chung mới, không chỉnh hồi tố số A.

## 9. File mới và đầu ra

| File | Vai trò |
|---|---|
| requirements-branch-b.txt | Chỉ bổ sung OR-Tools khóa version, không thay lock môi trường A |
| src/classical_baselines.py | FF, BFD, MILP và kiểm tra giá trị solver |
| src/classical_campaign.py | Protocol/hash, campaign, reference, bảng A/B, audit và ZIP |
| tests/test_classical_baselines.py | Kiểm thử thuật toán, status và toàn bộ input |
| tests/test_classical_campaign.py | Kiểm thử dữ liệu/campaign/export/chống sửa kết quả |
| data/benchmarks/nt409_classical_b_v1_1/protocol.json | Đặc tả B trước khi chạy benchmark Windows |
| notebooks/21_classical_baselines_b.ipynb | Notebook người dùng chạy |
| docs/branch_b_notebook21_vi.md | Tài liệu này |

Đầu ra tại `data/reference_results/phase4m_classical_b/b_<timestamp>/`: `campaign.json`, `protocol.json`, input, source snapshots, `raw/*.json`, `references.json`, `classical_results.csv`, `results.json`, `comparison_a_b.csv`, `summary.json`, ảnh, `audit.json`, `SHA256.json`. ZIP nằm cạnh thư mục đó.

Raw MILP có mô hình LP dạng text và giá trị x/y, bound/gap/status. Không gọi đó là solver stdout log hay chứng minh hình thức độc lập. Mọi phép đo môi trường kiểm tra Linux nằm trong `verification/`, không nhập làm kết quả Windows của người dùng.

## 10. Cài gói và chạy trên Windows

Gói bổ sung dựa trên backup `backup/a-phase4-20261013` (mốc d88b0af). Giải nén **nội dung** gói vào gốc `nt409-task-placement`: các thư mục src/tests/data/notebooks/docs phải nhập chung đúng vị trí, không tạo thêm một repo lồng bên trong. Gói chỉ thêm file B, không thay mã A hay input A. File hướng dẫn và kiểm tra Linux có tên riêng.

Trong terminal đang ở repo:

```bat
conda activate nt409-khiem
git switch -c feat/b-classical-baselines
python -m pip install -r requirements-branch-b.txt
python -m unittest discover -s tests
```

Nếu nhánh `feat/b-classical-baselines` đã tồn tại trên máy bạn, dùng `git switch feat/b-classical-baselines` thay lệnh tạo mới. Nếu không ở đúng backup A, chuyển về backup đó trước khi tạo nhánh B. Không cần merge main ở bước này.

Sau khi test báo OK: restart kernel, mở `notebooks/21_classical_baselines_b.ipynb`, chọn kernel nt409-khiem, Run All. Điền MACHINE_LABEL và TIMING_NOTE nếu cần. Nếu hash mismatch, dừng và gửi lỗi; không sửa/xóa guard.

Gửi ZIP mới + notebook đã chạy; hai CSV chính và audit.json có trong ZIP. Sau kiểm tra có thể commit/push nhánh B theo workflow terminal bình thường. Việc tạo nhánh/commit local trong gói kiểm tra không tự đẩy thay repo GitHub của bạn.

## 11. Điều kiện chốt B

- Test pass; input/protocol/hash đúng.
- 36 kết quả được lưu; 27 chính và 9 controls tách rõ; thất bại không bị loại.
- MILP optimal trên 10 input có nghiệm, infeasible trên hai input vô nghiệm; khớp vét cạn.
- Chất lượng FF/BFD được báo đúng dù kém hoặc thất bại.
- Timing Windows có runtime, nguồn, phạm vi và ghi chú; kết quả QA Linux không trộn vào.
- Bảng A/B cùng hash, raw/archive kiểm tra được và tài liệu đủ để bàn giao.

Hoàn tất các mục này sẽ đóng phần triển khai/thực nghiệm baseline B. Phần tổng hợp báo cáo và trình bày toàn đồ án vẫn cần nhóm hoàn thiện; không tự coi công việc C đã xong.
