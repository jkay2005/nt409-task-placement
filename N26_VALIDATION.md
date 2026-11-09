# Kiểm chứng gói Notebook26 — 25/10/2026

- RED: test_validation5x3.py thất bại vì module mới chưa tồn tại. GREEN:3 test mới đạt, gồm kiểm CPU dư thừa ở development, tái tạo lựa chọn, kiểm toán bốn case và từ chối ghi đè output.
- Toàn bộ170 unittest đạt trong60,998giây trên Linux; bao gồm167 kiểm thử trước đó. Test lịch sử giữ nguyên; fixture kích thước khác trong regression test không phải instance thực nghiệm mới.
- Đã chạy audit thực trên bốn case, tái tạo toàn pool và kiểm mọi điều kiện. QUBO/Ising sai số tối đa0 trên326 vector/case;8192 base/case được giải slack bằng reference. Oracle vector hóa được đối chiếu validator scalar trên243 assignment/case.
- Đã chạy thật cả sáu ô code của notebook bằng Python trong cùng namespace, có IPython display, audit và xuất ZIP. Không thay bằng kết quả audit có sẵn. Chưa thử GUI Jupyter/Windows trong lượt bàn giao này; người dùng sẽ chạy cùng kernel N25.
- Source classical_baselines.py sao chép nguyên byte từ source snapshot Notebook21 B, không thay định nghĩa FF/BFD. solve_milp được giữ nguyên với import OR-Tools trì hoãn nhưng không gọi trong N26. Không có kết quả MILP mới.
- Không optimizer/statevector, không số đo peakRAM hay benchmark timing. Số thời gian FF/BFD trong JSON là telemetry một lần, không xếp hạng tốc độ.
- Dataset SHA256 canonical:19bcd132aa4e240220611111dd81190fa21c84842f3c5f2bfb29de036c290758. Đây là hash JSON canonical, khác SHA256 byte của file có thụt lề. Hash module nguồn trong audit chuẩn hóa CRLF→LF để tương thích Windows; SHA256.json trong ZIP kiểm byte file thực tế.
- Gói thêm hai module, một test, notebook, dữ liệu và tài liệu. Không đổi guard exact-input ở module T3 và không sửa Notebook22–25. Gói phải giải nén lên repo N25 có đủ dependency/module cũ; không phải repo độc lập.

Quy tắc chọn đã ghi trước khi chọn mẫu và không chạy QAOA trên mẫu mới. Chỉ là đóng băng nội bộ; không khẳng định preregistration công khai hay test mù. Cỡ mẫu kiểm chứng là3, không tính development hoặc seed thành instance độc lập.
