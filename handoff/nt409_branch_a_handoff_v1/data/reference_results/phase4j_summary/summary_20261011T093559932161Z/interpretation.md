# Notebook 18 — hướng dẫn diễn giải

- quantum_groups.csv: tỷ lệ mẫu tối ưu/khả thi; SD giữa các seed; số lượt tìm thấy nghiệm.
- controls.csv: xác suất chính xác của uniform và random task-to-host; cột batch dùng 1024 lần lấy mẫu IID.
- classical_timings.csv: median/min/max từ các block đo trong phiên hiện tại. Đọc block_seconds/calls_per_block.
- summary.json: protocol timing, môi trường mới, nguồn QAOA cũ, preprocessing và giới hạn so sánh.
- Quantum total_seconds không phải toàn thời gian notebook; timing cổ điển không bao gồm import/calibration/exact reference.
- Chỉ đủ bằng chứng cho so sánh mô tả với các triển khai này; không phải so sánh với mọi solver cổ điển.
- Trường hợp vô nghiệm: P_opt không xác định (ô trống/null), P_feasible=0.
- Notebook18 chỉ audit và đo classical. Giữ nguyên mọi kết quả QAOA16/17.
