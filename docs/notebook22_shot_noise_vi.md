# Notebook 22 v2: QAOA exact/shots trên một input cố định

## Quyết định và câu hỏi

Dùng duy nhất `a3_dev_n5` làm bộ quy chiếu cho các thí nghiệm hiện tại. Không luân phiên sang p1_choice, p1_tight hoặc input ba-host khác. Câu hỏi của bước này: cùng input, encoding, mixer, optimizer và điểm đầu, bỏ nhiễu lấy mẫu khi huấn luyện có tạo bộ góc cho P_opt cao hơn không?

Exact là kỳ vọng năng lượng của trạng thái QAOA hiện tại trên simulator. Nó vẫn dùng COBYLA tìm góc, không thay bằng bộ giải placement và không bảo đảm cực tiểu toàn cục. Không đo lợi thế tốc độ so với cổ điển trong thí nghiệm này.

Bản v2 thay gói Notebook 22 hai-host chưa chạy theo quyết định thống nhất một bộ quy chiếu. Notebook 12–14 và các campaign cũ chỉ là lịch sử tham khảo; không gộp kết quả khác encoding, protocol hoặc môi trường vào phép so sánh mới.

## Input được khóa

| Thành phần | CPU | RAM |
|---|---:|---:|
| Task t0,t1,t2,t3 — mỗi task | 1 | 1 |
| Task t4 | 1 | 2 |
| Host h0 | 2 | 2 |
| Host h1 | 3 | 3 |
| Host h2 | 3 | 3 |

Input là bản sao nguyên nội dung của a3_dev_n5 trong bộ ba-host hiện có, lưu riêng ở `data/benchmarks/nt409_shot_noise_v2/instance.json`. Thứ tự task/host giữ nguyên. Hash canonical input: `e6d3ac93ed2d5a831f5d7393750e9a1995b46fbe20d077058a629c7797996278`.

Vét cạn 3^5=243 cách gán task→host cho 8 cách hợp lệ dùng hai host, 82 cách dùng ba host; tối ưu là hai. Đây là chứng nhận bài toán và tiêu chuẩn chấm, không phải kết quả QAOA. Việc gán đều task→host khác lấy đều toàn bộ bit domain-wall, y và slack.

## Thiết kế thí nghiệm

| Thành phần | Thiết lập |
|---|---|
| Encoding | three_host_domain_wall_v2, binary slack; 25 qubit |
| Penalty | Domain-wall và capacity đều 4, theo builder ba-host hiện có |
| Mixer / scaling | X / max_abs; scale 65.5 |
| Độ sâu | p=1 và p=2, báo cáo riêng |
| Góc đầu | p=1: beta=[0.3], gamma=[1]; p=2: beta=[0.3,0], gamma=[1,0] |
| Optimizer | COBYLA; cap 200 lần gọi hàm; rhobeg=1; tol=1e-4 |
| Nhánh exact | 1 lượt/độ sâu, không lặp giả thành nhiều seed |
| Nhánh shots | 5 lượt/độ sâu; seed 300–304; 1024 shots/lần gọi |
| Hiệu chuẩn | 20 batch/độ sâu tại góc đầu, trước huấn luyện |
| Chấm cuối | Xác suất lý tưởng và một batch đo độc lập 1024 shots |

Tổng: **12 lượt tối ưu trên cùng một input**. Hai độ sâu không phải hai input độc lập; năm seed chỉ thay phép lấy mẫu, không phải multistart. QUBO được đối chiếu fingerprint trước chạy: `8fa77f91e277724277e5aaf4c1a29b5cec345e91e3660f13a6a166efc44fc515`.

Hai nhánh dùng một mạch compile chung cho mỗi độ sâu. Khác biệt chính là estimator huấn luyện: exact lấy probabilities, shots thực sự chạy mạch có đo trên Aer. Không thêm nhiễu Gaussian giả lập. COBYLA nhận `(mean_energy-offset)/scale`; chỉ năng lượng quyết định góc. Ground truth/P_opt không dùng chọn điểm đầu, chọn góc hoặc chọn lại seed đẹp.

Cùng trần đánh giá không có nghĩa cùng nfev thực tế hoặc thời gian. Mỗi lượt lưu nfev và thời gian. Penalty 4 thuộc encoding ba-host này; không lấy số 3 của bản compact hai-host để thay giữa phép so sánh.

## Hiệu chuẩn và tài nguyên

Tại góc cố định, sai số chuẩn lý thuyết của trung bình từ S shots độc lập là `std(E)/sqrt(S)`. Notebook đối chiếu nó với độ lệch chuẩn thực nghiệm của 20 trung bình batch. Chênh lệch có thể do số batch hữu hạn; kết quả tại góc đầu không mô tả mọi vùng của landscape và chưa tự chứng minh optimizer bị ảnh hưởng.

Notebook lưu thời gian exact và từng batch, dùng median thời gian batch để ước lượng chi phí nếu dùng hết cap. Ước lượng không gồm khởi tạo, đo cuối, audit; góc và tải máy có thể thay đổi tốc độ. Dùng PREPARE_ONLY nếu chỉ muốn đo chi phí trước, nhưng phải resume cùng campaign sau đó.

Phần đánh giá tạo đường chéo QUBO theo block, không tạo 25 mảng bit toàn chiều hoặc ma trận Hamiltonian 2^25×2^25. Các mảng dữ liệu đường chéo chiếm 384 MiB cho mỗi evaluator; statevector double riêng lẻ chiếm 512 MiB, chưa gồm probabilities, temporary và runtime. Đây không phải tổng RAM tiến trình. Backend CPU, tối đa 4 luồng Aer, max_memory_mb=8192; guard RAM khả dụng 4 GiB và 7200 giây/lượt kiểm tra giữa các lời gọi native. Không chạy song song các lượt.

## Chấm chất lượng

| Chỉ số | Ý nghĩa |
|---|---|
| p_opt | Xác suất lý tưởng đo được domain-wall/y hợp lệ và objective=2 |
| p_valid | Xác suất lý tưởng domain-wall/y thỏa ràng buộc placement |
| p_ground | Xác suất bitstring đạt năng lượng QUBO nhỏ nhất, bao gồm slack |
| mean_energy_exact | Kỳ vọng năng lượng QUBO tại góc cuối |
| mean_energy_sampled | Trung bình năng lượng trong batch cuối độc lập |
| optimal_count / valid_count | Số mẫu đạt tiêu chí trong batch cuối |
| delta_p_opt_pp | 100 × (P_opt exact − trung bình P_opt của nhánh shots), đơn vị điểm phần trăm |

Cả hai nhánh được chấm bằng xác suất lý tưởng tại góc optimizer trả về. Nhờ đó không trộn chất lượng bộ góc với may rủi của batch cuối. Batch cuối dùng seed riêng, vẫn được giữ để quan sát hữu hạn shots. Không repair bit, không postselection. Domain-wall sai bị tính invalid; slack sai có thể đi cùng placement hợp lệ nên P_ground khác P_opt.

Đọc riêng từng độ sâu, từng seed và mức hoàn tất. Min–max năm seed không phải khoảng tin cậy. Không coi một lượt exact là năm mẫu độc lập, không điền 0 cho lượt lỗi/chưa chạy. Nếu exact giảm năng lượng nhưng không tăng P_opt, chưa thể tuyên bố chất lượng placement tăng.

Nếu exact tốt hơn nhất quán qua các seed, dữ liệu ủng hộ giả thuyết shots làm giảm chất lượng huấn luyện trên input này. Nếu cả hai yếu, tiếp tục khảo sát điểm đầu/multistart/INTERP trên chính input này. Thay objective sang CVaR là phép so sánh sau, không trộn vào thí nghiệm hiện tại.

Kết luận chỉ áp dụng cho bộ quy chiếu đã biết và các cấu hình đã chạy. Không suy rộng sang mọi placement hoặc QPU. Optimizer success là điều kiện dừng số học; audit PASS là kiểm tra nhất quán, không chứng minh tối ưu toàn cục, cải thiện chất lượng hoặc nguồn gốc chống giả mạo.

## Lưu và kiểm chứng

Campaign lưu protocol, runtime, nguồn và input; hiệu chuẩn lưu xong từng nhóm; huấn luyện lưu từng lượt và cập nhật ledger. Bắt được lỗi/ngắt trong huấn luyện thì giữ lịch sử đã trả về và traceback; kill process có thể mất lượt đang chạy. Nhóm hiệu chuẩn bị ngắt giữa chừng cần chạy lại. Khóa file chống hai writer; chỉ xóa khóa tồn sau khi xác nhận process cũ đã dừng.

Audit kiểm checksum, kế hoạch, seed, điểm đầu, nfev, histogram năng lượng và counts cuối; tính lại xác suất lý tưởng tại endpoint. Nó không replay toàn bộ đường đi optimizer. ZIP kết quả có raw, CSV, JSON, hình nếu đã vẽ, source/input/protocol snapshot và SHA256. PASS và complete là hai điều kiện riêng.

QA dùng fixture nhỏ và phép chạy rút gọn ở 25 qubit chỉ để kiểm chứng phần mềm. Gói bàn giao có notebook output rỗng, không chứa dữ liệu QA hoặc kết quả campaign chính của người chạy.

## Nguồn kỹ thuật

- [Qiskit AerSimulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html): statevector, seed, shots, double precision và giới hạn backend.
- [Aer save_probabilities](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_probabilities.html): lưu vector xác suất của trạng thái mô phỏng.
- [SciPy COBYLA](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html): maxiter là trần đánh giá hàm.
- [Zhou et al., PRX 10, 021067 (2020)](https://doi.org/10.1103/PhysRevX.10.021067): hướng INTERP cho thí nghiệm khởi tạo sau.
- [Barkoutsos et al., Quantum 4, 256 (2020)](https://doi.org/10.22331/q-2020-04-20-256): hướng CVaR cho thí nghiệm objective sau.
