# Đánh giá kết quả Notebook 20 — nhánh A

Ngày đánh giá: 13/10/2026. Ghi chú bổ sung: sau audit, người dùng cho biết máy có vào sleep/chế độ ngưng trong khi chạy; giữ số đo thời gian gốc, không xem toàn bộ là thời gian tính toán thuần. Campaign: `20261012T112947210418Z`.

**Kết luận:** Notebook 20 đã hoàn tất đúng giao thức: 90/90 lượt test và 18/18 probe. Tất cả lượt test tìm được placement khả thi; 63/90 lượt tìm được placement tối ưu. Tổng thời gian tính vào ngân sách là 3 giờ 28 phút 36 giây. Kết quả đủ để kết thúc đợt thực nghiệm ba host hiện tại và chuyển sang viết báo cáo nhánh A. Mục tiêu giải nhanh hơn các thuật toán cổ điển chưa đạt; dữ liệu này cũng chưa chứng minh QAOA hữu ích hơn lấy mẫu placement trực tiếp.

## 1. Phạm vi và cách đọc kết quả

Đợt test sử dụng sáu instance đã cố định: ba instance có 4 task, ba instance có 5 task; tất cả có 3 host. Mỗi instance chạy QAOA ở p=1, 2, 3 với năm seed 200–204: 6 × 3 × 5 = 90 lượt. Cả ba độ sâu được báo cáo ngang nhau; giao thức không chọn p dựa trên kết quả test.

Mỗi lượt tối ưu dùng 1.024 shot cho mỗi lần đánh giá, sau đó lấy một batch mới gồm 1.024 shot với evaluation seed riêng. COBYLA có giới hạn 200 đánh giá và giới hạn thời gian 2.400 giây/lượt. Mô phỏng dùng Aer statevector trên CPU, precision double, tối đa bốn thread. Đây là thực nghiệm mô phỏng trên máy tính cổ điển.

Đầu ra được chọn theo quy tắc `best_valid_no_bit_repair`: lấy placement khả thi có mục tiêu tốt nhất trong batch cuối, không sửa bit của mẫu. Tính khả thi được kiểm tra từ task, host, CPU, RAM và các biến bật host; slack của QUBO không được dùng làm điều kiện khả thi vật lý. Vì vậy, placement tốt có thể đi cùng slack không đúng và không phải trạng thái nền QUBO.

Quy tắc chọn đầu ra này cần được ghi rõ trong báo cáo vì đề cương ban đầu mô tả lấy bitstring xuất hiện nhiều nhất. Hai quy tắc không có cùng xác suất thành công. Không diễn giải thành công của best-of-1.024 thành thành công của một shot hoặc của bitstring mode.

## 2. Tính toàn vẹn và kiểm tra độc lập

Archive nguồn là `test_20261012T112947210418Z.zip`, SHA-256:

```text
c5f96510fad1007c9d7de185623e379e8416a59e3689bd0fdb3dbe8a9f49be19
```

Kết quả kiểm tra:

- 138 entry trong archive có tên duy nhất; toàn bộ 137 checksum payload khớp.
- Các file JSON, CSV, PNG và manifest tải riêng khớp byte với bản trong archive.
- 21 module nguồn khớp SHA-256 ghi trong campaign. Các module được đối chiếu với bản đã phát hành hoặc GitHub backup; khác biệt LF/CRLF được xử lý riêng.
- Toàn bộ 108 báo cáo gồm 90 trial và 18 probe vượt qua kiểm tra semantic của nguồn đã lưu: input, cấu hình, run key, seed, tham số, counts, giải mã, năng lượng, trace, shot accounting và manifest.
- Một phép duyệt placement độc lập tái tạo optimum của sáu instance và các xác suất đối chứng.
- Giải mã và tính năng lượng độc lập cho 91.497 bitstring khác nhau cộng theo từng trial, tương ứng toàn bộ 92.160 final shot. Chất lượng nghiệm được xác nhận trực tiếp từ các ràng buộc vật lý.
- Tính lại 90 dòng CSV và summary cho kết quả khớp. Notebook giữ nguyên 19 cell nguồn so với bản phát hành; chín code cell có execution count 1–9 và không có output lỗi.

Tổng cộng 206.063 điều kiện đối chiếu vượt qua. Con số này thể hiện độ bao phủ của audit, không phải 206.063 thử nghiệm chất lượng độc lập.

Audit chạy ở Linux với cùng các phiên bản thư viện ghi trong Windows: NumPy 2.5.3, SciPy 1.18.1, Qiskit 2.5.2, Qiskit Aer 0.17.2, Qiskit Optimization 0.7.0 và psutil 7.2.2. Chỉ phép so sánh chuỗi OS platform được điều chỉnh sang giá trị Windows đã lưu để kiểm tra dữ liệu có thể chạy trên môi trường khác. Không chạy lại quá trình huấn luyện QAOA hoặc xác nhận lại thời gian/RAM của Windows bằng đo Linux.

## 3. Chất lượng placement đã đạt

Optimum chính xác của cả sáu instance là **2 host hoạt động**.

| Chỉ tiêu | Kết quả |
|---|---:|
| Lượt hoàn tất | 90/90 |
| Batch cuối có ít nhất một placement khả thi | 90/90 |
| Batch cuối có ít nhất một placement tối ưu | 63/90 — 70% |
| Đầu ra dùng 2 host | 63 lượt |
| Đầu ra dùng 3 host | 27 lượt |
| Số host trung bình của đầu ra | 2,3 |
| Tỷ số mục tiêu đầu ra/optimum trung bình | 1,15 |

Như vậy, thuật toán luôn trả được một placement hợp lệ trong đợt này. Trong 30% lượt còn lại, đầu ra dùng thêm một host so với optimum. Tỷ số 1,15 là mô tả kết quả quan sát của best-of-1.024; nó không phải một bảo đảm xấp xỉ cho mọi bài toán.

**100% batch có nghiệm khả thi không có nghĩa 100% shot khả thi.** Xác suất khả thi trung bình theo shot chỉ khoảng 0,87% ở p1/p2 và 1,12% ở p3; nhiều mẫu đo vẫn không tạo được placement hợp lệ.

| Quy mô | p | Batch đạt tối ưu | P_opt trung bình mỗi shot | Thời gian một trial, trung vị |
|---|---:|---:|---:|---:|
| 4 task / 3 host | 1 | 7/15 | 0,0781% | 11,46 giây |
| 4 task / 3 host | 2 | 12/15 | 0,1367% | 24,79 giây |
| 4 task / 3 host | 3 | 10/15 | 0,0977% | 41,96 giây |
| 5 task / 3 host | 1 | 10/15 | 0,1758% | 62,91 giây |
| 5 task / 3 host | 2 | 12/15 | 0,2539% | 143,42 giây |
| 5 task / 3 host | 3 | 12/15 | 0,2799% | 302,61 giây |

Mỗi dòng gộp ba instance × năm seed. Các seed lồng trong instance; không xem 15 lượt là 15 bài toán độc lập. Số thành công được đếm trực tiếp từ batch cuối, không suy ra bằng công thức IID từ P_opt gộp của nhiều circuit.

Nếu gộp cả hai quy mô, p1 đạt 17/30, p2 đạt 24/30 và p3 đạt 22/30 batch tối ưu. p2 có số thành công cao nhất trong đợt quan sát này. Đây là kết luận mô tả sau test; không chứng minh p2 tối ưu toàn cục hoặc phù hợp nhất với mọi instance.

## 4. Đối chứng nói gì về hiệu quả thuật toán?

Hai mốc lấy mẫu có ý nghĩa khác nhau:

- **Lấy mẫu đều trong mã hóa:** lấy đều các bit domain-wall và y. Nhiều bitstring có nhãn host không hợp lệ hoặc biến y không phù hợp. Đây là mốc tham chiếu phân phối của mã hóa.
- **Lấy mẫu placement trực tiếp:** chọn một trong ba host cho mỗi task rồi suy ra y từ các host có task. Cách cổ điển này tránh các nhãn host vô nghĩa và không cần đoán y. Capacity vẫn được kiểm tra; không có phép sửa task để ép khả thi.

| Đối chiếu | Kết quả và cách diễn giải |
|---|---|
| QAOA so với đều trong mã hóa | Lift P_opt trung bình theo nhóm từ 0,8 đến 20,8; 15/18 nhóm cao hơn 1, một nhóm bằng 1 và hai nhóm thấp hơn 1. Có cải thiện ở nhiều nhóm, không đồng đều. |
| QAOA so với placement ngẫu nhiên trực tiếp | Cả 18 nhóm instance/p có P_opt trung bình thấp hơn đối chứng trực tiếp. Không kết luận mọi seed riêng lẻ đều thấp hơn. |
| Batch QAOA thực tế | 63/90 batch có optimum. |
| Batch đều trong mã hóa, kỳ vọng giải tích | Khoảng 43,58/90 batch có optimum nếu lấy 1.024 mẫu IID/batch. |
| Batch placement ngẫu nhiên trực tiếp, kỳ vọng giải tích | Khoảng 89,997/90 batch có optimum. Xác suất từng batch thấp nhất vẫn khoảng 99,9789%. |

Các con số kỳ vọng đối chứng được tính từ duyệt chính xác placement và công thức `1 − (1 − P_opt)^1024`. Chúng không phải số thành công quan sát từ 90 lần chạy đối chứng. Không dùng chúng để tuyên bố kiểm định thống kê đã chứng minh ưu thế hay thất bại trên toàn bộ quần thể bài toán.

Kết quả hiện tại cho thấy QAOA có thể nâng xác suất nghiệm tốt so với lấy bit đều trong một mã hóa lớn. Nhưng trên sáu bài toán này, một cách lấy mẫu cổ điển có tận dụng cấu trúc placement vẫn cho xác suất tốt hơn. **Lift lớn so với mốc bit đều chưa đủ để chứng minh thuật toán hữu ích hơn cổ điển.**

## 5. Thời gian, RAM và lượt chạy lâu

| Chỉ tiêu | Giá trị |
|---|---:|
| Số qubit | 20–25 |
| Tổng thời gian bên trong 90 trial | 12.212,19 giây — 3,392 giờ |
| Tổng thời gian bên trong 18 probe | 142,73 giây |
| Tổng ngân sách tính cho các giai đoạn hoạt động | 12.515,77 giây — 3 giờ 28 phút 36 giây |
| Giới hạn ngân sách | 21.600 giây — 6 giờ |
| Ngân sách còn lại | 9.084,23 giây — 2 giờ 31 phút 24 giây |
| Lượt lâu nhất | 2.173,29 giây — 36,22 phút |
| RSS đỉnh của process theo số đo đã lưu | 702,24 MiB |
| RAM hệ thống khả dụng thấp nhất tại các mốc kiểm tra | 12,01 GiB |
| Tổng số lần đánh giá objective | 3.945; 27–75 mỗi trial |
| Tổng algorithm shot | 4.224.000 |

Không có trial thất bại, interruption đang mở, hoặc chi phí recovery chưa xác nhận. Cả 90 lượt dừng theo thông báo COBYLA đạt giới hạn dưới của bán kính trust region; không lượt nào dùng hết cap200. `optimizer_success=True` chỉ mô tả tiêu chí dừng số học, không chứng nhận optimum toàn cục.

Tổng thời gian theo p là khoảng 21,47 phút ở p1, 48,15 phút ở p2 và 133,92 phút ở p3. p3 đắt hơn nhưng không tăng số batch tối ưu khi gộp toàn bộ instance.

Lượt lâu nhất là `a3_test_n5_1`, p3, seed201, có 63 đánh giá. Khoảng cách giữa log đánh giá 43 và 44 là **1.928,50 giây — 32,14 phút**; khoảng cách lớn thứ hai của lượt này chỉ khoảng 4,69 giây. Điều đó xác định nơi thời gian bất thường xuất hiện, nhưng không xác định nguyên nhân. Không có log đủ để phân biệt máy tạm ngưng, tranh chấp tài nguyên hoặc một lời gọi native bị chậm. Toàn bộ thời gian vẫn giữ trong chi phí, không trừ bỏ hoặc thay bằng kết quả chạy lại.

Ngân sách đo các giai đoạn hoạt động của notebook; thời gian người dùng nghỉ giữa những giai đoạn đã đóng không được tính. Các số RSS là đỉnh trong vòng đời process, có thể gồm hoạt động kernel trước đó; chúng không phải tổng RAM của máy hay phép đo peak riêng biệt cho từng trial. RAM khả dụng được kiểm tra tại các mốc, không phải theo dõi liên tục mọi thời điểm. Không ghi nhận vi phạm resource guard trong dữ liệu đã lưu.

Đối chứng vét cạn chỉ duyệt 3^4=81 hoặc 3^5=243 placement. Thời gian trung vị đã đo khoảng **0,134–0,448 ms** cho một lần giải chính xác. Lấy 1.024 placement ngẫu nhiên mất khoảng **3,17–3,74 ms**. Trong khi đó, trung vị QAOA theo từng nhóm instance/p là **4,08–512,27 giây**, đã gồm tối ưu, lấy mẫu và xử lý đầu ra.

Đo cổ điển chạy trong process đã khởi động: có validation, RNG khi cần, kiểm tra và tạo đầu ra; không tính imports, calibration và chuẩn bị reference. Vì phạm vi đo khác với khởi chạy một ứng dụng hoàn chỉnh, không nên đưa ra một hệ số speedup end-to-end chính xác. Tuy nhiên, ở cấu hình mô phỏng hiện tại, dữ liệu không cung cấp bằng chứng QAOA nhanh hơn các đối chứng này.

## 6. Vì sao giảm năng lượng chưa giúp đều cho placement?

Một ví dụ rõ là `a3_test_n5_2`: từ p2 sang p3, năng lượng batch cuối trung bình giảm từ **234,91 xuống 139,97**, nhưng P_opt giảm từ **0,1953% xuống 0,0977%**, còn một nửa. Số batch tối ưu vẫn là 3/5 ở cả hai p. Hiện tượng tương tự xuất hiện ở n4_2 và n4_3; n5_3 có năng lượng giảm mạnh ở p3 nhưng P_opt trung bình không tăng.

Tính lại năng lượng từ raw counts cho thấy phần phạt capacity/slack chiếm khoảng **97,28% tổng năng lượng trung bình cộng của 90 batch**. Phần này chứa bình phương sai số giữa usage, slack và capacity nhân y; nó gộp cả vi phạm tài nguyên/bật host và slack không khớp. Không diễn giải 97,28% là chỉ do slack “lãng phí”.

QAOA tối ưu sampled mean-energy của toàn bộ bitstring, trong khi chỉ tiêu đầu ra là placement khả thi có ít host nhất trong batch. Hai đại lượng liên quan nhưng không đồng nhất. Có **8 final shot đạt trạng thái nền QUBO**, trong khi 63 batch có placement vật lý tối ưu. Sự khác biệt phù hợp với việc nghiệm placement tốt không nhất thiết có slack đúng.

Đây là chẩn đoán từ dữ liệu và cấu trúc objective. Nó chưa chứng minh mean-energy là nguyên nhân duy nhất, và chưa chứng minh thay mixer, CVaR hoặc penalty sẽ cải thiện. Các thay đổi đó cần một nghiên cứu riêng với giao thức cố định trước khi chạy.

## 7. Vị trí của nhánh A và bước tiếp theo

| Mục tiêu | Trạng thái sau Notebook 20 |
|---|---|
| QUBO/Ising và kiểm tra tính đúng đắn trên bộ test hiện tại | Đạt: chứng chỉ mô hình và audit vật lý khớp reference. |
| Thực nghiệm QAOA p1/p2/p3, nhiều seed, 4–5 task / 3 host | Đạt: đủ 90 lượt trên sáu instance đã cố định. |
| Thực nghiệm phù hợp máy cá nhân | Đạt trong campaign này: 20–25 qubit, hoàn tất trong ngân sách và không ghi nhận vi phạm guard. |
| Chất lượng gần optimum | Đạt mức quan sát: 70% batch có optimum; đầu ra trung bình 2,3 host so với optimum 2. |
| Nhanh hơn cổ điển hoặc chất lượng tốt hơn đối chứng trực tiếp | Chưa đạt trên dữ liệu này. |
| Báo cáo toàn bộ đề cương | Chưa thể chứng nhận chỉ từ Notebook 20: phần so sánh FF/BFD/MILP không có trong campaign này. |

Đề cương có phạm vi 4–8 task, 2–4 host và thừa nhận QAOA có thể không thắng MILP/BFD ở bài toán nhỏ. Campaign này cung cấp một nghiên cứu trong phần 4–5 task/3 host; không xem đánh giá tài nguyên lý thuyết là đã chạy thực nghiệm 8 task/4 host. Ngoài ra, penalty trong đợt này được cố định; campaign này không thay thế một nghiên cứu độ nhạy penalty nếu phần đó cần được nghiệm thu theo đề cương.

**Khuyến nghị:** giữ nguyên kết quả Notebook 20, kết thúc đợt test ba host v1 và chuyển sang viết phần kết quả, thảo luận, giới hạn và kết luận nhánh A. Không cần chạy lại Notebook 20 hay mở thêm sweep để tìm một lần thắng đối chứng. Việc hoàn tất campaign là có cơ sở; việc tuyên bố hoàn tất mục tiêu cạnh tranh tốc độ thì chưa có cơ sở.

Phần tiếp theo của nhánh A nên gồm: bảng kết quả trên cùng dữ liệu; giải thích encoding và quy tắc chọn đầu ra; chi phí mô phỏng; đối chứng giải tích cùng phạm vi đo thời gian; hiện tượng năng lượng/placement; đối chiếu từng mục đề cương với bằng chứng đã có. Không triển khai phần của nhánh B hoặc C trong bước này. FF/BFD/MILP chỉ cần được ghi là chưa nằm trong bằng chứng của Notebook 20; không gán kết quả của chúng khi chưa có dữ liệu.

Một phát biểu phù hợp cho kết luận thực nghiệm là: “Trên sáu instance 4–5 task/3 host, mô phỏng QAOA hoàn tất 90 lượt trong giới hạn tài nguyên, luôn tìm được placement khả thi và đạt optimum ở 70% batch. QAOA cải thiện xác suất nghiệm tối ưu so với lấy bit đều ở phần lớn nhóm, nhưng chưa vượt lấy mẫu placement trực tiếp và giải chính xác cổ điển. Tăng độ sâu làm tăng chi phí và không cải thiện đồng đều; giảm mean-energy không đảm bảo tăng xác suất placement tối ưu.”

## 8. Giới hạn của kết luận

Sáu instance được chọn từ một pool có điều kiện; chỉ có ba instance cho mỗi quy mô. Seed đo độ biến thiên trong instance, không tạo thêm độ đa dạng bài toán. Không suy ra ưu thế trên quần thể, định luật scaling, hoặc tác động riêng của tăng task khi độ khó instance cũng thay đổi. Các kết quả hai host trước đây không phải đối chứng chỉ thay số host cho đợt này.

Audit không chạy lại training. Raw counts của từng callback training không được lưu đầy đủ nên không tái tạo độc lập mọi phương sai trong training. Kiểm tra xác nhận tính nhất quán của dữ liệu, mã nguồn và phép giải mã vật lý; không xác nhận tối ưu toàn cục của optimizer. Không có thực nghiệm phần cứng lượng tử hoặc chứng minh quantum advantage.

Nguồn chính: archive và notebook Notebook 20 do người dùng cung cấp, `test_results.csv`, `summary.json`, `controls.json`, `classical_timings.json`, `frozen_context.json`, 108 raw report và 21 module nguồn trong archive; đối chiếu phạm vi với `09-nt409-topic16-proposal.pdf`.
