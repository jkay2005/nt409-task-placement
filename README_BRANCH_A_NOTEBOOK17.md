# Chạy Notebook 17 — đối chứng mã hóa hai host

Gói bổ sung cho repo đã chạy Notebook 16. Chỉ nhánh A, cùng bộ dữ liệu v1.1.
Không cần chạy lại Notebook 13–16. Giữ toàn bộ kết quả cũ.

1. Giải nén gói vào một thư mục tạm, rồi chép các thư mục `src`, `tests`,
   `notebooks`, `docs`, `data` và README này vào gốc `nt409-task-placement`.
   Gói chỉ thêm file; không thay các module/notebook lịch sử.
2. Mở Anaconda Prompt tại gốc repo:

   ```bat
   conda activate nt409-khiem
   python -m unittest discover -s tests
   ```

   Với bộ Notebook 16 đầy đủ cùng gói này, mong đợi **97 tests, OK**.
   Không cần nâng cấp thư viện. Nếu kết quả test khác, gửi đầy đủ log trước
   khi chạy campaign.
3. Mở `notebooks/17_qaoa_two_host_encoding.ipynb` trong VS Code/Jupyter,
   chọn kernel `nt409-khiem`, Restart Kernel và chạy tám bước theo thứ tự.
4. ZIP Notebook 16 bạn đã gửi được đặt nguyên vẹn trong
   `data/benchmarks/nt409_encoding_v1/baseline_notebook16.zip`. Notebook
   kiểm tra lại từng báo cáo trước khi sử dụng; việc audit có thể mất vài phút.
5. Bước 2 in `RESUME_DIR`. Chép đường dẫn đó vào biến ở bước 1 để tiếp tục
   cùng campaign sau khi đóng kernel. Có thể chia phiên bằng `INSTANCE_IDS`.
   Không chạy song song hai kernel cùng campaign. Không đổi seed/ngân sách.
6. Gửi ZIP do bước 8 in ra và notebook đã chạy, kể cả nếu kết quả là PARTIAL.

## Notebook này đo điều gì?

Mã hóa cũ dùng hai bit x cho mỗi task; mã hóa mới dùng một bit z, tự bảo đảm
mỗi task nằm trên đúng một host. Giữ y và slack CPU/RAM, mục tiêu số host bật.
Số qubit choice/tight/reference giảm từ 20/18/23 xuống 16/14/19.
Chạy 45 lượt mới (ba instance × ba độ sâu × năm seed), thêm một smoke vô nghiệm.

Điểm cần đọc là cả tỷ lệ mẫu tối ưu và **lift so với uniform riêng**. Chỉ
thu nhỏ không gian đã tăng xác suất ngẫu nhiên; không được gọi toàn bộ phần
tăng đó là hiệu quả tối ưu của QAOA. Mã hóa mới chưa bảo đảm CPU/RAM.
Hamiltonian và trạng thái đầu khác giữa hai mã hóa; cả hai áp dụng cùng
quy tắc max_abs và cùng ngân sách, không cùng một hàm mục tiêu số học.

Đếm shots gồm các đánh giá optimizer, batch eigenstate nội bộ Qiskit và
batch cuối độc lập. Baseline 0.7.0 được tái dựng theo mã thư viện; compact
đếm lời gọi sampler. Probe và tiền xử lý được ghi riêng. Cùng runtime chưa
bảo đảm cùng phần cứng/tải máy để tuyên bố tăng tốc.

Trong CSV so sánh, cột `encoding` xác định nguồn: đường dẫn `report` của
`one_hot_slack_v1_1` nằm bên trong `baseline_notebook16.zip`; đường dẫn của
`two_host_binary_v1` tính từ thư mục campaign mới.

Đây là kiểm tra tác động của mã hóa trên ba instance đã biết, không phải
khảo sát 8 task/4 host hoặc bằng chứng quantum advantage. Kết thúc sau audit
ma trận cố định; không mở sweep mới chỉ vì kết quả chưa đẹp.

Tham khảo: `docs/two_host_encoding_protocol.md`.
Thư mục `validation/notebook17/` trong gói chỉ là kiểm chứng phần mềm Linux;
không nhập dữ liệu kiểm chứng vào campaign Windows của bạn.
