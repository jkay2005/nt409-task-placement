# Kiểm chứng Linux notebook 14

- Toàn bộ 72 test đạt; 8 test CVaR mới gồm biên phân phối, alpha=1, affine scaling,
  statevector độc lập, runner mean-equivalence, report identity và resume/tamper.
- Đã chạy 2 lượt default choice20qubit, alpha0.1, maxiter200, final1024shots.
- Common dùng hết 200 đánh giá; alternative dừng số học sau 178.
- Chạy 10 code cells nguyên phép tính bằng Python với display-only adapter.
  Môi trường không có Jupyter/IPython nên không tuyên bố kiểm thử giao diện kernel.
- Reload manifest và chạy lại loop xác nhận không sửa/khởi chạy lại report đã hoàn tất.
- Audit cuối tính CVaR từ vector đầy đủ bằng ngưỡng phân vị/phần khối xác suất tại biên,
  độc lập với cách gộp các mức năng lượng trong runner. Hai giá trị đều khớp.
- Tái lập batch đo cuối bằng seed100060 khớp toàn bộ bảng đếm.
- Môi trường khác baseline Windows: SciPy1.17.0 thay vì1.18.1, NumPy2.3.5 thay vì2.5.3.
  Các so sánh Linux/Windows chỉ phục vụ kiểm chứng, chưa thay thí nghiệm cùng môi trường.
