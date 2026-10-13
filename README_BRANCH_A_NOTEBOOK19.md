# Notebook 19 — domain-wall ba host và development pilot

Gói tiếp tục từ checkpoint Notebook18; nhánh A. Giải nén nội dung ZIP vào root
nt409-task-placement trên nhánh feat/a-three-host-domain-wall, không vào thư mục con
trùng tên. Chỉ thêm các file mới của gói. Các module lịch sử và báo cáo16–18 không đổi.

## Cách chạy Windows

1. Save mọi notebook đang mở. Trong terminal root:

   ```text
   conda activate nt409-khiem
   python -m unittest discover -s tests
   ```

2. Mở notebooks/19_three_host_validation_pilot.ipynb, chọn kernel nt409-khiem.
   Restart Kernel rồi chạy9bước. Không phải chạy lại13–18.
3. Bước2 in RESUME_DIR. Lưu đường dẫn này để tiếp tục đúng pilot. Có thể chạy
   RUN_INSTANCES=['a3_dev_n4'] trước, rồi n5/controls ở phiên tiếp theo cùng RESUME_DIR.
   Giữ nguyên config/seed/code và dataset khi resume; completed không chạy lại.
4. Gửi ZIP được in ở bước9 và notebook19 đã Save. Nếu RAM/time/error chặn,
   chạy bước8–9 hoặc mở lại với RESUME_DIR để export partial; đừng xóa report.

## Notebook làm gì?

| Bước | Kết quả |
|---|---|
|1–2|Khóa runtime/input/protocol/source; tạo hoặc mở pilot|
|3|Kiểm chứng đa thức/QUBO/Ising và oracle placement; giữ vô nghiệm|
|4|Uniform encoded và random placement; xác suất IID của controls|
|5|Đo solver vét cạn/random trong phiên hiện tại, không nhận đáp án tối ưu|
|6|6dev probes +2functional p1probes; compiled depth/ops và tài nguyên|
|7|12dev trials p1/p2/p3/2seed +2functional smokes, final batch độc lập|
|8–9|Bảng/plot development, audit nguồn/raw counts, ZIP và projection chi phí|

Hai dev23/25qubit; sáu test20–25qubit đã đóng băng, không chạy QAOA trên test.
Chọn test từ informative uniform-encoded batch0.2–0.7, không theo QAOA.
Controls gần100% random batch không chứng minh QAOA có ích hơn classical.
Không chọn p thắng từ pilot; không có ngưỡng27/30 hoặc24/30. Chỉ đánh giá chất
lượng từng instance và chi phí; không chứng minh scaling lớn hay quantum advantage.

Guard: start available8GiB, reserve4GiB, RSS Python4GiB, Aer2048MiB/4threads,
chạy tuần tự. Một vector25q512MiB không phải whole RSS. Guard ở ranh giới call,
không ngắt native allocation. Passed probe không bảo đảm full training.

Protocol pilot:mean/X/COBYLA,max_abs,P4,cap200,train/final1024shots,seed190/191,
evaluation seed100190/100191; controls p1cap35seed192/final100192. Time guard2400s
trước/giữa/sau native calls, không là hard timeout. Mọi failure giữ riêng và
không được gọi completed. Peak RSS là đỉnh vòng đời process: Restart Kernel.

Nguồn/spec: docs/three_host_study_spec.md, docs/three_host_encoding.md.
FF/BFD/MILP không có trong gói này; chưa gọi đây là hoàn tất so sánh cổ điển proposal.
Notebook20/campaign90test chỉ chuẩn bị sau review pilot Windows và ngân sách C2.
