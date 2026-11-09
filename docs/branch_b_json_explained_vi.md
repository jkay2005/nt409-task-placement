# Giải thích JSON và quy trình giải bài toán task placement — nhánh B

Tài liệu đối chiếu với mã và protocol B v1.1 ngày 22/10/2026. Phạm vi chính là `data/benchmarks/nt409_classical_b_v1_1/protocol.json`; các JSON đầu vào và đầu ra được giải thích để người đọc hiểu toàn bộ công đoạn. Bộ thuật toán là First-Fit, Best-Fit Decreasing và MILP.

## 1. JSON dùng để làm gì?

JSON là cách lưu thông tin theo cặp tên trường và giá trị để cả người và chương trình đọc được. Chuỗi nằm trong dấu ngoặc kép; số không cần ngoặc kép; `true`/`false` là giá trị đúng/sai; `null` biểu thị không có giá trị; `[]` là danh sách và `{}` là một đối tượng gồm các trường.

Trong đồ án, cần phân biệt ba loại thông tin:

| Loại JSON | Nội dung | Được dùng khi nào? |
|---|---|---|
| Input instance, ví dụ `p0_reference.json` | Task, host, CPU/RAM và mục tiêu bài toán | Trước khi giải |
| `protocol.json` | Danh sách input, thuật toán, phiên bản solver, ngân sách và quy tắc đo | Trước và trong campaign |
| `raw/*.json`, `results.json`, `summary.json`, `audit.json` | Nghiệm, thời gian và kết quả kiểm tra thực tế | Được chương trình tạo khi/sau khi chạy |

Việc viết protocol không tạo ra nghiệm hoặc chứng minh thuật toán thành công. Ví dụ `timing_repetitions: 5` yêu cầu năm phép đo theo điều kiện đã định; nó không có nghĩa đã đo năm lần. Kết quả phải có báo cáo thực thi tương ứng.

## 2. Công đoạn 1 — mô tả bài toán bằng input JSON

`p0_reference.json` có `objective: "min_active_hosts"`, nghĩa là tối thiểu số host được bật. `tasks` chứa nhu cầu tài nguyên của task; `hosts` chứa dung lượng tài nguyên của host.

| Đối tượng trong input | CPU | RAM |
|---|---:|---:|
| Task T1 | 2 | 4 |
| Task T2 | 3 | 2 |
| Task T3 | 1 | 3 |
| Task T4 | 4 | 5 |
| Host H0 | 5 | 6 |
| Host H1 | 6 | 8 |

`resource_units` trong input này ghi cả CPU và RAM là `unit`: đây là đơn vị mô hình, không tự động là GHz hay GB vật lý.

Một cách đặt hợp lệ là T1,T2 lên H0 và T3,T4 lên H1. H0 dùng CPU 5/RAM 6; H1 dùng CPU 5/RAM 8. Đầu ra placement theo chỉ số host là `[0,0,1,1]`. Chỉ số 0 tương ứng H0 và 1 tương ứng H1; thứ tự phần tử là thứ tự task nguồn. Cả hai host bật nên objective bằng 2. Đây là ví dụ giải thích có thể kiểm tra bằng phép cộng; protocol không truyền placement này làm gợi ý cho solver.

Input là một bài toán thử nghiệm được định nghĩa rõ. Không tự gọi nó là dữ liệu đo từ hệ thống cloud thực tế nếu không có nguồn thu thập tương ứng.

## 3. Công đoạn 2 — xác định phạm vi chạy trong protocol

```json
{
  "schema_version": 1,
  "study_id": "nt409_classical_b_v1_1",
  "algorithms": ["FirstFit", "BFD", "MILP"]
}
```

Đây là trích đoạn, không phải toàn bộ protocol.

- `schema_version`: phiên bản cấu trúc JSON; không phải kết quả đánh giá hay phiên bản thuật toán.
- `study_id`: mã nhận diện đợt thiết kế thực nghiệm B v1.1.
- `algorithms`: ba phương pháp được đưa vào campaign. FirstFit là First-Fit; BFD là Best-Fit Decreasing; MILP là mô hình tối ưu tuyến tính nguyên hỗn hợp, trong bài toán này chỉ dùng biến nhị phân.

Danh sách `instances` chứa 12 input. Mỗi phần tử có:

| Trường | Ý nghĩa |
|---|---|
| `instance_id` | Tên duy nhất dùng để liên kết input và báo cáo |
| `family` | Nhóm hai host (`two_host`) hoặc ba host (`three_host`) |
| `role` | Vai trò thiết kế: benchmark, test, negative_control hoặc functional_control |
| `input_path` | Đường dẫn tương đối từ gốc repo tới input JSON |
| `input_canonical_sha256` | Dấu vân tay của nội dung input đã chuẩn hóa |
| `include_in_main_comparison` | Có đưa input vào bảng so sánh chính hay chỉ báo cáo ở nhóm controls |

Phạm vi cụ thể:

| Nhóm | Các instance | Số lượng |
|---|---|---:|
| Hai host, so sánh chính | p1_choice, p1_tight, p0_reference | 3 |
| Ba host, 4 task, so sánh chính | a3_test_n4_1, a3_test_n4_2, a3_test_n4_3 | 3 |
| Ba host, 5 task, so sánh chính | a3_test_n5_1, a3_test_n5_2, a3_test_n5_3 | 3 |
| Controls | p1_infeasible, a3_one_host, a3_infeasible | 3 |

Tổng kế hoạch là 12 × 3 = 36 kết quả chất lượng: 27 chính và 9 controls. `a3_one_host` vẫn có ba host được cung cấp trong input; tên của nó diễn đạt trường hợp có thể đạt nghiệm một host. Hai controls infeasible dùng để kiểm tra cách xử lý bài toán vô nghiệm.

Việc đưa controls ra khỏi bảng chính dựa trên vai trò đã định, không phải bỏ một lượt chạy vì kết quả kém. Các heuristic thất bại trên input chính vẫn nằm trong bảng chính. Nhãn `test` kế thừa phân chia của nghiên cứu A; không có nghĩa các input này chưa từng được nhóm quan sát khi triển khai B.

## 4. Công đoạn 3 — giữ cùng dữ liệu và cách chấm

SHA256 là giá trị băm giúp phát hiện nội dung thay đổi. Với input, chương trình chuẩn hóa JSON bằng `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`, `allow_nan=False`, rồi mã hóa UTF-8 trước khi tính hash.

Thay khoảng trắng hoặc LF/CRLF không làm đổi hash canonical. Thay CPU/RAM, thêm task hoặc đổi thứ tự task/host sẽ làm đổi nội dung được băm. Sắp xếp khóa JSON không sắp xếp lại phần tử của danh sách task/host.

Các trường kiểm tra khác:

| Trường | Nội dung được bảo vệ |
|---|---|
| `a_group_normalized_sha256` | Văn bản bảng tổng hợp A, sau chuẩn hóa cách đọc BOM/xuống dòng |
| `a_groups_canonical_sha256` | Dữ liệu các hàng A sau khi phân tích CSV thành đối tượng; dùng khi kiểm tra bản chụp dữ liệu |
| `validator_normalized_sha256` | Văn bản `src/placement.py`, bộ kiểm tra nghiệm chung |

Ngoài các hash trong JSON, mã campaign có `PROTOCOL_HASH` để kiểm tra toàn bộ protocol. Vì vậy, file này không phải bảng tùy chọn để sửa tự do giữa các lượt đo. Một thay đổi có ý nghĩa cần thiết kế phiên bản mới và kiểm tra sự nhất quán với mã.

Hash chứng minh sự khớp với nội dung tham chiếu trong phạm vi kiểm tra. Hash không tự chứng minh thuật toán đúng, máy nào thực sự chạy hoặc người nào tạo dữ liệu; những điều đó cần mã nguồn, runtime, báo cáo thực thi và mô tả nguồn gốc.

## 5. Công đoạn 4 — giải bằng ba phương pháp

### First-Fit và BFD

Trường `heuristics` mô tả quy tắc đã chọn cho benchmark; hàm Python trong `src/classical_baselines.py` thực hiện các quy tắc đó.

First-Fit xử lý task theo thứ tự JSON và chọn host đầu tiên còn đủ cả CPU/RAM. Nếu không đặt được một task, thuật toán kết thúc với `no_placement_found`. Nó không bỏ task hoặc dùng một thuật toán khác để sửa nghiệm.

BFD tính độ lớn task i bằng `max(cpu_i/Cmax, ram_i/Rmax)`, với Cmax/Rmax là capacity lớn nhất theo từng tài nguyên. Task được sắp giảm dần theo độ lớn; hòa thì giữ thứ tự nguồn. Với mỗi task, thuật toán ưu tiên host đang bật và còn đủ tài nguyên; nếu không có mới xét host chưa bật. Trong tập ứng viên, chọn tổng tỷ lệ CPU/RAM dư sau khi đặt nhỏ nhất, chuẩn hóa theo capacity của chính host đó. Hòa thì chọn host có thứ tự nguồn nhỏ nhất.

Cuối cùng, BFD trả placement về thứ tự task gốc. Đây là định nghĩa BFD đa tài nguyên cụ thể của đồ án, không có bảo đảm rằng nó luôn tốt hơn First-Fit.

### MILP

Gọi x[i,h] là bit thể hiện task i nằm trên host h, y[h] là bit thể hiện host h được bật. Mục tiêu là tối thiểu tổng y[h]. Ràng buộc mỗi task: tổng x[i,h] theo h bằng 1. Với mỗi host và mỗi tài nguyên r: tổng demand[i,r] × x[i,h] không vượt capacity[h,r] × y[h].

| Trường | Giá trị | Ý nghĩa trong cách chạy hiện tại |
|---|---|---|
| `ortools_version` | 9.15.6755 | Khóa phiên bản thư viện Python OR-Tools |
| `solver` | SCIP | Backend giải mô hình MILP qua OR-Tools |
| `threads` | 1 | MILP được cấu hình một luồng |
| `time_limit_seconds` | 600 | Ngân sách cho một lần gọi Solve, không phải toàn notebook |
| `binary_tolerance` | 0.000001 | Dung sai khi kiểm tra giá trị solver gần bit 0/1 |

`solver_options` chứa ba dòng, được biểu diễn bằng ký tự `\n` trong chuỗi JSON:

```text
randomization/randomseedshift = 0
limits/gap = 0
limits/absgap = 0
```

Seed shift bằng 0 cố định tùy chọn randomization này. Hai gap limit bằng 0 không cho phép dừng với lý do đã đạt một mức gap dương do cấu hình đặt ra. Tuy vậy, solver vẫn có thể dừng vì giới hạn thời gian hoặc lý do khác; cấu hình này không bảo đảm mọi lần chạy tìm được tối ưu, cũng không loại bỏ dung sai số học của solver.

Giá trị gần 0/1 được chuyển về bit trong dung sai và kiểm lại bằng validator. Giá trị 0.5 bị từ chối. Giữ y do solver trả về; không tự tắt host để giảm objective. Chứng nhận `optimal` chỉ được ghi sau khi solver trả trạng thái tương ứng và nghiệm qua kiểm tra.

Một số trường protocol là đặc tả tương ứng với hằng số trong mã, như danh sách thuật toán, một luồng, tùy chọn SCIP và dung sai; không phải tất cả đều được truyền động từ JSON. Điều này là lý do phải kiểm tra đồng thời protocol và source khi thay thiết kế.

## 6. Công đoạn 5 — đo chất lượng và thời gian

| Trường | Giá trị | Ý nghĩa |
|---|---:|---|
| `quality_repetitions` | 1 | Một kết quả chất lượng cho mỗi cặp input/thuật toán |
| `timing_warmups` | 1 | Một lượt khởi động trước nhóm phép đo timing, nếu đủ điều kiện |
| `timing_repetitions` | 5 | Năm lượt đo timing bổ sung, nếu đủ điều kiện |
| `repeat_only_if_quality_total_below_seconds` | 10 | Chỉ đo lặp khi lượt chính có total dưới 10 giây và trạng thái phù hợp |

Lượt chính vẫn có thời gian riêng và quyết định kết quả chất lượng. Không chọn nghiệm tốt nhất giữa các lượt timing. Các phép đo bổ sung phải có trạng thái/objective khớp lượt chính. Năm lần đo timing không phải năm seed hoặc năm bài toán độc lập.

Nếu cả 36 cặp đều đủ điều kiện, có 36 lượt chất lượng + 36 warm-up + 180 lượt timing = 252 lần gọi hàm giải. Số kết quả chất lượng vẫn là 36. Nếu có lượt chậm hoặc trạng thái không phù hợp, số timing có thể thấp hơn 180 và phải được ghi đúng thực tế.

`timing_scope` định nghĩa phạm vi đo: chuẩn bị/kiểm tra input, dựng mô hình, giải và kiểm tra đầu ra trong process đã nạp thư viện. Không gồm import, đọc/ghi file, vét cạn tham chiếu, xuất mô hình LP hoặc phân tích. Đây không phải toàn bộ thời gian người dùng chờ từ khi mở notebook.

**Quy tắc timing v1.1:** các trạng thái được xét là `feasible`, `no_placement_found`, `optimal`, `infeasible`, cùng điều kiện lượt chính dưới 10 giây. Đo thời gian thất bại không biến thất bại thành nghiệm hợp lệ. Chuỗi `timing_policy` của v1.1 đã mô tả đủ hành vi này; v1 cũ có câu mô tả thiếu và được giữ nguyên làm lịch sử. Thay đổi mô tả không đổi logic đo.

## 7. Công đoạn 6 — kiểm tra nghiệm và ghép với A

`src/placement.py` kiểm tra task được đặt đúng một lần, x/y nhị phân và CPU/RAM không vượt capacity của host bật. Vét cạn trên các input nhỏ cho giá trị tham chiếu độc lập để hậu kiểm. Không cấp optimum hoặc placement vét cạn làm hint cho MILP/heuristic.

`a_comparison_notebooks: [17,20]` chọn dữ liệu A dùng cho đối chiếu: Notebook 17 với hai host và Notebook 20 với ba host. `a_group_path` trỏ tới bảng `handoff/nt409_branch_a_handoff_v1/tables/a_groups.csv`.

Bảng A/B được ghép theo cùng instance/hash và giữ riêng từng độ sâu p của QAOA. Có 9 input chính × 3 độ sâu = 27 hàng. Một kết quả classical xuất hiện lại trên các hàng p chỉ để tiện đối chiếu, không tăng số mẫu classical.

`limitations` ghi ba giới hạn:

1. A20 có thời gian chứa sleep do người chạy xác nhận; chưa có nghiên cứu timing end-to-end với phạm vi đo khớp nhau để kết luận speedup.
2. Bộ input nhỏ, cố định và đã biết; không suy ra hiệu quả trên mọi bài toán placement hay một holdout độc lập mới.
3. Heuristic không tìm được nghiệm không chứng minh bài toán vô nghiệm; lặp timing không phải lặp seed chất lượng.

Các giới hạn này là điều kiện diễn giải kết quả, không phải cơ chế điều chỉnh số liệu sau khi chạy.

## 8. Công đoạn 7 — hiểu các JSON đầu ra

| File | Nội dung và cách đọc |
|---|---|
| `campaign.json` | Trạng thái running/completed/failed, thời điểm chạy, môi trường, ghi chú người chạy, số bản ghi hoàn thành và hash source |
| `raw/<instance>__<algorithm>.json` | Kết quả quality, warmup, timings; chứa trạng thái, placement/x/y, objective và thời gian thực tế |
| `references.json` | Optimum và phân bố số host từ vét cạn, dùng để hậu kiểm |
| `results.json` | Các hàng kết quả được tổng hợp từ raw, gồm cả thất bại |
| `summary.json` | Số input chính có nghiệm hợp lệ/đạt tối ưu theo thuật toán |
| `audit.json` | Kết quả kiểm tra sự nhất quán giữa input, raw, reference và bảng |
| `SHA256.json` | Hash các file trong gói xuất để kiểm tra toàn vẹn |

`found_valid` nói có nghiệm hợp lệ. `objective` là số host bật, chỉ có nghĩa với nghiệm hợp lệ. `found_optimal` là nghiệm khớp optimum khi hậu kiểm; heuristic có thể đạt tối ưu mà không tự chứng nhận được. `solver_certified_optimal` là chứng nhận từ MILP được đối chiếu. `null` ở objective của lượt thất bại không có nghĩa là dùng 0 host.

`status: "PASS"` trong audit nghĩa là các kiểm tra được triển khai đã đạt, không có nghĩa mọi heuristic đều tối ưu hay QAOA thắng classical. `milp_certificates_complete` cho biết mọi kết quả MILP trong campaign có chứng nhận optimal hoặc infeasible theo yêu cầu. Số thực tế phải đọc từ campaign đang xét, không sao chép từ mẫu QA.

Các file trong `verification/branch_b_linux_qa/` của gói trước là kết quả kiểm tra thực thi trên môi trường Linux do trợ lý thực hiện. Không trình bày chúng là lần chạy của người dùng trên Windows. Notebook 21 tạo campaign mới trong `data/reference_results/phase4m_classical_b/` khi người dùng chạy. Ghi rõ nguồn gốc và môi trường của tập dữ liệu dùng trong báo cáo.

## 9. Đoạn mô tả quy trình có thể dùng trong báo cáo

“Nhánh B sử dụng bộ dữ liệu task placement chung với nhánh A để triển khai ba phương pháp đối chứng: First-Fit, Best-Fit Decreasing và MILP. Các input mô tả nhu cầu CPU/RAM của task và dung lượng CPU/RAM của host; mục tiêu là tối thiểu số host bật trong khi thỏa mãn ràng buộc gán và tài nguyên. Protocol JSON xác định danh sách input, quy tắc thuật toán, cấu hình solver và cách đo thời gian. Trước khi chạy, chương trình kiểm tra hash để bảo đảm input và bộ kiểm tra nghiệm khớp phiên bản tham chiếu. Sau khi giải, nghiệm được kiểm tra bằng validator chung và đối chiếu với vét cạn trên các instance nhỏ. Kết quả chất lượng được lưu riêng với các phép đo thời gian lặp. Bảng đối chiếu A/B giữ cùng input và từng độ sâu QAOA, đồng thời công bố giới hạn của việc so sánh thời gian.”

Đoạn trên mô tả phương pháp đã triển khai. Khi viết phần kết quả thực nghiệm, bổ sung ngày chạy, máy, phiên bản, mã campaign và số liệu lấy từ dữ liệu thực tế đã kiểm tra của nhóm.
