# Kiểm chứng Notebook 24

Ngày kiểm chứng: 2026-10-24. Bản bổ sung dựa trên Notebook23 v1.0.0, commit `b45c5f3`, tag `notebook23-v1.0.0`. Gói chỉ thêm file mới; các module mô hình/encoding/mixer/optimizer và nguồn Notebook23 giữ nguyên để không phá resume của campaign cũ. Không thêm dependency.

## Kiểm thử tự động

**159/159 test PASS**, thời gian 41.527 giây trong môi trường kiểm chứng Linux; gồm151 test cũ và8 test mới.

Tám test mới kiểm tra: kế hoạch sáu lượt/ba nhóm với cap200, p=1 mới dùng mean ở cả ba nhóm; CVaR có phần biên/đồng năng lượng/zero-mass/alpha1 và alpha không hợp lệ; histogram so với phép tính từng trạng thái; tạo/chạy/resume và hash parent INTERP; mean-control khớp code train cũ trên fixture; lỗi giữa huấn luyện giữ history; profile không tính vào training và resume không chạy lại; reservation trước native work, không tự reset lượt lỗi, chạy nhóm khác; từ chối nguồn/protocol/report bị sửa, kể cả report CVaR được tính lại hash sau khi giả mạo.

Fixture nhỏ trong test chỉ dùng kiểm chứng logic phần mềm, không thuộc dữ liệu nghiên cứu. Kết quả fixture không phải bằng chứng cải thiện QAOA trên input chính.

## Kiểm tra mã notebook với mạch thật25 qubit

Đã chạy tuần tự **cả9 ô mã** bằng IPython trên đúng a3_dev_n5:5 task +3 host,25 qubit. Bản QA riêng có software_validation=True, cap12 mỗi nhóm=6chuẩn bị+6đích; chạy đủ cả ba objective. Có ba nhóm/sáu lượt optimizer, tối đa36 đánh giá huấn luyện QA. Mỗi lượt vẫn có batch1024shots cuối.

Đã kiểm tra profile, huấn luyện, parent INTERP, bảng chấm chéo, biểu đồ, replay endpoint/mean/CVaR và export. Audit QA: PASS, complete=True, common_p2_start=True. Complete này chỉ nói đủ **kế hoạch QA cap12**, không phải đã chạy kế hoạch chính cap200. Đã xem biểu đồ để kiểm tra nhãn QA và đơn vị xác suất.

## Giới hạn

Kiểm chứng trên Linux, Qiskit2.5.2/Aer0.17.2, NumPy2.3.5/SciPy1.17.0. Chưa chạy toàn bộ kế hoạch chính tối đa600 đánh giá. Chưa xác minh trực tiếp giao diện VS Code/Jupyter trên Windows. Mã ô được chạy qua IPython, không tuyên bố đã chạy notebook bằng kernel Jupyter qua giao diện; môi trường kiểm chứng trước có giới hạn socket khởi tạo kernel.

Mean alpha1 giữ số học kỳ vọng cũ; test đối chiếu xác nhận điểm/giá trị/endpoint/counts trùng trên fixture. Điều này kiểm tính tương thích phần mềm, không bảo đảm mọi máy cho cùng đường đi optimizer đến từng bit. Runtime thực tế được ghi trong campaign; resume từ chối đổi runtime/input/nguồn/protocol.

Time/RAM guard kiểm giữa các lời gọi native; không ngắt cứng một lời gọi Aer. CVaR dùng thêm histogram và index mức năng lượng. Trần bằng nhau là trần đánh giá hàm huấn luyện; chi phí profile/chấm/audit nằm ngoài trần và không dùng chọn góc. Replay audit kiểm endpoint, không chạy lại toàn bộ đường optimizer và không chứng minh tối ưu toàn cục.

## Bàn giao

Notebook gốc có execution_count=None/output rỗng; protocol chính software_validation=False, cap200/100 và alpha[1,0.25,0.10]. ZIP chỉ có source mới, protocol mới, test mới, notebook và ba tài liệu, kèm SHA256SUMS.json. Không chứa raw report, notebook đã chạy, biểu đồ QA hoặc kết quả lịch sử Notebook23.

Sau khi giải nén vào repo đã có Notebook23, chạy8 test mới rồi Run All. Gửi notebook có output cùng cvar_<timestamp>.zip. Chỉ dữ liệu chạy chính mới dùng kết luận mean hay CVaR tốt hơn trên bộ quy chiếu. Nếu P_opt không tăng, báo kết quả âm; không thay alpha, xóa nhóm kém hoặc chỉ chọn chỉ số đẹp để tuyên bố thành công.
