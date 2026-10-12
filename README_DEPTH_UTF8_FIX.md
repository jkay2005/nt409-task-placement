# Sửa encoding trong test_depth_campaign.py

Nguyên nhân tái hiện: manifest được ghi UTF-8 (ensure_ascii=False), nhưng test đọc
bằng Path.read_text() không chỉ định encoding. Trên locale không mặc định UTF-8,
parameter_names chứa beta/gamma bị đọc sai, khiến kiểm tra Manifest row differs thất bại.

Bản vá chỉ thay tests/test_depth_campaign.py:
- Đọc manifest và report với encoding='utf-8'.
- Ghi report biến đổi dùng cho kiểm thử với encoding='utf-8'.
- Thêm test tái hiện locale cp1252 ngay cả khi chạy trên Linux UTF-8.

Đã tái hiện đúng lỗi trước sửa; trường khác biệt duy nhất là parameter_names.
Sau sửa: toàn bộ 64 kiểm tra đạt trên Linux, gồm test mô phỏng locale không UTF-8.
Chưa chạy trực tiếp trên máy Windows của người dùng.

Cách cài:
1. Giải nén vào thư mục gốc nt409-task-placement, thay tests/test_depth_campaign.py.
2. Trong môi trường Conda nt409-khiem, chạy:
   python -m unittest discover -s tests
3. Kết quả mong đợi: Ran 64 tests ... OK.

Không thay file src/, notebook hoặc dữ liệu. Không cần chạy lại notebook 13.
Các DeprecationWarning/SparseEfficiencyWarning không phải lỗi làm test này thất bại.
verification/depth_utf8_tests.log ghi kết quả kiểm chứng.
