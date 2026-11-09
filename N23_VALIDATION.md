# Phạm vi kiểm chứng Notebook 23

Ngày kiểm chứng: 2026-10-23. Bản bổ sung dựa trên Notebook 22 v2, commit `101376c`, tag `notebook22-v2.0.0`. Không thay module mô hình, encoding, mixer, optimizer hay input cũ. Gói này thêm module campaign, protocol, test, notebook và ba tài liệu.

## Kiểm thử tự động

- Bộ test A hiện có và test mới: **151/151 PASS**, chạy trong 37.640 giây tại môi trường kiểm chứng Linux.
- Trong đó có **9 test mới** cho Notebook 23: INTERP đúng thứ tự beta/gamma, plan và RNG tái lập, ngân sách bằng nhau, chọn theo năng lượng thay vì P_opt, tạo/chạy/resume campaign, tính phí và hash giai đoạn chuẩn bị, profile không tối ưu, giữ lượt lỗi thay vì reset ngân sách, phát hiện protocol/report bị thay đổi và audit/export.
- Fixture nhỏ trong test chỉ kiểm chứng logic phần mềm. Không dùng kết quả fixture làm kết luận về chất lượng QAOA trên bộ quy chiếu.

## Kiểm tra luồng notebook trên input thật

Đã chạy tuần tự **9 ô mã** qua IPython trên đúng input a3_dev_n5, 5 task + 3 host, **25 qubit**. Bản kiểm chứng riêng dùng `software_validation=True`, cap tổng 12, cap mỗi giai đoạn 6, một seed 400 và chỉ chọn nhóm INTERP p=2. Hai giai đoạn p=1 mới → p=2 đều chạy; profile ở cả hai độ sâu, bảng, biểu đồ, replay endpoint, audit và export chạy thành công. Batch cuối vẫn có 1024 shots mỗi lượt.

Audit báo PASS, nhưng campaign QA là **partial: 1/5 nhóm**, không phải campaign chính 13 nhóm/24 lượt. Số 5 thuộc protocol QA đã rút còn một seed; không thay đổi kế hoạch chính. Kết quả này kiểm tra khả năng thực thi và kế toán ngân sách, không chứng minh INTERP hoặc multistart cải thiện P_opt.

## Giới hạn kiểm chứng

Môi trường kiểm chứng dùng Linux, Qiskit 2.5.2, Aer 0.17.2, NumPy 2.3.5, SciPy 1.17.0. Chưa chạy lại toàn bộ 2600 đánh giá tiềm năng của protocol chính. Chưa xác minh giao diện Jupyter/Windows trực tiếp. Do môi trường kiểm chứng trước đó có giới hạn socket khi khởi tạo kernel, lần này chạy mã ô bằng IPython; không tuyên bố đã chạy Jupyter kernel qua giao diện. Máy người dùng có runtime khác sẽ được ghi lại trong campaign và không được gộp âm thầm với dữ liệu QA.

Thời gian/RAM guard chỉ kiểm tra giữa các lời gọi native, không bảo đảm ngắt cứng giữa một phép mô phỏng Aer. Trần 200 là số đánh giá hàm huấn luyện mỗi chiến lược, không phải toàn bộ backend calls hoặc thời gian bằng nhau. Replay audit kiểm các góc cuối; không tái chạy toàn bộ đường optimizer.

## Nội dung bàn giao

Notebook bàn giao có execution_count=None và output rỗng, protocol chính có software_validation=False, cap 200/100 và năm seed 400–404. Gói không chứa raw report, notebook đã chạy hoặc biểu đồ của QA; cũng không chứa kết quả người dùng từ Notebook 22. SHA256SUMS.json xác nhận nội dung các file trong gói. Giải nén bổ sung lên repo đã có Notebook 22 v2, rồi chạy 9 test mới trước khi Run All.

Khi đọc kết quả thật, audit PASS chỉ xác nhận nhất quán; complete=True xác nhận đủ kế hoạch. Chỉ so sánh P_opt/P_valid/năng lượng sau khi có dữ liệu chạy chính, đồng thời xem nfev và phạm vi seed.
