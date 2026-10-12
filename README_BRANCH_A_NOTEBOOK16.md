# Bắt đầu Notebook16 — chỉ nhánh A

Đây là gói bổ sung cho repo đã chạy Notebook15, không phải một repo độc lập.

1. Merge `src`, `tests`, `notebooks`, `docs`, `data`, `tasks` vào thư mục gốc
   `nt409-task-placement`. Giữ các notebook/report trước đó.
2. Trong môi trường `nt409-khiem`, chạy `python -m unittest discover -s tests`.
   Với bộ hiện tại, mong đợi87 tests và OK.
3. Mở `notebooks/16_qaoa_unified_benchmark_a.ipynb`, chọn đúng kernel, Restart
   Kernel, chạy lần lượt8 bước. Lưu đường dẫn RESUME_DIR ở bước2.

Hướng dẫn đầy đủ: [docs/benchmark_a_runbook.md](docs/benchmark_a_runbook.md).

Thiết kế: cùng input v1, protocol A v1.1,45 lượt QAOA +1 smoke vô nghiệm riêng.
Time guard2400 giây/lượt áp dụng đều cho p1/2/3. Có probe RAM/thời gian trước
campaign, tự lưu từng lượt và resume; không chạy lại completed để chọn kết quả.

Gửi ZIP được bước8 in ra và notebook executed. Nếu bị chặn, gửi ZIP partial.
Chỉ nghiệm thu dữ liệu A khi đủ45 lượt và qua audit; không phụ thuộc B/C.

Thư mục `validation/branch_a_v1_1/` trong gói chỉ chứa bằng chứng kiểm chứng
Linux của người triển khai. Không nhập các báo cáo này vào campaign Windows
hay coi chúng là một phần45 lượt chính thức.
