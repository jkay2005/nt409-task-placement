# Notebook 24: objective CVaR trên bộ quy chiếu cố định

## Câu hỏi và phạm vi

Sau Notebook 23, INTERP là lựa chọn khởi tạo có triển vọng trên input đang dùng. Câu hỏi mới: với cùng khởi tạo INTERP và trần ngân sách, thay mean-energy bằng lower-tail CVaR ở p=2 có tăng xác suất thu placement tối ưu không?

Đây là thí nghiệm khám phá trên **một input đã được quan sát và dùng để chọn INTERP**, không phải kiểm định trên tập mới hoặc chứng minh tổng quát. Chưa có kết quả chạy chính của Notebook 24 lúc bàn giao. Không cam kết CVaR sẽ thắng.

Giữ nguyên a3_dev_n5, 5 task + 3 host,25 qubit; domain-wall, penalty capacity/domain=4, X mixer, max_abs scale 65.5, COBYLA rhobeg=1/tol=1e-4. Bộ quy chiếu có ba host khả dụng; nghiệm tối ưu của input dùng hai host. Ground truth chỉ dùng chấm chất lượng, không dùng huấn luyện hoặc chọn góc.

Input canonical SHA256: `e6d3ac93ed2d5a831f5d7393750e9a1995b46fbe20d077058a629c7797996278`.
QUBO SHA256: `8fa77f91e277724277e5aaf4c1a29b5cec345e91e3660f13a6a166efc44fc515`.

## CVaR đang tính gì?

Gọi E_j là các mức năng lượng QUBO tăng dần, p_j là tổng xác suất ở mức đó. Với alpha thuộc(0,1], chọn k đầu tiên sao cho tổng xác suất đến k đạt alpha. Khi đó:

$$
\mathrm{CVaR}_{\alpha}=\frac{\sum_{j<k}E_jp_j+E_k\left(\alpha-\sum_{j<k}p_j\right)}{\alpha}.
$$

Đây là lower-tail cho bài toán tối thiểu hóa. Phải lấy đúng alpha khối xác suất, bao gồm phần biên, không làm tròn số mẫu và không lấy alpha phần số trạng thái. Các trạng thái đồng năng lượng được gộp. Alpha=1 trả về mean-energy.

Hai mức alpha 0.25 và0.10 được cố định trước chạy. Đây là lựa chọn khảo sát, không tuyên bố tối ưu. Không thử thêm alpha rồi chỉ công bố giá trị thắng. Toàn bộ ba phương án phải được báo cáo, kể cả kết quả âm.

Huấn luyện dùng phân phối statevector lý tưởng. Mỗi evaluation chỉ chạy một mạch, rồi tính mean và objective từ phân phối đó; không dùng P_opt/P_valid để cập nhật góc. Hàm `lower_tail_cvar` và quy tắc biên được tái sử dụng từ Notebook 14. Evaluator mới dùng mạch/encoding25 qubit của Notebook 22/23; không dùng oracle cũ giới hạn23 qubit.

Vì QUBO này có năng lượng nguyên không âm, histogram gộp mức năng lượng bằng bincount với index được chuẩn bị một lần, không sắp xếp33 triệu trạng thái trong từng evaluation. Đây là cách triển khai phép tổng, không đổi Hamiltonian hoặc phép đo. Mean alpha=1 giữ phép nhân vector cũ để không đổi số học control.

## Chỉ đổi objective ở giai đoạn đích

Mỗi phương án chạy mới p=1 từ [beta=0.3,gamma_execution=1] với mean-energy và cap 100. Lặp góc theo INTERP để khởi tạo p=2: [beta,gamma] → [beta,beta,gamma,gamma]. Sau đó p=2 cap 100 tối ưu một trong mean/CVaR 25%/CVaR 10%.

Giữ p=1 là mean cho cả ba phương án nhằm thu cùng khởi tạo p=2. Nếu p=1 cũng đổi sang CVaR thì sẽ đồng thời thay objective và khởi tạo, làm khó xác định nguyên nhân. Audit kiểm các điểm khởi tạo p=2 khớp trong tolerance 1e-10.

Mỗi nhóm có p=1 riêng và dependency hash của chính nó, không chia sẻ miễn phí report/góc từ nhóm khác hay Notebook 23. Control mean được chạy mới để đối chiếu trên cùng runtime; kết quả0.8361% của Notebook 23 chỉ là bối cảnh lịch sử, không được nhập làm kết quả nhóm mean mới.

## Ngân sách và chi phí ngoài tối ưu

Mỗi kết quả có cap 200=100 chuẩn bị + 100 đích. Toàn campaign có ba kết quả, sáu lượt optimizer và tối đa 600 đánh giá huấn luyện. Nfev thực dùng được giữ; COBYLA có thể dừng sớm. Trần bằng nhau không đồng nghĩa cùng nfev, cùng thời gian hoặc cùng số backend calls ngoài tối ưu.

Một evaluation CVaR có thêm chi phí histogram. Profile đo riêng từng loại objective; các phép profile không chọn hay cập nhật góc. Tại mỗi endpoint có một phép exact chấm placement/mean và một phép statevector chấm toàn bộ ba objective, cùng batch1.024 shots độc lập. Các phép này không đi vào ngân sách training và được ghi trong diagnostic_exact_calls/final_measurement_shots. Audit replay tiếp các endpoint/profile ngoài cap.

Ghi nhận running trước native work để kill process không âm thầm đặt lại ngân sách. Failed/interrupted giữ history có sẵn; nếu kill thì nfev có thể chưa biết. Không tự retry hay lấy ngân sách dư từ phương án khác. Campaign không đủ được báo partial, không điền P_opt=0 cho nhóm chưa chạy.

## Chọn góc, chấm và diễn giải

Mỗi nhóm lấy đúng góc COBYLA trả về theo objective đã định, không chọn lại theo P_opt hoặc chọn điểm đẹp trong lịch sử. Chỉ p=2 là đầu ra chất lượng; p=1 là chuẩn bị có phí. Ba kết quả xác định không phải ba seed độc lập; sáu lượt optimizer không phải sáu mẫu nghiên cứu độc lập.

Tại mọi góc p=2 đều báo cùng các cột:

- P_opt: xác suất placement hợp lệ dùng số host tối ưu, trên toàn phân phối.
- P_valid: xác suất placement hợp lệ; P_ground: xác suất đạt năng lượng QUBO thấp nhất gồm slack.
- mean_energy, cvar_025, cvar_010: chấm chéo cùng objective tại mọi góc.
- raw_objective: giá trị objective riêng mà nhóm đã tối ưu; không gọi nó là mean nếu alpha<1.
- nfev: tổng hai giai đoạn; budget_cap, thời gian, chi phí chấm và counts ghi riêng.

Chỉ so sánh **cùng một cột** giữa các phương án. CVaR 10% thường thấp hơn mean tại cùng một phân phối theo định nghĩa; chênh lệch đó không chứng minh huấn luyện tốt hơn. P_opt/P_valid không bị điều kiện hóa theo tail, không postselection và không repair bit. Việc objective huấn luyện dùng tail không làm thay đổi mẫu số của các xác suất chất lượng báo cáo.

QUBO gồm penalty và slack, nên ưu tiên năng lượng tail chưa chắc trùng ưu tiên placement tối ưu. Nếu CVaR giảm nhưng P_opt không tăng, phải báo mục tiêu chất lượng chưa cải thiện. Nếu P_opt tăng nhưng P_valid giảm, báo rõ đánh đổi. Nếu cả hai tăng, dữ liệu ủng hộ phương án trong cấu hình này; vẫn không suy rộng sang mọi input hoặc phần cứng.

Mean-energy không nhất thiết giảm dưới huấn luyện CVaR. Batch cuối1.024 shots có nhiễu; không dùng vài counts chênh lệch làm bằng chứng thay cho xác suất exact. Không tạo khoảng tin cậy/SD giả từ lặp cùng một phép tối ưu xác định.

Hết cap vẫn là lượt hoàn tất nhưng không chứng minh hội tụ; optimizer success chỉ là điều kiện dừng số học. Audit PASS xác nhận dữ liệu/đơn vị/ngân sách nhất quán; complete xác nhận đủ kế hoạch. Audit tính lại endpoint và objective, không replay toàn bộ đường optimizer và không chứng minh tối ưu toàn cục.

## Tái lập và nguồn

Export có input, protocol, runtime,15 module nguồn snapshot, plan, góc, history, parent hash, counts, profile, bảng so sánh và checksum. Các nguồn cũ được giữ nguyên để không làm hỏng resume của Notebook 23.

Nguồn: Barkoutsos et al., [Improving Variational Quantum Optimization using CVaR](https://doi.org/10.22331/q-2020-04-20-256), Quantum 4, 256 (2020), [bản tác giả](https://arxiv.org/abs/1907.04769). Bài báo là cơ sở của objective; chất lượng trên placement này phải do dữ liệu mới xác định.

INTERP: Zhou et al., [Quantum Approximate Optimization Algorithm: Performance, Mechanism, and Implementation on Near-Term Devices](https://doi.org/10.1103/PhysRevX.10.021067), PRX 10,021067(2020), Appendix B Eq.B1. Việc kết hợp INTERP ngân sách100+100 với CVaR ở đây là thiết kế thí nghiệm của dự án, không phải tái hiện toàn bộ thực nghiệm hai bài báo.
