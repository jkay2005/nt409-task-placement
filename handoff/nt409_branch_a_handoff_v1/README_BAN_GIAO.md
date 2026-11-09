# Bàn giao nhánh A — Phase 4, phiên bản 1

Chốt ngày 14/10/2026. Mục đích: người nhận dùng đúng input của A, đọc được kết quả đã chạy và truy được báo cáo gốc. Đây là gói dữ liệu và hướng dẫn đối chiếu; mã thực thi đầy đủ nằm trong repository đã backup: https://github.com/jkay2005/nt409-task-placement.

**Không cần chạy lại các notebook để sử dụng gói này.** Giải nén vào một thư mục riêng, mở tài liệu này trước. Notebook được giữ để đọc mã và output; khi cần tái chạy một study, dùng môi trường và workflow trong repository đầy đủ.

## 1. Người nhận bắt đầu ở đâu?

| Tệp/thư mục | Dùng để làm gì? |
|---|---|
| `tables/instance_registry.csv` | Danh sách 14 input, vai trò, đường dẫn, hash, kích thước và optimum tham chiếu |
| `data/instances/` | Bốn JSON hai host nguyên bản |
| `data/benchmarks/nt409_three_host_v2/instances/` | Mười JSON ba host nguyên bản |
| `data/benchmarks/` | Manifest và protocol cố định cho từng study |
| `tables/a_campaigns.csv` | Bảng ngắn về bốn campaign QAOA chính: Notebook 16, 17, 19, 20 |
| `tables/a_groups.csv` | 42 nhóm instance/encoding/p: 36 nhóm đối chiếu chính và 6 nhóm development |
| `tables/a_runs.csv` | 196 lượt được xuất thống nhất: 192 lượt benchmark/development/test và 4 lượt control |
| `tables/a_controls.csv` | 32 dòng đối chứng xác suất giải tích; không phải số lượt solver cổ điển đã chạy |
| `tables/a_classical_timings.csv` | 38 dòng đo exact enumeration/random assignment đã có, kèm notebook nguồn và phạm vi đo |
| `tables/exact_reference.json` | Tham chiếu vét cạn để chấm đầu ra sau khi solver chạy |
| `data/reference_results/` | ZIP gốc và các bảng/JSON/ảnh xuất từ Notebook 16–20; ZIP lịch sử Notebook 12–15 |
| `archives/notebooks06_11_repository_snapshot.zip` | Bản gom mới của các báo cáo lịch sử Notebook 06–11 hiện có trong repository |
| `notebooks/` | Notebook 06–20 và các biến thể choice/reference đã lưu output |
| `docs/nt409_phase4_branch_a_summary_and_glossary_vi.md` | Tổng kết toàn Phase 4, công thức, ký hiệu và thuật ngữ đã viết |
| `templates/classical_results_pending.csv` | Mẫu nhận kết quả FF/BFD/MILP; mọi hàng đều `pending`, chưa phải bằng chứng đã chạy |
| `tables/archive_registry.csv` | Danh sách 10 archive, nguồn gốc và SHA-256 |
| `SHA256.json`, `verify_handoff.py` | Kiểm tra tính toàn vẹn và số liệu tổng hợp của gói |

B đọc mục 2, 3, 6 và 7, rồi lấy input JSON. C đọc mục 4, 5 và 8, rồi dùng các bảng tổng hợp cùng báo cáo gốc. Người trình bày A đọc bản tổng kết và thuật ngữ trong `docs/`.

## 2. Một bộ dữ liệu cố định cho mọi phương pháp

Các thuật toán dùng đúng JSON theo `input_path` trong registry; giữ nguyên ID, tài nguyên và thứ tự task/host. Một bộ chung gồm nhiều instance, không có nghĩa mọi instance phải có cùng kích thước.

| Tập | Instance | Vai trò |
|---|---|---|
| Hai host | `p1_choice`, `p1_tight`, `p0_reference` | Ba instance đối chiếu chính của Notebook 16–18; đã được dùng trong thăm dò, không gọi là test độc lập |
| Hai host | `p1_infeasible` | Control vô nghiệm, ngoài xếp hạng chất lượng |
| Ba host | `a3_dev_n4`, `a3_dev_n5` | Development của Notebook 19; không gộp vào test |
| Ba host | `a3_test_n4_1`, `a3_test_n4_2`, `a3_test_n4_3` | Ba instance test: 4 task, 3 host |
| Ba host | `a3_test_n5_1`, `a3_test_n5_2`, `a3_test_n5_3` | Ba instance test: 5 task, 3 host |
| Ba host | `a3_one_host`, `a3_infeasible` | Control optimum=1 và control vô nghiệm; ngoài xếp hạng |

**Bảng đối chiếu chính có 9 instance.** So A với B trên cùng instance và cùng hash; báo riêng các nhóm hai/ba host. Bốn task/hai host và năm task/ba host không phải thí nghiệm chỉ thay một yếu tố.

Hash input dùng JSON canonical: `sort_keys=True`, `ensure_ascii=False`, `separators=(",", ":")`, `allow_nan=False`, UTF-8. Khác cách thụt lề hoặc LF/CRLF không đổi hash canonical; thay giá trị hoặc thứ tự mảng làm đổi hash. `SHA256.json` ở cấp gói dùng hash **bytes** để giữ nguyên bản bàn giao.

Optimum của các instance: choice=1 host; tight/reference=2; cả sáu instance test ba host=2; one-host control=1; hai control vô nghiệm không có optimum. Registry và exact reference ghi chi tiết số assignment khả thi/tối ưu.

## 3. Protocol nào là bản đã chạy?

| Study | Protocol/đặc tả cần dùng |
|---|---|
| Notebook 16 | `data/benchmarks/nt409_benchmark_v1_1/manifest.json`, `protocol.json`; `docs/benchmark_a_protocol_v1_1.md` |
| Notebook 17 | Cùng input hai host; `docs/two_host_encoding_protocol.md`, campaign/config trong archive 17 |
| Notebook 18 | `docs/branch_a_summary_protocol.md`; tổng hợp 16/17 và đo đối chứng, không huấn luyện QAOA mới |
| Notebook 19 | `data/benchmarks/nt409_three_host_v2/manifest.json`, `protocol.json`; `docs/three_host_study_spec.md` |
| Notebook 20 | `data/benchmarks/nt409_three_host_test_v1/protocol.json`, `docs/three_host_test_protocol.md` và `frozen_context.json` trong kết quả 20 |

Các protocol lịch sử có thể còn chuỗi `frozen_design_not_executed`, `requires_new_runner_implementation` hoặc `test_campaign_started:false`: đó là nội dung đã khóa trước chạy. **Không sửa các chuỗi này để làm đẹp trạng thái.** Trạng thái thực thi đọc từ campaign, CSV và summary trong kết quả gốc. Đặc tả chung v1 là tài liệu trước v1.1 và trước phần mở rộng ba host; không dùng các giới hạn cũ của nó thay protocol 20.

Cấu hình chính: mean-energy, X mixer, Hamiltonian max-abs, COBYLA cap200, training/final 1024 shots, final seed riêng, p=1/2/3. Hai host dùng penalty3/3; ba host dùng domain/capacity penalty4/4. Năm seed chính không phải năm điểm khởi tạo: các seed dùng cùng điểm đầu. Development 19 chỉ có hai seed; p được báo ngang nhau, không chọn một p sau khi xem test.

Notebook 16: one-hot, 20/18/23 qubit. Notebook 17: một bit chọn host/task, 16/14/19 qubit trên đúng input cũ. Ba host: hai bit domain-wall/task, giữ y/slack, các instance test có 20/22/22/24/24/25 qubit. Giảm register thay Hamiltonian và phân bố đối chứng; không quy toàn bộ cải thiện cho riêng số qubit.

## 4. Kết quả A đã chốt

| Notebook | Tập đánh giá | Batch có nghiệm khả thi | Batch có nghiệm tối ưu |
|---|---|---:|---:|
| 16 | 45 lượt hai host, one-hot | 29/45 | 24/45 |
| 17 | 45 lượt hai host, mã hóa gọn | 45/45 | 45/45 |
| 19 | 12 lượt development ba host | 12/12 | 8/12 |
| 20 | 90 lượt test ba host | 90/90 | 63/90 |

Các control và probe nằm ngoài mẫu số này. Notebook 18 là tổng hợp của 16/17, không cộng thêm 90 lượt QAOA vào số thí nghiệm. Không gộp development 19 với test 20. Không dùng các lượt thăm dò 06–15 như các lần xác nhận độc lập của campaign cuối.

Trong Notebook 20, 63 đầu ra dùng 2 host và 27 đầu ra dùng 3 host, trung bình 2,3 host. Đây là chất lượng quan sát trên sáu case, không là bảo đảm tỷ lệ xấp xỉ cho mọi input. p1/p2/p3 có lần lượt 17/30, 24/30, 22/30 batch tối ưu; p2 tốt nhất theo chỉ số này trong dữ liệu đã chạy, chưa chứng nhận p2 tốt nhất tổng quát.

Hai host 17 đạt 45/45 optimum nhưng lấy mẫu đều trong mã hóa gọn cũng đã có xác suất batch thành công gần 100%. Ba host 20: 15/18 nhóm có lift trung bình >1 so với uniform encoded; cả 18 nhóm có P_opt trung bình thấp hơn structured random placement. Điều đó **chưa chứng minh ưu thế chất lượng hoặc tốc độ so với phương pháp cổ điển**. FF/BFD/MILP của B chưa nằm trong bằng chứng A.

## 5. Đọc đúng các chỉ số

Các cột xác suất trong CSV là số từ 0 đến 1; nhân 100 để viết phần trăm. Ô trống là thiếu/không áp dụng, không tự đổi thành 0. `True/False` là boolean ghi dạng chữ.

| Thuật ngữ/cột | Cách hiểu |
|---|---|
| `selected_objective` / số host | Mục tiêu gốc của placement hợp lệ do thuật toán trả về |
| `sample_mean_energy` | Trung bình năng lượng QUBO, có các penalty; không cùng đơn vị ý nghĩa với số host |
| `feasible_probability` | Tỷ lệ shot cuối giải mã thành placement hợp lệ, giữ nguyên bit/y |
| `optimal_probability` / P_opt | Tỷ lệ shot cuối có placement hợp lệ với số host bằng optimum tham chiếu |
| `ground_probability` | Tỷ lệ shot cuối ở ground QUBO; còn phụ thuộc slack, không đồng nhất với P_opt |
| `found_optimal` | Lượt có ít nhất một placement tối ưu trong batch cuối; không cần 1024 shot đều tối ưu |
| `observed_batch_success` | Số lượt có optimum / số lượt trong nhóm; mỗi nhóm chính có 5 seed |
| `lift_encoded` | P_opt trung bình / P_opt của uniform encoded trên đúng mã hóa đó |
| `lift_random_assignment` | P_opt trung bình / P_opt của chọn host đều cho từng task, y suy từ host được dùng |
| `optimality_gap` | Số host đầu ra hợp lệ trừ optimum; không có gap cho đầu ra invalid hoặc input vô nghiệm |
| `optimizer_success` | Trạng thái dừng của COBYLA; không chứng nhận nghiệm placement tối ưu toàn cục |
| `mean_selected_objective_valid_only` | Trung bình trên các lượt có đầu ra hợp lệ; phải đọc cùng `valid_batches/runs` để không bỏ qua thất bại |

Đầu ra A là **best-valid trong batch cuối**, không sửa bit/slack/y để cứu nghiệm. Mode và các trường hợp đồng hạng được giữ trong báo cáo gốc. Quy tắc này khác lấy bitstring phổ biến nhất trong proposal và đã được công bố.

Uniform encoded và random assignment là hai đối chứng khác nhau. Xác suất thành công batch của các đối chứng là kỳ vọng giải tích, không phải các lượt FF/BFD/MILP đã thực chạy. Không lấy P_opt trung bình của nhiều mạch QAOA rồi dùng công thức IID để suy ra tỷ lệ batch của QAOA; dùng số batch thành công thực tế.

Năm seed lồng trong một instance; 90 lượt không phải 90 instance độc lập về độ khó. SD trong bảng mô tả biến thiên theo seed. Nếu C cần khoảng tin cậy qua instance, dùng phân tích theo instance/cụm và nêu chỉ có sáu test instance; không gọi SD hiện có là khoảng tin cậy.

## 6. Quy tắc chấm đầu ra cổ điển

B giải bài toán nguyên thủy từ JSON: mỗi task đúng một host; tổng CPU/RAM không vượt capacity; mục tiêu min số host bật. Không cần dùng qubit, slack hoặc minimization energy để làm FF/BFD/MILP.

Placement vector dùng thứ tự `tasks` trong JSON; phần tử là chỉ số host bắt đầu từ 0 theo thứ tự `hosts`. Ví dụ input hai host có bốn task: `[0,1,0,1]` đặt task thứ nhất/thứ ba lên host đầu tiên. Khi thuật toán đổi thứ tự xử lý task, phải ánh xạ đầu ra về thứ tự gốc.

Heuristic chỉ trả placement thì y được suy từ các host có task, đúng `evaluate_placement` trong `src/placement.py` của repository. Nếu solver trả x/y tường minh thì dùng `evaluate_model`, giữ y solver trả; không tự tắt host dư rồi ghi đó là objective gốc. QAOA giữ nguyên y đã đo.

Failure/timeout/no-incumbent phải được giữ trong bảng; không bỏ task. Heuristic không tìm được placement hoặc QAOA không thấy mẫu khả thi không chứng minh input vô nghiệm. Với MILP, ghi riêng trạng thái proven infeasible hoặc chứng nhận optimal; không suy từ timeout. Tệp exact reference là để kiểm tra **sau** solve, không đưa optimum/placement tối ưu vào solver.

## 7. B cần trả lại những gì?

Mẫu `templates/classical_results_pending.csv` có 36 hàng: 9 instance chính ×3 thuật toán, cộng 3 control ×3 thuật toán. Hai development instance được giữ để truy lịch sử, không bắt buộc chạy baseline trong bảng test. Mẫu hiện tại hoàn toàn `pending`; gói này không triển khai hoặc gửi thông báo cho B.

Các quy tắc FF/BFD/MILP đã có trong mục 4 của `docs/unified_benchmark_v1.md`, áp dụng cho từng input nguyên thủy kể cả ba host. Nếu B đã dùng định nghĩa BFD khác, ghi cấu hình rõ và xử lý sự khác biệt trước khi C gộp bảng; không đổi nhãn mà bỏ qua khác biệt.

- First-Fit: thứ tự task/host gốc, chọn host đầu tiên còn đủ cả CPU/RAM; task không đặt được thì failure.
- BFD: sắp giảm theo max(cpu/Cmax, ram/Rmax), hòa giữ thứ tự task gốc; ưu tiên host đang bật; chọn tổng tỷ lệ CPU/RAM dư sau đặt nhỏ nhất, hòa theo thứ tự host gốc.
- MILP: cùng x/y và ràng buộc gốc, solver/version/options được ghi; protocol baseline đặt time limit600s, một thread. Ghi incumbent/bound/gap khi có và chứng nhận của solver.

B ghi status, placement, y nếu có, objective đã validate, thời gian cùng phạm vi đo, môi trường/solver version/options và đường dẫn báo cáo gốc. Nếu deterministic, một nghiệm chất lượng/instance là đủ; lặp timing không thành nhiều seed chất lượng. Những trường chứng nhận không áp dụng cho heuristic để trống.

## 8. C tổng hợp như thế nào?

Ghép bảng bằng `instance_id` **và** `input_canonical_sha256`. QAOA giữ encoding và p trong khóa nhóm; báo đủ p1/p2/p3. Không chọn p đẹp nhất trên test rồi gọi đó là lựa chọn đăng ký trước. Báo hai host và ba host riêng; development/control không tham gia xếp hạng.

Bảng đề xuất: instance, phương pháp/encoding/p, coverage, tỷ lệ đầu ra khả thi, tỷ lệ batch đạt optimum nếu có, số host/gap của đầu ra hợp lệ và phạm vi thời gian. Deterministic baseline trả một placement thì ghi kết quả đó; không đặt một P_opt mỗi shot giả vào cột xác suất của QAOA. Nêu rõ best-valid của A và output rule của baseline.

Thời gian QAOA theo trial gồm tối ưu, lấy mẫu cuối và hậu xử lý; preparation/probe/audit/export được ghi riêng trong campaign. Classical timing 18/20 là warm-process, loại import/calibration/preparation tham chiếu; có validation/checking/output. Những phép đo này không đủ cho một tỷ số tăng tốc end-to-end công bằng.

Bảng timing giữ cả các phép đo trên input test đã được Notebook 19 chuẩn bị trước campaign 20. Cùng instance/method xuất hiện ở hai notebook là hai phép đo khác phiên; giữ `source_notebook` trong khóa và không tự gộp chúng thành những lần đánh giá chất lượng độc lập.

Notebook 20 giữ thời gian trial tổng 12.212,19s và thời gian tính vào ngân sách campaign 12.515,77s. Người chạy báo máy có sleep; một trial có khoảng trống log khoảng32,1 phút. Không trừ toàn bộ khoảng trống này như thời gian sleep chính xác và không gọi tổng thời gian là compute thuần. Không cần chạy lại quality. Nếu sau này có benchmark timing riêng, gắn study/version riêng và giữ số đo gốc.

Kết luận được phép: giảm qubit trong mã hóa hai host đi cùng cải thiện thành công quan sát; QAOA ba host tìm optimum ở63/90 batch; energy giảm chưa bảo đảm placement tốt hơn; chưa thấy ưu thế so với structured random/exact trên các case nhỏ. Kết luận chưa được hỗ trợ: QAOA thắng FF/BFD/MILP, quantum advantage, scalability tổng quát, hoặc25 qubit là trần vật lý laptop.

## 9. Truy báo cáo gốc và kiểm tra gói

Mỗi hàng `tables/a_runs.csv` có `source_archive_path` và `raw_report_member`. Mở ZIP tương ứng, đọc report ở member đó. Hai trường này cùng nhau định danh bằng chứng; `report` là đường dẫn bên trong archive, không phải một tệp đã giải nén sẵn cạnh CSV. Campaign và source/runtime trong archive là nguồn gốc của lượt chạy. Các hàng 16/17 được Notebook 18 xuất lại để đối chiếu, không phải các lượt huấn luyện mới.

Archive 16–20 giữ checksum nội bộ và được kiểm tra lại lúc đóng gói. Archive 12–15 và snapshot mới của 06–11 được kiểm tra CRC và hash bytes ở cấp gói; không tuyên bố chúng có một checksum nội bộ vốn không tồn tại. Hồ sơ audit 20 đầy đủ nằm trong `docs/nt409_notebook20_windows_review_20261013.md`; gói bàn giao không thực hiện lại quantum training.

Trong terminal, chuyển vào thư mục giải nén rồi chạy:

```powershell
python verify_handoff.py
```

Chỉ cần Python tiêu chuẩn. Lệnh kiểm tra hash mọi tệp đóng gói, hash canonical của14 input, optimum bằng vét cạn nguyên thủy, checksum các archive chính và tổng hợp192 lượt chính/development cùng4 control. Một lần kiểm tra PASS xác nhận dữ liệu bàn giao nhất quán; không chứng nhận thuật toán có lợi thế.

Kiểm tra trước khi chỉnh sửa. Khi điền kết quả cổ điển, tạo bản sao template ở ngoài phần dữ liệu đã khóa; sửa bản gốc sẽ khiến kiểm tra hash báo thay đổi.

Notebook 06–15 và các tài liệu cũ được giữ để truy lại quyết định. Bản tổng kết Phase 4, protocol từng study và kết quả cuối có ưu tiên khi đọc trạng thái hiện tại; các mục còn `pending` trong kế hoạch lịch sử không thay trạng thái campaign đã hoàn tất.

## 10. Điều kiện để A bàn giao xong

Gói có input/protocol cố định, bảng per-run và per-group, raw archive, hướng dẫn chấm và kiểm tra PASS. A đã chuẩn bị xong phần này; việc người khác nhận gói hoặc hoàn thành FF/BFD/MILP không được tự đánh dấu. User đã báo backup Git xong, hash commit Windows đó không được tự suy bằng hash checkout dùng để chuẩn bị gói.

Việc tiếp theo của A là chuẩn bị trình bày từ bản tổng kết. Phần đối chiếu đầy đủ đề bài chờ kết quả B trên đúng dữ liệu và phần tổng hợp C. Theo quyết định hiện tại, không mở thêm thí nghiệm QAOA hoặc khảo sát trần RAM laptop.
