# Protocol kiểm chứng 5×3 — chốt trước khi chạy QAOA mới

Ngày 25/10/2026. Giữ a3_dev_n5 làm development; bổ sung đúng ba instance kiểm chứng, tất cả 5 task × 3 host và 25 qubit. Đây là mẫu tổng hợp có điều kiện, không đại diện mọi workload thực tế.

## Quy tắc chọn dữ liệu

1. Duyệt hết multiset 5 demand trong {1,2,3}² và multiset 3 capacity trong {2,3}². Không giới hạn tổng demand ≤6 như bộ cũ. Capacity 2/3 giữ đúng hai bit slack mỗi resource/host.
2. Giữ instance có nghiệm, ít nhất hai loại task và hai loại host, đồng thời có assignment qua CPU nhưng trượt RAM và assignment qua RAM nhưng trượt CPU. Hai ràng buộc do đó không suy ra nhau trên toàn bộ 243 assignment.
3. Loại tương đương do hoán vị task/host hoặc đổi CPU↔RAM; loại chữ ký của các input lịch sử 5×3 đã thu được trong snapshot A/B (lưu danh sách loại trừ).
4. Chia ba tầng: optimum=2; optimum=3 với số assignment khả thi ở nửa dưới; optimum=3 ở nửa trên. Chia nửa bằng thứ tự (số khả thi, chữ ký), floor(N/2). Chọn một phần tử mỗi tầng có SHA256({seed:20261025, signature:…}) nhỏ nhất. Không dùng QAOA, FF hay BFD để lọc/chọn. Nghiệm tối ưu chỉ dùng định nghĩa tầng và chấm điểm.
5. Xáo trộn thứ tự task/host một lần bằng Random(20261025+k), k=0,1,2 theo thứ tự tầng; khóa thứ tự cho mọi thuật toán. Không thử nhiều thứ tự rồi lấy kết quả đẹp.

Đây là lựa chọn dự kiến trước kết quả QAOA trên các instance mới, không phải preregistration công khai hay kiểm định mù. Với ba instance và một lần khởi tạo, chỉ kết luận trên từng case; seed huấn luyện không làm tăng số instance độc lập. Optimum=3 khiến mọi placement khả thi đều tối ưu theo mục tiêu số host; phải đọc P_valid/P_opt cùng nhau và giải thích điều này.

## T4 dự kiến được khóa trong bước này

Ba nhánh standard_x, valid_x, valid_dw; penalty domain/capacity=4; exact ideal Aer double CPU, 4 threads, RAM còn tối thiểu4GiB; mean-energy + COBYLA, max_abs Hamiltonian. Mỗi instance/nhánh: p1 bắt đầu [0.3,1.0], tối đa100 lời gọi objective; p2 INTERP từ góc mean-energy tốt nhất p1, tối đa100 lời gọi. rhobeg=1, tol=1e-4; giới hạn thời gian mỗi stage2400giây; báo nếu ngừng sớm. Không chọn góc theo P_opt. Không tái dùng kết quả huấn luyện lịch sử làm một nhánh miễn phí. Tính cả p1, setup, final scoring và mọi simulation ngoài optimizer; cap bằng nhau không đồng nghĩa thời gian bằng nhau.

Trước hết chạy ba nhánh trên development (600 objective evaluations). Sau khi xác minh phần mềm/ngân sách, chạy nguyên cấu hình trên ba instance mới (1800 objective evaluations). Tổng tối đa2400 objective evaluations, cộng preflight/scoring/shots, dự kiến nhiều giờ trên Windows; không hứa thời gian từ một phép đo. Nếu thay phương pháp sau khi xem validation, đánh dấu validation đã dùng phát triển và báo thay đổi. Không tự tăng cap/chọn seed hoặc bỏ case thất bại.

Depth p1 là chuẩn bị có trả chi phí; p2 là kết quả chính với tổng cap200. Báo các bước bị lỗi, nfev/cap, trạng thái dừng, runtime, P_domain/P_valid/P_opt/P_ground/mean-energy. Thêm final sampling1024 shot với seed20261025+k theo thứ tự instance, dùng cùng seed giữa nhánh chỉ để tái lập; exact metrics là chính, counts là minh họa. Chưa thực hiện optimizer trong Notebook26.

## Kiểm toán trước huấn luyện

Notebook26 tái tạo pool và chọn mẫu; kiểm hash/input/thứ tự; vét cạn243 assignment; kiểm QUBO/Ising trên326 vector cơ sở bậc2; giải chính xác slack cho8192 base. Uniform encoded giữ y đo được; random host assignment suy y là control khác. FF/BFD dùng nguyên source Notebook21; MILP vẫn chờ bước T5 với solver/version/status được ghi riêng. Không gọi vét cạn là MILP. Không đo tốc độ thuật toán từ một lần kiểm toán.

Protocol này thay điều khoản “chỉ một exact input cho toàn study” trong kế hoạch cũ. Trong mỗi phép so sánh, mọi phương pháp phải dùng cùng input/hash; kích thước 5×3 cố định từ đầu đến cuối. Artifact T2 và Notebook22–25 vẫn đúng cho a3_dev_n5; không sửa kết quả cũ.
