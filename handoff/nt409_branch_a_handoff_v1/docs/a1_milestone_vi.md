# Mốc A1 - Kết quả 18 lượt QAOA

Văn bản chỉ tiếng Việt. Ngày chốt: 05/10/2026.

## Mốc A1: hoàn tất khảo sát QAOA ban đầu

Ngày ghi nhận: 05/10/2026, giờ Việt Nam. Nhóm: A phụ trách QUBO/Ising/QAOA; B phụ trách thuật toán cổ điển và MILP; C phụ trách phân tích và báo cáo. Văn bản chỉ dùng số liệu do A thực sự chạy trên máy Windows; không gộp các lượt kiểm thử của trợ lý.

Kết luận: đã thực hiện đủ 18 lượt dự kiến trên ba bộ dữ liệu gốc. Quy trình chạy và tính chỉ số được kiểm chứng. Cấu hình hiện tại tìm được placement tối ưu trên cả ba bộ, nhưng kết quả trên p0_reference còn hiếm và chưa ổn định. Chưa hoàn tất khảo sát hệ số phạt, độ sâu hoặc so sánh với baseline.

| Hạng mục | Thiết kế giữ cố định |
| --- | --- |
| Mô hình | Mỗi task đặt nguyên vẹn trên đúng một host; CPU và RAM không vượt dung lượng; tối thiểu số host bật. |
| QUBO | Biến gán x, biến bật host y và slack nhị phân; một hệ số phạt chung P=3. |
| QAOA | Độ sâu p=1; 1024 phép đo mỗi lần lấy mẫu; COBYLA tối đa 35 lần đánh giá. |
| Khởi tạo | goc_cu: [0.3, 0.7]; gamma_nho: [0.3, 0.05]; thứ tự là beta, gamma. |
| Seed | 42, 43, 44 cho mỗi điểm khởi tạo. |
| Môi trường | Windows 11; Conda Python 3.12.14; Qiskit 2.5.2; Aer 0.17.2; Qiskit Optimization 0.7.0. |
| Tài nguyên | Aer CPU, statevector double, 4 luồng, 2048 MiB cho bộ mô phỏng; ngân sách 300 giây/lượt kiểm tra giữa các lần đánh giá. |

| Bộ dữ liệu | Task / host | Qubit | Lượt hoàn tất | Lượt có placement tối ưu |
| --- | --- | --- | --- | --- |
| p1_tight | 4 / 2 | 18 | 6 / 6 | 6 / 6 |
| p1_choice | 4 / 2 | 20 | 6 / 6 | 6 / 6 |
| p0_reference | 4 / 2 | 23 | 6 / 6 | 1 / 6 |

A1 là tên tổ chức nội bộ cho khảo sát ban đầu. Có báo cáo kết quả không đồng nghĩa thuật toán luôn tìm được nghiệm hoặc cả nhóm đã hoàn tất một phase chính thức. Bộ p1_infeasible không nằm trong 18 lượt này; demo p3_demo cũng được giữ riêng.

## Kết quả p1_tight

Mỗi khởi tạo có ba seed; mỗi lượt có 1024 phép đo cuối. Các số đếm dưới đây được tính lại từ chuỗi bit và kiểm tra với báo cáo nguồn.

| Khởi tạo | Seed | Mẫu hợp lệ | Mẫu tối ưu | Năng lượng TB | Bộ giải (giây) |
| --- | --- | --- | --- | --- | --- |
| goc_cu | 42 | 12 | 12 | 136,737 | 0,91 |
| goc_cu | 43 | 24 | 24 | 120,122 | 0,97 |
| goc_cu | 44 | 21 | 21 | 132,112 | 0,82 |
| gamma_nho | 42 | 8 | 8 | 71,125 | 0,90 |
| gamma_nho | 43 | 10 | 10 | 105,086 | 0,93 |
| gamma_nho | 44 | 6 | 6 | 147,585 | 0,91 |

| Khởi tạo | Hợp lệ TB (%) | Độ lệch chuẩn | Tối ưu TB (%) | Năng lượng TB |
| --- | --- | --- | --- | --- |
| goc_cu | 1,8555 | 0,6099 | 1,8555 | 129,657 |
| gamma_nho | 0,7812 | 0,1953 | 0,7812 | 107,932 |

Cả sáu lượt đều tìm được placement tối ưu dùng hai host. Mọi placement hợp lệ của bộ này đều cần hai host nên tỷ lệ hợp lệ bằng tỷ lệ tối ưu. goc_cu có 57 mẫu hợp lệ trong 3072 phép đo; gamma_nho có 24/3072.

Mốc hợp lệ khi lấy mẫu đều: 0,390625%. Hai nhóm đều vượt mốc này trong dữ liệu quan sát. gamma_nho giảm năng lượng trung bình, nhưng giảm tỷ lệ mẫu hợp lệ/tối ưu. Không thể chọn góc tốt hơn chỉ từ năng lượng.

Không lượt nào đo được cực tiểu QUBO. Placement tối ưu chỉ yêu cầu x,y đúng; cực tiểu QUBO còn đòi hỏi slack đúng.

Độ lệch chuẩn là độ lệch chuẩn mẫu giữa ba seed, đơn vị điểm phần trăm. Không diễn giải nó thành khoảng tin cậy. Tỷ lệ số lượt có nghiệm khác với tỷ lệ mẫu có nghiệm.

## Kết quả p1_choice

Mỗi khởi tạo có ba seed; mỗi lượt có 1024 phép đo cuối. Các số đếm dưới đây được tính lại từ chuỗi bit và kiểm tra với báo cáo nguồn.

| Khởi tạo | Seed | Mẫu hợp lệ | Mẫu tối ưu | Năng lượng TB | Bộ giải (giây) |
| --- | --- | --- | --- | --- | --- |
| goc_cu | 42 | 33 | 2 | 141,023 | 1,88 |
| goc_cu | 43 | 23 | 1 | 140,356 | 1,93 |
| goc_cu | 44 | 14 | 3 | 144,280 | 2,30 |
| gamma_nho | 42 | 26 | 1 | 123,539 | 2,19 |
| gamma_nho | 43 | 29 | 2 | 115,550 | 1,73 |
| gamma_nho | 44 | 21 | 1 | 119,217 | 2,09 |

| Khởi tạo | Hợp lệ TB (%) | Độ lệch chuẩn | Tối ưu TB (%) | Năng lượng TB |
| --- | --- | --- | --- | --- |
| goc_cu | 2,2786 | 0,9282 | 0,1953 | 141,887 |
| gamma_nho | 2,4740 | 0,3947 | 0,1302 | 119,435 |

Cả sáu lượt đều có placement tối ưu dùng một host, nhưng mỗi lượt chỉ đo được 1-3 mẫu tối ưu. goc_cu có 70 mẫu hợp lệ và 6 mẫu tối ưu trong 3072 phép đo; gamma_nho có 76 mẫu hợp lệ và 4 mẫu tối ưu.

Placement dùng hai host có thể hợp lệ nhưng không tối ưu. Vì vậy, cột hợp lệ và cột tối ưu trả lời hai câu hỏi khác nhau. Mốc lấy mẫu đều: hợp lệ 1,171875%; tối ưu 0,09765625%.

gamma_nho làm năng lượng thấp hơn và tỷ lệ hợp lệ tăng nhẹ, nhưng tỷ lệ tối ưu giảm. Chỉ ba seed mỗi nhóm, chưa đủ khẳng định một khởi tạo ổn định hơn. Không có mẫu đạt cực tiểu QUBO.

Độ lệch chuẩn là độ lệch chuẩn mẫu giữa ba seed, đơn vị điểm phần trăm. Không diễn giải nó thành khoảng tin cậy. Tỷ lệ số lượt có nghiệm khác với tỷ lệ mẫu có nghiệm.

## Kết quả p0_reference: chạy được, nghiệm còn hiếm

| Khởi tạo | Seed | Mẫu hợp lệ | Mẫu tối ưu | Năng lượng TB | Bộ giải (giây) |
| --- | --- | --- | --- | --- | --- |
| goc_cu | 42 | 0 | 0 | 658,904 | 14,99 |
| goc_cu | 43 | 0 | 0 | 631,863 | 13,43 |
| goc_cu | 44 | 0 | 0 | 683,186 | 15,80 |
| gamma_nho | 42 | 0 | 0 | 387,896 | 16,21 |
| gamma_nho | 43 | 0 | 0 | 683,459 | 16,22 |
| gamma_nho | 44 | 1 | 1 | 703,586 | 15,06 |

Có một mẫu hợp lệ trong 6144 phép đo cuối, tỷ lệ 0,016276%. Chỉ gamma_nho/seed44 có nghiệm: một mẫu trong 1024 phép đo. Năm lượt còn lại hoàn tất bình thường nhưng không đo được placement hợp lệ.

| Host | Task được đặt | CPU dùng / tối đa | RAM dùng / tối đa |
| --- | --- | --- | --- |
| H0 | T1, T2 | 5 / 5 | 6 / 6 |
| H1 | T3, T4 | 5 / 6 | 8 / 8 |

Đây là placement tối ưu dùng hai host. Tổng RAM của task bằng 14, vượt dung lượng từng host, nên không thể dùng một host. Đối chiếu toàn bộ 1024 cấu hình x,y cho thấy đúng một cấu hình hợp lệ.

Slack cần có theo thứ tự CPU H0, RAM H0, CPU H1, RAM H1 là [0,0,1,0]. Mẫu đo mã hóa [3,3,1,8], nên năng lượng bằng 2 + 3 × (3² + 3² + 0² + 8²) = 248. Placement đúng nhưng chưa đạt cực tiểu QUBO bằng 2.

Mốc hợp lệ khi lấy mẫu đều là 1/1024 = 0,09765625%. Tỷ lệ quan sát của cả hai nhóm khởi tạo đều chưa vượt mốc này. Năng lượng TB goc_cu: 657,984375; gamma_nho: 591,646810; mốc năng lượng lấy mẫu đều: 742. Giảm năng lượng không bảo đảm tăng tỷ lệ hợp lệ.

Bước 9 trong notebook đang xem lượt đầu tiên, goc_cu/seed42, nên hiển thị None. Đó là kết quả của một lượt, không phải kết luận cả sáu lượt không có đáp án.

## Cách đọc kết quả và phạm vi đã kiểm chứng

| Tiêu chí | Kết quả và giới hạn |
| --- | --- |
| Tính đúng | Đối chiếu cấu hình, mã băm dữ liệu/thiết kế, khóa lượt, chuỗi bit, năng lượng và chỉ số; báo cáo nguồn khớp chỉ mục. Không có lỗi chạy trong notebook. |
| Chạy ổn định | 18 lượt đều hoàn tất; đợt 23 qubit không timeout. Không suy rộng sang dữ liệu hoặc cấu hình chưa chạy. |
| Tìm placement tối ưu | 12/12 lượt của tight/choice; 1/6 lượt của reference. 13/18 chỉ là số đếm hành chính giữa các bài toán khác nhau, không dùng làm chỉ số chất lượng chung. |
| Cực tiểu QUBO | Không có mẫu đạt cực tiểu QUBO trong 18 lượt. Chưa thể coi đây là kết quả tối ưu năng lượng hoàn chỉnh. |
| Thống kê | Ba seed mỗi khởi tạo là khảo sát nhỏ. Giữ mọi lượt hoàn tất, gồm lượt không có nghiệm; không chỉ chọn seed tốt nhất. |
| So sánh cổ điển | Chưa dùng kết quả này để tuyên bố thắng MILP/FF/BFD; cần kết quả cùng dữ liệu và tiêu chí từ B. |

Lưu ý về mẫu phổ biến nhất: cột cũ kiểm tra mẫu đầu sau khi sắp theo tần suất. Có nhiều mẫu đồng hạng. Với gamma_nho/seed44 của reference, cả 1024 chuỗi chỉ xuất hiện một lần. Mẫu placement đúng được tìm khi kiểm tra tất cả mẫu, chưa phải một chuỗi nổi trội theo quy tắc tần suất trong proposal. Đợt sau cần báo số mẫu đồng hạng và chỉ đánh giá mode duy nhất khi thật sự có mode duy nhất.

Thời gian: tight/choice tổng bộ giải 17,561 giây, giải mã 14,417 giây; reference tổng bộ giải 91,705 giây, giải mã 9,044 giây. Các tổng này không gồm mọi chi phí chuẩn bị/ghi file. RAM đỉnh báo cáo: 197,109 MiB ở đợt đầu; 293,512 MiB ở đợt reference. Đỉnh tính trên toàn vòng đời tiến trình Python, không phải RAM tăng thêm từng lượt hoặc RAM của toàn hệ thống.

Trong công thức E = tổng y + P × V, V là tổng bình phương sai số one-hot và phương trình tài nguyên có slack. V không chỉ đo quá tải CPU/RAM: slack sai cũng làm V tăng. P > số host là điều kiện đủ để cực tiểu toàn cục hợp lệ khi bài toán có nghiệm và sai số là số nguyên. Điều kiện đó không bảo đảm QAOA tìm được cực tiểu.

## Chốt mốc và bước tiếp theo theo đề cương

Đã hoàn thành: môi trường và mô hình gốc; QUBO/slack và kiểm chứng; demo QAOA; quy trình Aer cho dữ liệu gốc; khảo sát A1 có kiểm soát trên ba bộ dữ liệu. Việc B/C đã nhận bàn giao được A xác nhận trước A1; việc họ đã nhận các báo cáo mới cần A thực hiện riêng.

Theo proposal mục 5-6, bước tiếp theo là khảo sát hệ số phạt, rồi p=1,2,3 với nhiều seed, sau đó so sánh baseline và tổng hợp. Giá trị đồ án là đo lường trung thực, giải thích giới hạn. Không có cam kết mọi lượt QAOA đều tìm được nghiệm hoặc thắng thuật toán cổ điển.

Đợt kế tiếp: thay P chung theo các giá trị 1,2,3,5,8; giữ p=1, 1024 phép đo, maxiter=35, hai khởi tạo và ba seed. Mặc định p1_tight/p1_choice: 60 lượt; p0_reference chạy riêng: 30 lượt. Đây là lát cắt A=B=P của hệ số phạt trong proposal, chưa khảo sát hai hệ số độc lập. Chưa tăng số task/host hoặc đổi optimizer trong đợt này.

Không so trực tiếp năng lượng thô giữa các P vì thang năng lượng đã đổi. So sánh tỷ lệ hợp lệ/tối ưu, số lượt có nghiệm, thời gian và V trung bình. Mỗi P phải kiểm tra tham chiếu QUBO riêng; cực tiểu QUBO có thể khác với nghiệm gốc khi thay penalty.

| Nhánh | Việc tiếp theo |
| --- | --- |
| A | Chạy khảo sát P, cung cấp chỉ mục và toàn bộ báo cáo nguồn; đánh giá các mẫu thực đo và ghi rõ ngân sách. |
| B | Hoàn thiện FF/BFD/MILP trên cùng JSON; dùng chung mục tiêu tối thiểu host và ràng buộc CPU/RAM. |
| C | Tách từng instance/khởi tạo/P; ghi số lượt dự kiến/thực chạy, trung bình và độ lệch chuẩn; phân biệt placement và cực tiểu QUBO. |

Nguồn số liệu: chỉ mục campaign_20261005T033659278851Z.json (12 lượt) và campaign_20261005T043159632930Z.json (6 lượt), cùng 18 báo cáo JSON được chúng tham chiếu; hai bản notebook 06 có đầu ra. Thông tin gốc được giữ trong data/reference_results/phase3_runs và chỉ mục trong phase4a_runs. Không đếm notebook/chỉ mục/báo cáo của cùng lượt thành nhiều thí nghiệm.

Nguồn định hướng: nt409-topic16-proposal.pdf, mục 3 (QAOA và giải mã), mục 5 (lịch trình), mục 6 (kết quả kỳ vọng). Văn bản này ghi nhận mốc A1 ngày 05/10/2026, không thay thế proposal hoặc xác nhận các công việc còn lại đã xong.
