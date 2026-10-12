# Kiểm chứng bàn giao notebook 13

Đây là dữ liệu kiểm chứng phần mềm trên Linux, không thay thế hai lượt đối chứng Windows của người dùng.

- Đã chạy tuần tự toàn bộ 10 code cells với cấu hình mặc định: 2 lượt exact, p1_choice 20 qubit, 1024 shots cuối, maxiter=200.
- Môi trường không có Jupyter/IPython. Bộ kiểm chứng dùng Python với bộ chuyển đổi riêng cho display để in bảng; mọi phép tính chạy nguyên văn. Không tuyên bố đã chạy bằng Jupyter kernel.
- Common dừng số học sau 112 đánh giá; alternative sau 107. Năng lượng lần lượt 59.29362411064877 và 59.29362362435783.
- P_opt lý tưởng lần lượt 0.1257778983% và 0.1257792076%; sample cuối lần lượt có 0 và 4 nghiệm tối ưu trong 1024 shots. Không loại kết quả zero-success.
- Resume tải manifest, xác minh và bỏ qua hai lượt đã lưu; thời điểm sửa đổi của các report không thay đổi.
- Baseline Windows dùng SciPy 1.18.1, NumPy 2.5.3; kiểm chứng Linux dùng SciPy 1.17.0, NumPy 2.3.5. Không quy toàn bộ chênh lệch với Windows cap80 cho ngân sách.
- `placement.py` chỉ khác kiểu xuống dòng LF/CRLF, đã đối chiếu hai SHA256 tương ứng. Nội dung mã lõi không thay đổi.
- `verification.json`: cấu hình môi trường, bảng so sánh và kết quả resume. Đường dẫn tuyệt đối trong file này thuộc môi trường kiểm chứng.
- `linux_exact_budget_reports.zip`: manifest, 2 report đầy đủ, CSV. Dữ liệu ở đây phục vụ kiểm chứng; không giải nén đè vào campaign Windows.
- `budget_traces.png`: đồ thị quỹ đạo; `tests.log`: kết quả bộ kiểm tra tự động.
