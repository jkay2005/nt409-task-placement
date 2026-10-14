# Protocol Notebook18 — phase4j_branch_a_summary_v1

Ngày11/10/2026. Nhánh A, bổ sung phép tổng hợp và đo classical vào thí nghiệm mã hóa đã hoàn tất. Input mặc định là nguyên archive Windows17 có baseline16 lồng bên trong. Không thay input, source module lịch sử hoặc output rule của QAOA.

## Audit

Kiểm tra ZIP không có tên trùng/đường dẫn không an toàn, tổng giải nén tối đa512MiB, checksum phủ mọi payload. Đọc trong bộ nhớ, không extract lên repository. Thiết kế phải khớp benchmark đã load bằng manifest v1.1 đóng băng. Kiểm tra ledger, trial, config, source SHA (chấp nhận khác LF/CRLF), dữ liệu mẫu, tham chiếu, năng lượng, output, shot accounting và CSV. Từ chối campaign thiếu lượt chính/negative-control hoặc probe. Các attempt lỗi trước lần thành công được giữ trong archive và ghi số lượng; tổng formal timing chỉ gồm lần hoàn thành được tổng hợp.

Runtime gốc được giữ nguyên; khác runtime hiện tại không tự khiến dữ liệu vô hiệu. Đây là kiểm tra tính nhất quán số học/metadata, không phải chứng thực độc lập quá trình chạy trên máy gốc. Mã tạo16/17 phải khớp nguồn đã ghi nhận, tránh dùng code mới chấm lại dữ liệu cũ mà không biết.

## Đối chứng

Mỗi instance hai host có2^n phân công. Duyệt assignment nguyên thủy, tính tổng CPU/RAM từng host, y bằng host được sử dụng. Phân công quá tải không sửa. Ground truth là min số host trên tập khả thi, không truyền optimum vào solve_classical.

Random assignment: independent uniform host choices,1024 draws, giữ mọi draw, lấy nghiệm khả thi có objective nhỏ nhất; tie giữ ứng viên gặp trước. Exact enumeration: duyệt toàn bộ assignment theo thứ tự từ điển, cùng rule chọn nghiệm. Các solver đều dùng positive-integer CPU/RAM và validation schema của mô hình; tests đối chiếu kết quả với evaluate_placement gốc.

P_opt/P_feasible uniform encoding từ reference đã audit. P_opt structured random từ enumeration không gian assignment, không từ một lượt random được chọn. Exact-reference/infeasible tách rõ None và0.

## Timing

Mặc định blocks7, target_seconds0.02, max_calls4096, random shots1024. Calibration tăng số solve/block theo lũy thừa2 đến mục tiêu hoặc trần; ghi thời gian calibration nhưng loại khỏi median solver. Đo bảy block, chia cho calls/block và báo median/min/max, lưu toàn bộ block_seconds. Seed đo được xác định từ180000+block_index*max_calls+call_index. Calibration và từng block có lịch seed được tái lập trong cùng môi trường.

Không can thiệp GC hoặc trừ empty-loop overhead. Bao gồm input conversion/validation trong solve, RNG và candidate checking/output cùng bookkeeping đo nhỏ. Loại import, calibration, ground truth prep khỏi solver timing. Lặp benchmark không phải lặp training QAOA; tần suất thành công trong các phép đo chỉ là diagnostic, random success chuẩn dùng xác suất chính xác.

Historical QAOA total_seconds từ báo cáo trial, model/reference preprocessing tách riêng. Không phân bổ lại thời gian cache/preprocessing, không xem audit hoặc replay archive là lần giải QAOA mới. Không tính TTS99 từ pooled samples, không đưa tỷ số tăng tốc mang nghĩa end-to-end khi chưa có phép đo tương ứng. So sánh cùng chất lượng phải chỉ rõ xác suất thành công và phạm vi đo; observed5seed không chứng nhận99%.

## Đầu ra và điểm dừng

Xuất92 per-run rows,18 formal groups,12 control rows và6 timing rows, metadata/môi trường/source hash, input nguyên bản, ảnh và checksum. Pooled probabilities dùng tổng count/tổng finalshots; SD dùng các xác suất per-seed. Giữ zero, negative-control và mọi source attempt.

Hoàn tất khi audit đầy đủ, exact controls khớp, timing Windows được ghi và export kiểm tra được. Không mở campaign QAOA/CVaR hoặc benchmark mới trong Notebook18. Đây là đóng phép so sánh của nhánh A, không chứng nhận mọi hạng mục proposal/B/C hoàn tất hoặc quantum advantage.
