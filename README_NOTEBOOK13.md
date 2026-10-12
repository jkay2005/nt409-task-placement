# Cập nhật notebook 13 — exact choice 80 → 200

Giải nén vào thư mục gốc nt409-task-placement (cùng cấp src/, notebooks/, docs/).
Mở docs/qaoa_exact_budget.md để xem hướng dẫn đầy đủ.

1. Cập nhật module campaign và hai file kiểm tra từ gói.
2. Chạy: python -m unittest discover -s tests
3. Mở notebooks/13_qaoa_exact_budget_choice.ipynb; chọn kernel notebook 12; Restart Kernel.
4. Giữ RESUME_MANIFEST=None, MAX_EVALUATIONS=200; chạy Bước 1–10.
5. Save As: 13_qaoa_exact_budget_choice_executed.ipynb.
6. Gửi notebook có output và ZIP exact_budget_choice_<timestamp>.zip do Bước 10 tạo.

Gói gồm bản gốc manifest và 8 report choice ngày 08/10 để đối chiếu tự động.
Không cần chạy lại sampled hoặc reference. Không dùng manifest cap80 để resume cap200.

63 kiểm tra tự động đạt. Toàn bộ 10 code cells và 2 lượt đầy đủ đã chạy bằng Python
trong kiểm chứng Linux; display được chuyển sang in bảng, không phải một lượt Jupyter kernel.
Resume đã xác nhận không chạy lại report đã lưu. Dữ liệu Linux nằm riêng ở
verification/notebook13/, không thay thế thí nghiệm Windows của bạn.
