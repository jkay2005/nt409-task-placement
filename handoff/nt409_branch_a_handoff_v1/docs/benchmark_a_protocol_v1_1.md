# Protocol A v1.1 — thời gian chạy và phạm vi nghiệm thu

Ngày 10/10/2026. Phụ lục này kế thừa dữ liệu và quy tắc QAOA của
`docs/unified_benchmark_v1.md`; khi khác nhau, phụ lục này có ưu tiên cho nhánh A.
Manifest mới lưu hash của cả phụ lục và đặc tả gốc. Bản v1 được giữ nguyên.

## Thay đổi duy nhất về ngân sách QAOA

`qaoa.max_seconds`: **600 → 2400 giây**, áp dụng đồng đều cho p=1,2,3 trên
mọi instance, kể cả smoke. Cap 200, shots 1024, seed 70–74, seed cuối
100070–100074, penalty (3,3), sampled mean, max_abs và các điểm đầu giữ nguyên.
Smoke vẫn dùng cap8/shots64 như v1. Ma trận chính thức vẫn là 45 lượt.

Lý do là probe tài nguyên trước campaign chính thức: trên máy kiểm thử Linux,
ước lượng có hệ số dự phòng 1,5 cho reference 23 qubit đạt khoảng 1800 giây
ở p2 và 2301 giây ở p3 nếu dùng hết 200 đánh giá. Bản 600 giây sẽ chặn các
cấu hình này trước tối ưu. Đây là điều chỉnh khả năng thực thi dựa trên timing,
không phải điều chỉnh theo chất lượng nghiệm. Một lượt kiểm chứng p3 sau đó
hội tụ sau 53 đánh giá; số này không đảm bảo các seed khác đều dừng sớm.

2400 giây là ngưỡng được kiểm tra tại ranh giới đánh giá và phép đo cuối,
không phải ngắt cưỡng bức của hệ điều hành. Ngưỡng tính từ trước khởi tạo
backend/optimizer tới sau phép đo cuối. Chi phí tạo QUBO/reference trước runner,
giải mã và audit nằm ngoài time guard và phải được báo riêng. Một lời gọi
native đang chạy có thể vượt ngưỡng trước khi điều khiển trở về Python.

Probe trên máy Windows của Khiêm vẫn bắt buộc. Không dùng kết quả probe Linux
để bỏ qua kiểm tra Windows. Nếu probe vượt 2400 giây hoặc thiếu RAM thì lưu
partial, xử lý nguyên nhân hoặc xem xét phiên bản protocol tiếp theo; không tự
giảm shots/cap hoặc tăng time guard trong một campaign đã tạo.

## Phạm vi đang triển khai: chỉ nhánh A

Theo yêu cầu hiện tại, Notebook16 chỉ thực hiện QUBO/Ising/QAOA và các phép
kiểm tra tham chiếu nhỏ phục vụ tính đúng. Những định nghĩa baseline trong
đặc tả v1 được giữ làm lịch sử; gói này không triển khai hay chạy B/C, và việc
nghiệm thu A không phụ thuộc trạng thái B/C.

Điểm dừng A: audit đủ 45 lượt chính thức có dữ liệu hợp lệ, kiểm tra vô nghiệm
riêng, bảng theo instance/p/seed, chi phí, mode và best-valid, cùng gói tái lập.
Một lượt completed có 0 mẫu hợp lệ vẫn là kết quả phải giữ. Các lượt resource,
time, error hoặc interrupted phải có trạng thái riêng; campaign chưa đủ 45
completed được ghi PARTIAL, không tuyên bố đã hoàn tất. Không thêm sweep chỉ
vì kết quả thấp. Hoàn tất A không đồng nghĩa tuyên bố toàn bộ đồ án/nhóm đã xong.

Đầu vào vẫn là bốn JSON gốc cùng SHA256, 4 task/2 host, 18–23 qubit. Không ghép
kết quả notebook06–15 hay dữ liệu kiểm thử Linux vào ma trận xác nhận Windows.
Tình trạng thực thi nằm trong campaign, không suy từ trường mô tả thiết kế
`status` của protocol đã khóa.
