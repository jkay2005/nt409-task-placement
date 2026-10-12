# Kiểm chứng phần mềm Notebook 17

97 tests: PASS, không skip. Trong container Linux này, PID namespace khác
procfs; trình kiểm thử ánh xạ psutil.Process() không đối số tới PID đọc từ
/proc/self để đo RSS thật cho module cũ. Không thay source module cũ, không
giả lập RAM khả dụng và không bỏ các kiểm thử guard. Module mới đọc
/proc/self trực tiếp qua bộ theo dõi RAM sẵn có.

Đã chạy tuần tự cả tám code cell, 9 probe, 45 lượt compact chính và một
negative smoke, với cấu hình đầy đủ. Đây là kiểm chứng Linux, không phải
campaign Windows của Khiêm. Chỉ thay IPython.display bằng in văn bản vì
môi trường kiểm chứng không có Jupyter/IPython; đồ thị dùng backend Agg.

ZIP baseline người dùng được audit lại theo hash và từng báo cáo thô.
13 module lịch sử khớp nguồn đã chạy, cho phép khác line ending. Bảng/biểu
đồ và ZIP xuất ra đã qua audit. Không trộn báo cáo Linux vào ma trận Windows.

Các đường dẫn tuyệt đối trong log/JSON là đường dẫn môi trường kiểm chứng.
Chạy file notebook sạch trong notebooks/ theo README gốc để tạo campaign mới.
