# Notebook 21 — Linux QA, không phải benchmark Windows

Kiểm tra ngày 21/10/2026, base Git d88b0af. Mã A/input/protocol lịch sử không thay đổi.

- OR-Tools 9.14.6206, SCIP 9.2.2 / SoPlex 7.1.3; Python 3.12.14 Linux.
- `python -m unittest discover -s tests`: **139 tests, OK**, 40.093s; log: `full_unittest.log`.
- Nhánh B: 11 tests; campaign test chạy đủ 36 lượt chính/180 timing trong thư mục tạm, phát hiện thay input/raw report, kiểm tra export và đường dẫn có dấu cách.
- 7 code cells nguyên bản của Notebook 21 được thực thi tuần tự trong một process IPython; tất cả PASS. Đây không phải lần chạy qua kernel Jupyter: môi trường QA từ chối socket TCP và IPC khi khởi động kernel. Notebook đã kiểm tra schema nbformat và lưu output từng cell.
- Campaign đủ 36/36 quality records, 27 main, 9 controls, 180 timing records, 27 hàng A/B. `milp_certificates_complete=true`.
- MILP: 10 input có nghiệm đều optimal, 2 negative controls đều infeasible; khớp vét cạn độc lập.
- Trên 9 input chính: FF hợp lệ 8/9, tối ưu 3/9; BFD hợp lệ 8/9, tối ưu 2/9; MILP hợp lệ/tối ưu 9/9.
- `classical_quality.png` đã kiểm tra trực quan: không mất nhãn/cắt chữ, số cột khớp summary.
- ZIP raw được kiểm CRC và SHA256 từng member khi export.

`classical_b_linux_qa.zip` chứa toàn bộ raw kết quả QA; hai CSV, summary/audit và ảnh cũng có bản rời trong thư mục này. Notebook output giữ đường dẫn gốc lúc thực thi; sau QA đã giữ archive trong verification, không nhập dữ liệu này vào thư mục kết quả Windows. `notebook_execution.json` ghi cả đường dẫn lúc chạy và sau chuyển.

Lần chạy toàn bộ đầu tiên ghi nhận 5 failures + 1 error ở test_benchmark_a (status error thay completed/interrupted). Kiểm tra cô lập và hai lần chạy có instrumentation không tái hiện; lệnh unittest chuẩn cuối cùng pass 139/139. Chưa xác định nguyên nhân lượt đầu. Không sửa/tắt test A hoặc sửa mã A để làm test qua. Hai diagnostic logs giữ lại để đối chiếu; dòng RuntimeError 'backend failed' trong đó là lỗi giả có chủ ý của test xử lý error, không phải thất bại campaign thực.

Không dùng thời gian Linux này làm thời gian laptop Windows. Không tính quantum speedup. Không đổi thuật toán sau khi thấy chất lượng BFD.
