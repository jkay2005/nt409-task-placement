# Kiểm chứng N27 — T4b development

Ngày25/10/2026. Giữ5task ×3host/25qubit. Gói chỉ thêm file lên N26; không sửa source N22–26 hoặc dataset/protocol đã khóa.

## Phần đã kiểm chứng

- RED: test import module ledger mới thất bại, sau đó đạt3 test ledger. RED cho runner/export/open_campaign mới chưa tồn tại, sau triển khai đạt8 test mới.
- Toàn bộ178 unittest đạt trong45,608giây trên Linux. Không giảm fixture coverage, không tắt warning/skip test cũ để lấy OK. Test điều khiển campaign dùng evaluator double rẻ ở boundary mô phỏng, không tạo bài toán placement nhỏ hơn.
- Test mới kiểm cap600 chính thức và cap36 chỉ-QA tách biệt; INTERP từ đúng p1; chọn điểm bằng mean-energy; tính cả preparation; stage hoàn tất không chạy lại; evaluation lỗi đã được cấp không reset; chặn runner thứ hai; input/raw report/ledger/runtime thay đổi bị từ chối; con trỏ notebook không tạo campaign mới khi chạy lại.
- Bảy ô code N27 đều parse được; notebook bàn giao không chứa output. Đã thực thi cả bảy ô bằng Python/IPython trên worktree N26 sạch được overlay gói, với simulation boundary double. Kết quả kiểm luồng đó không phải số liệu quantum, không bàn giao làm kết quả chính. Chưa chạy GUI VS Code/Jupyter Windows.

## Kiểm tra Aer thật

Lượt qualification riêng dùng a3_dev_n5 với đầy đủ25qubit, ba nhánh×p1/p2, cap6 objective evaluations/stage. software_validation=True được ghi trong identity/summary; không dùng con trỏ N27 chính. Đây là kiểm thử phần mềm, không phải thí nghiệm cap100/stage đã khóa cho người dùng.

Bắt đầu một stage, gọi lại runner để kiểm resume năm stage còn lại. Từng stage tính mean-energy, chọn best quan sát, replay exact metrics; p2 thêm1024shot cuối. Tất cả objective attempts được ghi trước native call và kết quả được checkpoint sau native call. Lịch sử failed/in_flight không bị cấp mới trên resume.

Số đo và kết luận PASS của lượt qualification được ghi trong báo cáo T4B_CHUAN_BI_NOTEBOOK27.md khi lượt chạy hoàn tất. Không dùng metric của cap6 để chọn mixer hay tune cap100. Chưa chạy đủ600 objective evaluations của campaign chính thức tại bước bàn giao; lượt Windows cần được người dùng thực hiện và đánh giá riêng.

## Chi phí và giới hạn

Cap600 chỉ là objective calls. Nếu sáu stage hoàn tất, có6 final-exact và3 final-sampling calls bổ sung, tối đa609 calls tổng cộng khi objective đạt cap. Raw reports lưu riêng calls đã cấp và completed_objective_calls. Một call chưa có kết quả sau crash vẫn được coi đã cấp; không khẳng định nó đã hoàn thành.

Source/runtime/dataset guard tính cả tất cả src/*.py và phiên bản thực tế; không cập nhật code/package giữa campaign. Checkpoint evaluation không khôi phục được trạng thái nội bộ SciPy COBYLA giữa stage; chỉ tự tiếp tục stage chưa bắt đầu sau các stage hoàn tất. Guard RAM/thời gian kiểm giữa native calls, không ngắt cưỡng bức.

Stage completed không khẳng định optimizer converged. Không có kết luận quantum advantage, khả năng tổng quát, peakRAM hoặc hardware circuit cost từ QA này. Ba validation case chưa được QAOA huấn luyện. MILP chưa thực hiện ở N27.
