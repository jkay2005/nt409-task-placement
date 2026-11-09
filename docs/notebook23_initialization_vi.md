# Notebook 23: khởi tạo và ngân sách đánh giá QAOA

## Câu hỏi

Trên duy nhất a3_dev_n5, thay điểm khởi tạo hiện tại bằng hai điểm khởi tạo hoặc INTERP có tạo phân phối QAOA với P_opt cao hơn, dưới cùng trần tổng đánh giá hàm tối ưu không?

Notebook 22 cho thấy nhiễu shots ảnh hưởng đường đi và thời điểm dừng; exact có thể được chạy nhiều nfev hơn. Vì vậy bước này dùng exact cho cả ba chiến lược, ghi nfev thực tế và giữ nguyên mọi thành phần khác. Đây là thí nghiệm khám phá trên một input đã quan sát, không phải chứng minh tổng quát hay lợi thế tốc độ.

## Mô hình cố định

Dùng trực tiếp `data/benchmarks/nt409_shot_noise_v2/instance.json`: t0–t3 mỗi task (1,1), t4 (1,2); h0 (2,2), h1,h2 mỗi host (3,3). Có 5 task, 3 host, 25 qubit. Domain-wall, penalty 4, X mixer, scale max_abs=65.5, mean-energy và COBYLA rhobeg=1/tol=1e-4 giữ nguyên.

Input canonical SHA256: `e6d3ac93ed2d5a831f5d7393750e9a1995b46fbe20d077058a629c7797996278`.
QUBO SHA256: `8fa77f91e277724277e5aaf4c1a29b5cec345e91e3660f13a6a166efc44fc515`.

Bộ quy chiếu vẫn có ba host khả dụng. Nghiệm tối ưu của input này chỉ cần dùng hai host; ground truth đó dùng để chấm, không chọn góc. Không nhập góc hoặc kết quả đã học từ Notebook 22. Có fixture nhỏ trong unit test để kiểm chứng phần mềm; đó không phải bộ dữ liệu nghiên cứu thứ hai.

## Chiến lược và ngân sách

### Single

p=1 bắt đầu [beta=0.3,gamma_execution=1]. p=2 bắt đầu beta=[0.3,0], gamma_execution=[1,0]. Một lượt optimizer, cap 200. Mỗi độ sâu có một kết quả xác định, không lặp giả thành năm seed.

### Multistart hai điểm

Mỗi lần chạy chiến lược có hai lượt optimizer: điểm hiện tại cap 100, một điểm random cap 100. Chọn điểm optimizer trả về có mean-energy exact thấp nhất; nếu bằng nhau chọn lượt đứng trước trong plan. Chấm P_opt/P_valid sau lựa chọn đó. Không chọn điểm có P_opt cao nhất hoặc nhiều mẫu tối ưu nhất.

Có năm bộ seed 400–404 cho mỗi độ sâu; một seed tạo một bộ hai điểm. Các bộ chia sẻ điểm anchor, chỉ điểm random thay đổi. Chúng không phải năm lần đo lượng tử độc lập của cùng bộ góc.

### INTERP có tính phí chuẩn bị

Chạy mới p=1 từ [0.3,1] với cap 100, rồi dùng góc trả về để khởi tạo p=2 với cap 100. Với p=1→2, công thức INTERP của Zhou et al. cho:

`[beta,gamma] -> [beta,beta,gamma,gamma]`.

Thứ tự Qiskit là toàn bộ beta trước, rồi toàn bộ gamma. Cả hai lớp p=2 đều được khởi tạo từ góc đã học; không nối thêm cặp góc 0 như điểm hiện tại. Chỉ kết quả p=2 được chấm như đầu ra chiến lược, còn nfev tính cả p=1. Không dùng miễn phí góc của single/multistart hay dữ liệu cũ. P=1 bị giới hạn 100 nên có thể chưa hội tụ: đây là INTERP chịu ngân sách, không tái hiện toàn bộ thực nghiệm của bài báo.

### Kế toán chi phí

Mỗi nhóm có tổng cap **200**: single 200; multistart 100+100; INTERP 100+100. Hai độ sâu có 13 nhóm, tổng 24 lượt optimizer, tối đa 2600 lời gọi hàm huấn luyện. Không phải mỗi start đều có 200.

Cap bằng nhau không bảo đảm nfev thực dùng hoặc thời gian bằng nhau. INTERP có một phần tính ở độ sâu 1; chi phí mỗi evaluation có thể khác evaluation ở độ sâu 2. Các chẩn đoán tại góc cuối, batch đo cuối, profile và audit nằm ngoài ngân sách tối ưu; chúng không được dùng chọn góc. `diagnostic_exact_calls` và `final_measurement_shots` ghi phần chấm của từng nhóm.

Không tái cấp ngân sách cho lượt lỗi bằng retry tự động. Lượt đang chạy được ghi trước native work để kill process không âm thầm biến lượt đó thành chưa từng chạy. Dữ liệu chưa đủ được đánh dấu partial; nhóm lỗi không được điền P_opt=0 hoặc bị chọn bỏ để cải thiện trung bình.

## Góc random và đơn vị scaling

Đặt s=65.5. H_execution=H_raw/s, nên gamma_execution=s×gamma_raw. Beta lấy đều trên [0,π); gamma_raw lấy đều trên [0,2π), tương đương gamma_execution trong [0,2πs). RNG là default_rng(seed+10000×p); plan lưu số thực cuối cùng để kiểm chứng.

Miền trên dùng một chu kỳ xác suất của mô hình: X mixer có chu kỳ beta π đến pha toàn cục; năng lượng QUBO nguyên cho chu kỳ gamma_raw 2π đến pha toàn cục. Đây là miền khởi tạo, optimizer vẫn được di chuyển ra ngoài. Không nhầm gamma_execution với gamma_raw hoặc lấy khoảng nhỏ rồi gọi là khảo sát toàn chu kỳ.

Miền random, hai điểm và chia 100+100 là các lựa chọn cố định trước chiến dịch này, không bảo đảm tối ưu hơn single. Nếu cần khảo sát miền hoặc số start khác, phải coi đó là thí nghiệm khác với protocol rõ ràng.

## Chấm và kết luận

Đơn vị kết quả là **chiến lược**, không phải từng lượt optimizer. Đầu ra chính có 13 dòng, không trộn 24 lượt optimizer làm 24 mẫu độc lập. Với INTERP, p=1 chỉ chuẩn bị. Với multistart, mỗi nhóm chỉ có một góc được chọn theo năng lượng.

- P_opt: xác suất lý tưởng thu placement hợp lệ dùng hai host tại góc được chọn.
- P_valid: xác suất lý tưởng thu placement hợp lệ.
- P_ground: xác suất đạt năng lượng QUBO nhỏ nhất, gồm slack.
- mean_energy: năng lượng QUBO kỳ vọng tại góc được chọn.
- optimal_count: số mẫu tối ưu trong batch 1024 shots cuối của lượt được chọn.
- budget_cap và nfev: trần ngân sách và tổng số đánh giá thực dùng, gồm p=1 chuẩn bị INTERP.

Báo cáo riêng p=1 và p=2. Với multistart cần xem cả năm seed và mean/min–max; min–max không phải khoảng tin cậy. Single/INTERP có một kết quả xác định, không tạo SD giả từ các lần lặp giống nhau. Nếu chỉ một seed tốt, báo cáo sự phụ thuộc seed thay vì chọn riêng seed tốt nhất làm đại diện.

Năng lượng thấp hơn nhưng P_opt không tăng chưa đáp ứng mục tiêu tăng xác suất lấy placement tối ưu. Nếu multistart/INTERP ổn định hơn single về P_opt, dữ liệu ủng hộ thay khởi tạo trong phạm vi cấu hình này. Nếu không cải thiện, báo cáo kết quả âm và xem giới hạn mỗi start/khác biệt objective, chưa kết luận khởi tạo không quan trọng nói chung.

Optimizer success là điều kiện dừng số học; chạm cap là lượt hoàn tất nhưng chưa chắc hội tụ. Audit PASS kiểm nhất quán dữ liệu/ngân sách, không chứng minh tối ưu toàn cục hoặc cải thiện chất lượng. Complete xác nhận đủ nhóm trong kế hoạch, không đánh giá chất lượng.

## Tái lập và nguồn

Export có input/protocol/runtime/nguồn snapshot, lịch sử, góc, dependency hash INTERP, counts, bảng chiến lược và SHA256. Audit tính lại các endpoint; không replay toàn bộ 2600 lời gọi optimizer. Giữ cả notebook có output và ZIP khi bàn giao.

Nguồn INTERP: Zhou et al., [Quantum Approximate Optimization Algorithm: Performance, Mechanism, and Implementation on Near-Term Devices](https://doi.org/10.1103/PhysRevX.10.021067), PRX 10,021067 (2020), Appendix B, Eq.B1. Bài báo nghiên cứu MaxCut; việc áp dụng cho placement này là thí nghiệm cần kiểm chứng.

[Qiskit Aer](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html) mô tả simulator/precision/shots; [SciPy COBYLA](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html) mô tả cap đánh giá và trust-region tolerance. Không dùng kết quả QA rút gọn làm bằng chứng chất lượng.
