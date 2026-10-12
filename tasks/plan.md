## Kế hoạch hiện hành — chỉ nhánh A, protocol v1.1 (10/10/2026)

Yêu cầu mới nhất của Khiêm: thực hiện A, không triển khai hoặc chờ B/C. Phần
này có ưu tiên so với các kế hoạch lịch sử bên dưới. Dùng cùng bốn input v1;
phụ lục `docs/benchmark_a_protocol_v1_1.md` nâng riêng QAOA time guard lên2400
cho mọi p sau probe tài nguyên, giữ bản v1. Hướng dẫn: `docs/benchmark_a_runbook.md`.

### U1 — Thiết kế cố định: hoàn tất
Ma trận45 = choice/tight/reference × p1/2/3 × seed70–74. Mean/P3/max_abs,
cap200/shots1024 và final seed riêng. Một negative smoke ngoài45. Manifest
v1.1 khóa cả đặc tả mới và đặc tả kế thừa; input giữ nguyên hash. Không tái sử
dụng kết quả06–15 làm45 lượt xác nhận.

### U2 — Triển khai/kiểm chứng phần A: hoàn tất
Hai module benchmark_a,13 kiểm thử mới và Notebook16 có probe lớp sâu,
resource/time status, lưu nguyên attempts, khóa theo campaign, recovery,
resume và export. Đã đạt87 kiểm thử Linux; probe9 tổ hợp18/20/23 qubit; một
lượt p3 reference cap200 hội tụ sau53 đánh giá. Notebook kiểm tra bằng Python
không giao diện Jupyter, gồm đường partial. Kết quả kiểm chứng phần mềm nằm
ngoài campaign Windows chính thức. Máy Windows vẫn phải probe trước chạy.

### U3 — Campaign A trên máy Khiêm: đang chờ thực nghiệm
Chạy Notebook16 trong nt409-khiem, có thể chia phiên theo instance bằng cùng
RESUME_DIR. Nghiệm thu đủ45 completed + negative-control riêng, nguồn mẫu,
seed, config, hash và output rule khớp; giữ0 nghiệm và mọi failure/interrupt.
Thiếu lượt thì PARTIAL, không sửa ngân sách giữa campaign hoặc chọn lại seed.

### U4 — Review và đóng phần A: đang chờ U3
Review ZIP và notebook executed; bảng theo instance/p/seed, tỷ lệ khả thi/tối
ưu, output/mode đồng hạng, chi phí và giới hạn. Đóng A sau review đủ dữ liệu;
không mở sweep mới vì kết quả thấp. B/C không là dependency của đợt này.
Không đồng nhất hoàn tất A với hoàn tất toàn bộ đề tài hay thực nghiệm8/4.

**English:** A only. Implementation and Linux verification are complete;
Windows preflight,45 formal runs and final A review remain pending. v1.1
changes the QAOA time guard uniformly to2400 seconds, retaining v1 provenance.

---

> **English version below.**

## Lưu trữ — kế hoạch benchmark v1 trước yêu cầu chỉ làm A

Theo yêu cầu thống nhất từ đầu của Khiêm, kế hoạch này thay phương án 35 lượt/5 task/classical 8/4 trước đó. Dữ liệu gốc và các mốc lịch sử dưới đây giữ nguyên.

Tài liệu chuẩn: [unified_benchmark_v1.md](../docs/unified_benchmark_v1.md). Manifest/protocol: `data/benchmarks/nt409_benchmark_v1/`.

- Một bộ cố định cho mọi phương pháp: choice/tight/reference (benchmark), infeasible (kiểm tra chức năng riêng). Tất cả 4 task/2 host; QAOA 18–23 qubit.
- QAOA sampled mean/P3/max_abs, p1/p2/p3, 5 seed 70–74, final seed 100070–100074, shots1024/cap200/timeguard600: **45 lượt**. Không ghép kết quả notebook 06–15 vào ma trận này.
- FF/BFD/MILP dùng đúng hash input, validator/output/algorithm rules trong protocol; baseline đã có chỉ dùng lại sau kiểm tra khớp. B/C chưa được xác nhận hoàn tất/đã nhận gói.
- Giữ chính sách RAM 28 GB: available>=8 GiB trước chạy, reserve>=4 GiB, ngưỡng RSS Python4 GiB, Aer2048 MiB/4 threads, chạy tuần tự; runner mới còn cần triển khai các kiểm tra.
- Bỏ mở rộng 5 task và 8/4 khỏi nghiệm thu hiện tại; công bố thay đổi phạm vi proposal. Không xóa báo cáo cũ hoặc thay mã mô hình đã kiểm chứng.

### U1 — Khóa đầu vào và protocol
Nghiệm thu: manifest/version/hash của 4 JSON và protocol khớp; mỗi phương pháp cùng input; số qubit và optimum nhỏ được kiểm tra. Xác minh bằng JSON canonical, build_qubo và liệt kê placements. Tệp: manifest.json, protocol.json, docs/unified_benchmark_v1.md. Đã hoàn tất chuẩn bị, chưa xác nhận B/C/GV tiếp nhận.

### U2 — Bộ chạy chung và probe
Nghiệm thu: đọc manifest, từ chối mismatch; ghép đúng 45 cấu hình; tài nguyên/timeout có status riêng; start-state p1/p2/p3 tương đương, sampling cuối độc lập và resume đúng. Xác minh fixture nhỏ, probe lớp sâu hoạt động và test guard bằng số đo giả. Phụ thuộc U1. Tệp dự kiến: module campaign mới, tests và notebook chính thức; chưa triển khai.

### U3 — Campaign chính thức và baseline
Nghiệm thu: có trạng thái/nguồn của 45 lượt QAOA, ba baseline trên cùng 3 input, negative-control riêng; không loại thất bại. Xác minh report/counts/input hashes, output validation, source/runtime và bảng notebook. Phụ thuộc U2; B có thể chuẩn bị code baseline song song nhưng không chạy nặng cùng QAOA trên cùng máy. Tệp: reports/manifests và bảng tổng hợp.

### U4 — Tổng kết và đóng Phase 4
Nghiệm thu: bảng cùng instance, gap đúng, failures retained, chi phí tách preprocessing/solver/postprocessing và total; mode/best-valid và sampled/exact được phân biệt; giới hạn phạm vi công bố. Xác minh nguồn dữ liệu và gói tái lập. Phụ thuộc U3. Tệp: docs, README, bảng/biểu đồ và gói bàn giao. Không yêu cầu QAOA thắng baseline.

Checkpoint sau U2: probe RAM/p3 đạt trước campaign. Checkpoint U4: đủ nghiệm thu hoặc công bố phần bị chặn, không tự mở thêm sweep.

**English update:** One frozen suite and protocol supersede the prior 35-run plan. Three feasible instances are shared by all solvers; one infeasible fixture is a separate functional check. The 45-run sampled QAOA matrix is p1/p2/p3 by five paired seeds by three inputs. Historical notebooks remain exploratory. The new runner and formal campaign are pending.

---

# Kế hoạch nhánh A: penalty, độ sâu và chẩn đoán hội tụ

Cập nhật ngày 07/10/2026. Nhánh A: Khiêm phụ trách QUBO/Ising/QAOA; B: First-Fit, Best-Fit Decreasing, MILP; C: tổng hợp số liệu và báo cáo. B/C đã nhận bàn giao ban đầu. Việc họ nhận các báo cáo mới hoặc hoàn tất baseline chưa được xác nhận.

## Mốc đã kiểm chứng

- A1: 18 lượt Windows, P=3, p=1, hai khởi tạo và seed 42/43/44; gồm 12 lượt tight/choice và 6 lượt reference. Mẫu thô đã được review; tài liệu và PDF A1 đã được tạo.
- Khảo sát P chung: 60 lượt tight/choice trong campaign_20261005T084248968346Z.json và 30 lượt reference trong campaign_20261005T100508165284Z.json. Cả hai chỉ mục nằm trong data/reference_results/phase4a_penalty_runs/; đường dẫn báo cáo nguồn được ghi trong từng chỉ mục.
- Đã kiểm tra đủ 90 báo cáo mới: input/config/hash/run key; giải mã x/y, dung lượng, mục tiêu; công thức bình phương, QUBO, Ising; số mẫu, metrics, đồng hạng và bảng notebook.
- Reference: 21/30 lượt có nghiệm; 33/30.720 mẫu hợp lệ, đều tối ưu 2 host; không có mẫu đạt cực tiểu toàn bộ QUBO. P=1 và P=5 đều đạt 6/6 lượt, nhưng chỉ có 12 và 9 mẫu hợp lệ. Tỷ lệ gộp đợt reference 0,107422% gần mức lấy mẫu đều 0,097656%; đây không phải xác suất của một cấu hình cố định.
- Thời gian QAOA reference: tổng 495,498 giây, từng lượt 14,292–29,221 giây; giải mã 44,860 giây; chẩn đoán 4,868 giây. RSS đỉnh kernel được báo cáo 311,438 MiB; phép đo là đỉnh vòng đời tiến trình, có thể gồm hoạt động kernel trước đó.
- P=3 ở cả hai campaign mới tái lập các metrics A1 với cùng input/config/seed. Không cộng A1 và các đối chứng P=3 mới thành những lần lặp độc lập.

Hoàn tất ma trận P chung đã định nghĩa. Đây là lát cắt hai hệ số bằng nhau, chưa hoàn tất nghiên cứu hai hệ số độc lập và p=1/2/3 trong proposal. Năng lượng trung bình giảm không đủ để kết luận xác suất nghiệm tối ưu đã tăng đáng kể.

Ngày 06/10: mô hình hai hệ số, báo cáo/chẩn đoán, manifest/resume và notebook 08 đã triển khai/kiểm chứng với 23 kiểm tra tự động và các lượt Aer rút gọn. Sau đó A chạy đủ 24 lượt Windows shots=1024/maxiter=35; campaign_20261006T080102274154Z.json đã được review toàn bộ 24.576 shots, đại số/QUBO/Ising, tham chiếu, metadata, tám đối chứng tái lập và bảng notebook.

Pilot penalty độc lập: choice có 12/12 lượt hợp lệ, 9/12 lượt tối ưu; 317 mẫu hợp lệ/12 mẫu tối ưu trong 12.288 shots. Reference có 7/12 lượt hợp lệ và tối ưu, 12 mẫu trong 12.288 shots. Không có ground state toàn bộ QUBO. (3,12) có 4 mẫu tối ưu choice, so với 3 của (3,3); reference có 4 mẫu, so với 5 của (1,1). Chưa kết luận cải thiện ổn định từ seed 42. QAOA tổng 209,225 giây; tổng solver/giải mã/chẩn đoán 245,503 giây; RSS đỉnh ghi nhận 309,012 MiB. Quy tắc best-valid là hậu xử lý; năm mode duy nhất đều không hợp lệ, 19 lượt có đồng hạng và phải công bố riêng.

Notebook 09 đã chạy/review đủ 20 lượt Windows seed 45–49, 20.480 shots; hai manifest confirmation_p1_choice_20261006T092857554634Z.json và confirmation_p0_reference_20261006T094118167230Z.json cùng các bảng notebook đều khớp dữ liệu nguồn. Choice (3,3): 100 mẫu hợp lệ/6 tối ưu, 4/5 lượt tối ưu; (3,12): 80/10, 4/5. Reference (1,1): 12 mẫu hợp lệ/tối ưu, 5/5 lượt; (3,12): 6 mẫu, 2/5 lượt. Không có mẫu ground state toàn QUBO. Năm mode duy nhất đều không hợp lệ; 15 lượt đồng hạng, best-valid vẫn là hậu xử lý. Chưa có bằng chứng dùng (3,12) cải thiện cả hai input.

Notebook 10 đã chạy/review đủ 30 lượt Windows/30.720 shots, seed 50–54, (3,3), p=1 và shots1024/maxiter35. Choice raw/matched/common có 5/6/10 mẫu tối ưu và 3/3/5 lượt thành công; reference có 4/4/3 mẫu và 3/4/2 lượt. Common giảm năng lượng trung bình khoảng 42,2%/49,7% nhưng chưa tăng xác suất tối ưu đồng thời. Reference/common/seed52 có một mẫu ground state E=2. Công thức, Ising/thang/gamma, nguồn mã, giải mã và các bảng đều khớp. Giữ kết luận thăm dò, không coi đây là phép so trực tiếp vượt cấu hình riêng của notebook 09.

Notebook 11 đã chạy/review đủ 20 lượt Windows, 20.480 shots, seed55–59, p1/p2 và shots1024/maxiter80. Choice p1/p2 có 107/137 mẫu hợp lệ, 12/8 tối ưu trong 5.120 shots mỗi nhóm và 5/5,4/5 lượt tối ưu. Reference có 6/4 mẫu hợp lệ/tối ưu, 3/5 lượt thành công ở cả hai nhóm. Không có ground state toàn QUBO. Bốn mode duy nhất đều không hợp lệ; 16 lượt đồng hạng. p2 giảm năng lượng nhưng chưa tăng xác suất placement tối ưu. Số đánh giá thực tế28–49, dưới cap80; đây chưa chứng minh đã hội tụ về nghiệm tối ưu.

Review lại Phase0–11: công thức/Ising/scaling/bit và các mẫu đo nhất quán. Đã replay lý tưởng tại20 bộ góc cuối; năng lượng batch cũ thấp hơn kỳ vọng chính xác ở cả20. Sampler dùng lại seed có thể lặp cùng counts, khiến batch cuối cũ chưa độc lập với training. Các kiểm tra góc gần nhau cho thấy nhiễu ảnh hưởng quỹ đạo. Đối chứng exact có giới hạn giảm năng lượng nhưng vẫn P_opt thấp, nên cần phân biệt nhiễu, hội tụ số học và chất lượng placement; chưa quy toàn bộ khó khăn cho một nguyên nhân hay kết luận p1 không thể giải.

## Quyết định cho đợt tiếp theo

Giữ dữ liệu và trình mô phỏng Aer CPU hiện tại. Thay đổi một yếu tố nghiên cứu tại một thời điểm. Chọn cấu hình theo tỷ lệ khả thi, xác suất placement tối ưu, tỷ lệ lượt thành công và chi phí; không chọn theo năng lượng thô giữa các mô hình khác penalty. P=1 là đối chứng thực nghiệm đáng chú ý trên reference; P=3 là đối chứng có bảo đảm đủ mạnh cho các mô hình 2 host với dữ liệu nguyên. Các cực tiểu của cả năm P đang dùng đã được kiểm chứng hợp lệ trên ba fixture khả thi; điều này không chứng minh P=1 đủ cho mọi input.

## Task 1 — Mô hình hai hệ số phạt độc lập

Giữ mục tiêu số host, biến x/y/slack và ánh xạ qubit. Năng lượng mới: số host + lambda_assign × sai số gán task + lambda_capacity × sai số phương trình tài nguyên. Mặc định và lời gọi P chung cũ tiếp tục hoạt động; khi hai hệ số bằng nhau phải tái tạo mô hình cũ. Không tạo notebook thí nghiệm lớn trước khi mô hình được kiểm chứng.

Tiêu chí nghiệm thu:
- [x] Kiểm tra hai hệ số dương, hữu hạn; thứ tự biến không đổi; lambda_assign=lambda_capacity=P cho cùng hệ số QUBO như trước.
- [x] Công thức độc lập, QUBO và Ising bằng nhau trên các vector kiểm chứng; routine tham chiếu xử lý đúng hai hệ số. Với các cặp được chọn, kiểm tra mọi cực tiểu trên fixture khả thi và xử lý đúng fixture vô nghiệm.
- [x] Kiểm tra hồi quy các fixture hiện có; min(lambda_assign, lambda_capacity)>2 giữ bảo đảm đủ mạnh cho 2 host và sai số nguyên khi bài toán có nghiệm.

Xác minh: các kiểm tra mô hình có ý nghĩa và nghiệm tham chiếu; không cần chạy QAOA dài để kiểm tra đại số. Phụ thuộc: mốc P chung đã review. Tệp dự kiến: src/qubo.py và tests/test_qubo_penalties.py. Phạm vi: nhỏ.

## Task 2 — Báo cáo và chẩn đoán có hai hệ số

Cập nhật runner/chẩn đoán để ghi riêng hai hệ số, phiên bản mô hình, cấu hình, tham số theo tên và nguồn mã. Run key/resume phải phân biệt hai hệ số. Báo cáo cũ giữ nguyên và tiếp tục đọc được.

Tiêu chí nghiệm thu:
- [x] Năng lượng trung bình tái dựng bằng số host trung bình + lambda_assign × mean_assignment_error + lambda_capacity × mean_capacity_equation_error.
- [x] Placement khả thi/tối ưu được chấm từ bit đo thật; ground state dùng toàn bộ bit; không sửa slack hoặc task trước khi chấm. Đồng hạng, thiếu nghiệm và mục tiêu không tồn tại được biểu diễn rõ.
- [x] Lưu số lần đánh giá, thời gian solver/giải mã, RAM và hai penalty; resume không trộn mô hình/cấu hình khác nhau.

Xác minh: kiểm tra report và resume trên lượt Aer ngắn, cùng hồi quy báo cáo P chung. Phụ thuộc: Task 1. Tệp: src/qaoa_experiment.py, src/penalty_analysis.py, src/independent_campaign.py và kiểm tra liên quan. Phạm vi: vừa; đã triển khai/kiểm chứng.

## Task 3 — Notebook 08: khảo sát hai penalty có giới hạn

Thực hiện pilot trên p1_choice và p0_reference; p1_tight dùng kiểm tra hồi quy. Giữ p=1, shots=1024, maxiter=35, hai khởi tạo và tài nguyên như đối chứng. Ma trận hiện đã chuẩn bị: (1,1), (3,3), (12,3), (30,3), (3,6), (3,12), theo thứ tự (lambda_assign, lambda_capacity). Bổ sung (1,1) và chạy lại cả hai đối chứng trong cùng bộ mã để có nguồn gốc trực tiếp; báo cáo cũ giữ làm mốc lịch sử, không cộng đối chứng cùng seed thành các lần lặp độc lập. Seed 42 cho pilot; đây là thăm dò, không dùng một seed để tuyên bố cấu hình thắng. Tổng mặc định: 2 instance × 6 cặp × 2 khởi tạo × 1 seed = 24 lượt.

Tiêu chí nghiệm thu:
- [x] Chuẩn bị/kiểm thử notebook: đo thử tài nguyên, chạy tuần tự, lưu từng lượt/manifest riêng, tiếp tục không chạy lại và giữ lượt hoàn tất có 0 nghiệm.
- [x] A chạy đủ 24 lượt pilot Windows mặc định và gửi notebook/manifest/báo cáo; đã review dữ liệu nguồn.
- [x] Bảng ghi sai số gán, tỷ lệ one-hot, khả thi/tối ưu, thành công theo lượt và chi phí. Sai số phương trình tài nguyên gồm cả slack sai, không được gọi toàn bộ là vượt dung lượng thật.
- [x] Chọn một cặp ứng viên (3,12) và cố định khởi tạo/đối chứng theo từng instance trước khi xem seed xác nhận.
- [x] Chuẩn bị notebook 09 và hướng dẫn song ngữ; kiểm thử 20 tổ hợp rút gọn, bảng ghép seed và resume.
- [x] A chạy/review xác nhận seed 45–49: choice 10 lượt và reference 10 lượt, p=1/shots=1024/maxiter=35. Giữ riêng pilot seed 42 và xác nhận.
- [x] Đóng ma trận penalty đã định; ghi nhận choice có tín hiệu hạn chế ở (3,12), reference ưu tiên (1,1). Bổ sung chẩn đoán cách tìm gamma với penalty chung trước p=2.

Xác minh: ma trận đầy đủ/duy nhất, bộ tổng hợp khớp báo cáo, và phân biệt seed chọn cấu hình với seed xác nhận. Kiểm tra seed mới chỉ đánh giá độ ổn định trên các fixture đang có, không chứng minh khả năng khái quát sang input mới. Phụ thuộc: Task 2. Tệp: notebooks/08_qaoa_independent_penalties.ipynb, notebooks/09_qaoa_penalty_confirmation.ipynb và các hướng dẫn tương ứng trong docs/. Phạm vi: pilot và xác nhận đã review đầy đủ.

## Task 3.5 — Notebook 10: thang Hamiltonian và khởi tạo với penalty chung

Giữ (3,3), p=1, shots=1024/maxiter=35/rhobeg=1; ba cấu hình đã ghi ở mốc trên. So normalized_matched với raw_original để kiểm tra đổi đơn vị/hình học tìm kiếm tại cùng trạng thái khởi đầu; so normalized_common với normalized_matched để kiểm tra đổi khởi tạo. Không chuẩn hóa từng phương trình tài nguyên hoặc sửa bit trước khi chấm.

- [x] Helper chuẩn hóa/quy đổi gamma, runner chấm năng lượng QUBO gốc, nguồn mã/thang/góc và manifest riêng.
- [x] Notebook/hướng dẫn song ngữ; 34 bài kiểm tra và 30 lượt Aer rút gọn, tiếp tục không chạy lại.
- [x] A chạy/review Windows: 15 lượt choice và 15 reference, seed 50–54; đủ 30.720 shots, manifest và bảng khớp.
- [x] Đánh giá riêng từng input; chọn thang chuẩn hóa/khởi tạo cố định cho phép so độ sâu, không tuyên bố cấu hình chung thắng reference.

Tệp: src/ising.py, src/qaoa_experiment.py, src/scaling_campaign.py, hai kiểm tra mới, notebooks/10_qaoa_hamiltonian_scaling.ipynb, docs/qaoa_hamiltonian_scaling.md. Phụ thuộc: Task 3. Source hash mới từ chối resume cũ theo thiết kế; dữ liệu đã hoàn tất của 08/09 tiếp tục dùng làm mốc. Không thêm dependency. Các cấu hình riêng tốt ở notebook 09 cần đối chứng cùng phương pháp/ngân sách nếu muốn tuyên bố một cách chung vượt chúng.

## Task 4 — Khảo sát độ sâu và ngân sách tối ưu

Notebook 11 giữ (3,3) và H_raw/kappa. p1 bắt đầu [0.3,1.0]; p2 nhúng [0.3,0,1.0,0], theo thứ tự beta0,beta1,gamma0,gamma1. Hai trạng thái đầu bằng nhau; góc lớp mới được tự do tối ưu. Không nhận nghiệm đã học từ một lượt p1 trước. Cả hai dùng shots1024/maxiter80, rhobeg1 và seed mới55–59. Mỗi input có 10 lượt ghép, cả hai 20. Đo p1/p2 và một mạch p2 có lớp mới hoạt động trước khi chạy; review rồi mới xét p3.

Tiêu chí nghiệm thu:
- [x] Chuẩn bị notebook11/module/tests/docs song ngữ; kiểm chứng trạng thái lớp0, bốn góc, lưu/resume và ngân sách ghép.
- [x] A chạy/review notebook11 Windows: 10 lượt choice, 10 reference, shots1024/maxiter80.
- [x] p1/p2 có đối chứng input/penalty/shots/seed/ngân sách, probe và dữ liệu nguồn đã xác minh.
- [x] So xác suất/tỷ lệ thành công/gap với thời gian/RAM; công bố mode, đồng hạng và best-valid riêng.
- [ ] Kiểm tra cấu hình được chọn bằng seed mới; không suy ra tăng p bảo đảm một lượt tối ưu hữu hạn tốt hơn. Nếu nghiên cứu có giới hạn không cải thiện, kết luận giới hạn đó và tiến hành so sánh baseline.

Xác minh phần mềm notebook11: 42 bài kiểm tra và20 lượt Aer Linux rút gọn đã đạt; sau đó đủ20 lượt Windows mặc định đã được review. Tệp: src/depth_campaign.py, src/qaoa_experiment.py, tests/test_depth_campaign.py, notebooks/11_qaoa_depth_comparison.ipynb và docs/qaoa_depth_comparison.md. Phụ thuộc: Task3.5. Chưa triển khai p3; làm Task4.5 trước để rõ tác động shots và optimizer.

## Task 4.5 — Notebook 12: mẫu cuối độc lập và đối chứng năng lượng chính xác

Giữ input choice/reference, penalty(3,3), p1, max_abs, rhobeg1/tol1e-4 và cap80. Hai khởi tạo cố định [0.3,1.0], [0.8,1.2]. Mỗi input có6 sampled (seed60/61/62) và2 exact (mỗi khởi tạo một tối ưu xác định),8 lượt tổng. Cả hai chấm placement từ1024 shots cuối bằng seed riêng. Đối chứng exact chỉ là mô phỏng lý tưởng để chẩn đoán, không phải baseline MILP hay lợi thế lượng tử.

- [x] Runner lấy mẫu cuối độc lập, ghi thống kê năng lượng và status/success/message/nfev của SciPy; giữ nguyên report lịch sử.
- [x] Oracle dùng vector số và Aer CPU, giới hạn23qubit; kiểm chứng độc lập công thức, thứ tự bit và scaling ở p1/p2.
- [x] Manifest riêng, ma trận6+2, kiểm tra/resume từ report nguồn; từ chối thay input/config/mã/phiên bản.
- [x] Notebook/hướng dẫn song ngữ; 59 bài kiểm tra và16 lượt Aer rút gọn trên20/23qubit đạt. Dữ liệu kiểm thử không thay benchmark Windows.
- [ ] A chạy đủ8 lượt choice rồi8 reference mặc định; cung cấp2 notebook có output,2 manifest và16 report nguồn.
- [ ] Review E_train/E_eval/E_exact, lý do dừng, P_opt/one-hot/mode/thành công và chi phí riêng; không yêu cầu mỗi cấu hình cải thiện.
- [ ] Chọn một bước tiếp theo có căn cứ: ngân sách/khởi tạo, phương pháp tối ưu chịu nhiễu, objective/mixer hoặc độ sâu; không thay tất cả yếu tố cùng lúc.

Tệp: src/qaoa_optimizer.py, src/qaoa_experiment.py, src/convergence_diagnostics.py, src/convergence_campaign.py, notebooks/12_qaoa_convergence_diagnostics.ipynb, docs/qaoa_convergence_diagnostics.md và3 kiểm tra mới. SciPy>=1.16,<2 được khai báo trực tiếp. Source hash mới từ chối resume cũ; kết quả hoàn tất của notebook11 giữ làm dữ liệu lịch sử. Đợt này là chẩn đoán thăm dò, không đủ để chứng minh ưu thế thống kê hoặc giới hạn phổ quát của p1.

## Task 5 — Đối chiếu B/C và chốt phạm vi báo cáo

B cung cấp FF/BFD/MILP trên đúng JSON đầu vào; A cung cấp campaign/report; C tổng hợp theo instance, penalty, p, khởi tạo, seed và nguồn dữ liệu. MILP là baseline của B; routine liệt kê nhỏ của A chỉ dùng kiểm chứng mô hình.

Tiêu chí nghiệm thu:
- [ ] C nhận đủ báo cáo nguồn/chỉ mục; A không tự đánh dấu việc gửi hoặc việc B/C hoàn tất khi chưa được xác nhận.
- [ ] Đáp án trả về được kiểm tra khả thi; gap bằng số host của nghiệm hợp lệ trừ số host tối ưu. Lượt không tìm được nghiệm được tính vào tỷ lệ thất bại, không bị loại khỏi mẫu thống kê.
- [ ] Công bố cả quy tắc lấy mẫu phổ biến nhất của proposal và quy tắc lọc chọn mẫu hợp lệ tốt nhất đang dùng; ghi rõ chi phí xây mô hình, tối ưu/lấy mẫu và hậu xử lý, cùng phạm vi tinh chỉnh.

Phụ thuộc: baseline B và kết quả A; C có thể tổng hợp mốc P chung ngay khi nhận đủ tệp. Không cần đợi QAOA thắng MILP để hoàn tất đồ án. Quy mô 8 task/4 host trong proposal chưa được mô phỏng ở mốc này; chỉ mở rộng sau đo số qubit và tài nguyên, ghi rõ giới hạn thực nghiệm.

---

# Branch A plan: penalties, depth and convergence diagnostics

Updated 7 October 2026. A owns QUBO/Ising/QAOA, B owns FF/BFD/MILP, and C owns analysis/reporting. Initial handoff is confirmed; delivery of later reports and completion of B/C work remain unconfirmed.

A1 comprises 18 reviewed Windows trials. The common-penalty study now has 90 reviewed trials: 60 tight/choice and 30 reference, with P=1,2,3,5,8, depth 1, 1024 shots, maxiter 35, two initial points and seeds 42–44. Reference has 21 successful trials and 33 feasible/optimal placements among 30,720 shots, with zero observed full-QUBO ground states. Its pooled placement rate is 0.107422%, close to the 0.097656% uniform baseline; pooling describes this campaign rather than a fixed configuration. P=1 and P=5 succeed in all six reference trials but provide only 12 and nine feasible shots. Solver time totals 495.498 s, decoding 44.860 s and diagnostics 4.868 s. Reported lifetime kernel peak RSS is 311.438 MiB. New P=3 controls reproduce A1 with identical settings/seeds and must not be counted as additional independent repetitions.

The defined common-P matrix is complete, while the proposal's independent penalties and depth study remain incomplete. Preserve the Aer CPU backend, fixtures and raw-sample scoring. P=1 is an empirical reference control; P=3 retains the sufficient integer-error guarantee for two hosts. Exact checks validate minima for all five common P values on the current feasible fixtures; this does not establish universal sufficiency of P=1.

The weighted model, reports/diagnostics, campaign resume and notebook 08 are implemented/verified with 23 automated tests and reduced-budget Aer checks. A then completed all 24 default-budget Windows pilot trials; campaign_20261006T080102274154Z.json was reviewed against every raw sample, formula/QUBO/Ising, reference, metadata, eight reproduction controls and notebook tables. Choice has 12/12 feasible and 9/12 optimal trials, 317 feasible/12 optimal shots out of 12,288. Reference has 7/12 feasible/optimal trials and 12 feasible/optimal shots out of 12,288. No full-QUBO ground state was observed. Pair (3,12) has four optimal choice shots versus three for (3,3), and four reference shots versus five for (1,1); a single seed does not establish stable improvement. Solver time totals 209.225 s, solver/decoding/diagnostics 245.503 s and recorded peak RSS 309.012 MiB. Best-valid postselection must be disclosed; all five unique modes are invalid and nineteen trials have frequency ties.

Notebook 09's twenty Windows trials (20,480 shots, seeds 45–49) and both confirmation manifests/notebooks are fully reviewed. Choice (3,3) has 100 feasible/six optimal shots and 4/5 optimal trials; (3,12) has 80/ten and 4/5. Reference (1,1) has twelve feasible/optimal shots and 5/5 trials; (3,12) has six and 2/5. No full-QUBO ground state was observed. All five unique modes are invalid and fifteen trials have frequency ties. A common (3,12) improvement is not supported.

Notebook 10 is fully reviewed: thirty Windows trials/30,720 shots, seeds 50–54, shared (3,3), depth1, shots1024/maxiter35. Raw/matched/common arms give 5/6/10 optimal choice shots and 3/3/5 successful trials versus 4/4/3 reference shots and 3/4/2 successes. Common initialization lowers mean energy by about 42.2%/49.7% without joint optimal-placement improvement. Reference/common/seed52 yields one full-QUBO ground-state sample of energy2. Sources, formula/Ising/unit/gamma, decoding, manifests and notebook tables agree. This remains exploratory and does not directly establish superiority over notebook09 per-instance settings.

Notebook11 is fully reviewed: twenty Windows trials/20,480 shots, seeds55–59, p1/p2, shots1024/maxiter80. Choice p1/p2 yields107/137 feasible shots,12/8 optimal shots and5/5,4/5 optimal trials. Reference yields6/4 feasible/optimal shots and3/5 successful trials in each arm. No full ground state is observed. Four unique modes are invalid and16 trials have ties. Actual optimizer evaluations28–49 are below the cap; stopping does not certify optimal placement.

The Phase0–11 review found consistent equations, Ising/scaling and measured bits. Ideal replays at all twenty final points exceed the old batch energies; same-seed sampler repetitions can reproduce identical counts. Training noise affects nearby-point comparisons, while bounded exact controls still show low P_opt despite lower energy. Separate measurement, initialization and numerical stopping before increasing depth; do not claim one universal cause or p1 impossibility.

## Ordered implementation tasks

1. **Independent penalties — implemented/verified:** introduce lambda_assign and lambda_capacity while preserving common-P behavior, variable order and default calls. Verify independent formula/QUBO/Ising equality, tiny exact references and infeasible handling. min(lambda_assign, lambda_capacity)>2 is sufficient for feasible two-host integer fixtures. Files: src/qubo.py and focused tests. Depends on the completed review.
2. **Reports and diagnostics — implemented/verified:** record both weights, model/source versions, named parameters, budget and resources; hash both weights in run keys and resume checks. Reconstruct weighted mean energy, preserve old reports, score only measured bits and distinguish placements from full ground states. Short Aer reports, archived common-P reports and resume checks pass. Includes src/independent_campaign.py. Depends on Task 1.
3. **Bounded penalty pilot/confirmation — reviewed:** the 24-trial seed-42 pilot and twenty-trial seed-45–49 confirmation are fully reviewed. Choice gives limited (3,12) signal, while reference favors (1,1); a universal (3,12) improvement is not established. Close the defined penalty grid and keep input-specific results. Common-P reproduction controls are not independent repetitions. Report one-hot/feasibility/optimality, success/costs and output-rule distinctions; resource-equation error includes slack. Depends on Task 2.
3.5. **Execution-scale/start diagnostic — fully reviewed:** thirty Windows runs, three arms/five seeds50–54, original-QUBO scoring and identical input/model. Common normalized initialization improves choice descriptively but not reference optimal sampling; one reference ground-state sample is not stable success. Use shared normalized coordinates as a fixed depth-study protocol, not a claimed universal winner. Sources/angles/raw samples/manifests/tables agree. Depends on Task3.
4. **Depth and optimizer budget — notebook11 fully reviewed:** fixed(3,3), max_abs, identical-state p1/p2 initialization, shots1024/maxiter80/rhobeg1 and paired seeds55–59. Twenty Windows reports and20,480 shots have been reviewed; lower energy does not establish better optimal sampling. Resources, actual evaluation counts and output ties are disclosed. p3 remains unimplemented; Task4.5 comes first.
4.5. **Convergence diagnostic — software implemented/verified, Windows execution pending:** independent final sampling and SciPy stopping metadata; ideal-expectation oracle with numeric vectors; separate manifest and strict resume. Fixedp1/P3/normalized coordinates, two fixed starts, six sampled and two deterministic exact optimizations per input, matched80-evaluation caps and1024 final shots. Fifty-nine tests and sixteen reduced-budget20/23qubit Aer trials pass; these are software checks rather than Windows quality data. A must run8+8 default trials and provide2 notebooks/2 manifests/16 reports. Review objective estimates, independent means, ideal P_opt, one-hot/output rules and separate costs before selecting one further change. New source hashes invalidate old resume; completed history is preserved. SciPy>=1.16,<2 is declared directly. This exploratory diagnostic does not establish significance or a universal p1 limit.
5. **B/C comparison:** use identical input JSONs and verified MILP ground truth, keep zero-solution trials in success-rate denominators, disclose postselection and separate model/solver/postprocessing/tuning costs. C may analyze the current campaign as soon as reports are delivered. Do not mark delivery or teammates' work complete without confirmation.

Fresh-seed validation measures stability on existing fixtures, not generalization to new inputs. Tiny exact enumeration is a model check rather than B's MILP baseline. The proposal's larger 8-task/4-host scale has not been simulated here; expansion requires explicit qubit/resource probing. Completing an honest comparison does not require QAOA to outperform MILP.
