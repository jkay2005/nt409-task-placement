# Notebook25 — T3: kiểm chứng mixer, giữ 5 task × 3 host

Gói này là code để thêm vào repo đã có Notebook24. Tất cả phép kiểm chứng bài toán và phép đo chi phí dùng đúng a3_dev_n5, 25 qubit. Không thay CPU/RAM hoặc thứ tự task/host.

## Gói này thực hiện gì?

1. Tạo trạng thái đầu phân bố đều trên ba mã domain-wall hợp lệ của mỗi task.
2. Thêm mixer có thứ tự A rồi B, chỉ nối các mã hợp lệ; giữ X rotations trên y/slack.
3. Đối chiếu ba cấu hình tại các góc cố định chưa học, p=1 và2; kiểm tra leakage và chi phí.

**Không chạy optimizer và chưa phải chiến dịch so sánh T4.** Có ba lần kiểm tra trạng thái đầu và sáu lần đánh giá mạch; các bước chuẩn bị diagonal/compile và thống kê cũng tốn thời gian/RAM.

## Cài vào repo

Giải nén gói vào thư mục gốc repo đang dùng. Các đường dẫn phải là src/domain_wall_mixer.py, src/domain_wall_probe.py, notebooks/25_domain_wall_mixer_validation.ipynb,... không lồng thêm một cấp thư mục.

Gói cập nhật src/shot_noise_diagnostic.py bằng hai keyword tùy chọn initial_state/mixer_operator để tái sử dụng evaluator. Khi không truyền chúng, control dùng cùng ansatz mặc định. Các nguồn cũ được giữ trong ZIP kết quả lịch sử. Không resume campaign Notebook22–24 đang dang dở sau khi thay source; source hash mới phải tạo lượt/campaign mới. Các campaign đã hoàn tất không bị sửa.

Không thêm dependency ngoài môi trường Notebook24.

```powershell
conda activate nt409-khiem
python -m unittest discover -s tests -p "test_domain_wall_mixer.py"
```

Sau khi tám test báo OK, mở Notebook25, chọn kernel nt409-khiem và Restart Kernel → Run All. Để THREADS=4 và MIN_AVAILABLE_GIB=4.0; chương trình dừng nếu thiếu RAM trước lời gọi native, không tự hạ guard hoặc thay input nhỏ hơn.

Nếu gặp MemoryError, lưu traceback và giữ nguyên input. Nếu tiến trình bị ngắt, thư mục kết quả trước đó được giữ; T3 dùng thư mục mới khi chạy lại, không có resume optimizer vì không có optimizer. Khi exception đã được bắt, probe.json giữ status FAILED và lỗi; một lần chạy lại không ghi đè nó.

## Gửi lại gì?

Save notebook có output và gửi:

- 25_domain_wall_mixer_validation.ipynb đã chạy.
- ZIP được cell cuối in ra, nằm cạnh thư mục probe trong data/reference_results/phase5_domainwall_t3/.

Không gửi nhầm gói code cài đặt thay cho ZIP kết quả vừa chạy. Kết quả kiểm thử Linux của trợ lý được ghi riêng; số đo chi phí trên Windows phải lấy từ lần chạy của bạn.

## Cách đọc PASS

- Trạng thái đầu valid_x và valid_dw có P_domain≈1.
- valid_dw sau mạch p=1 và2 phải có P_domain≈1 trong dung sai1e-10.
- valid_x có thể mất tính hợp lệ sau X mixer: đây là đối chứng có chủ đích.
- PASS xác nhận mạch và khả năng chạy; không chứng minh P_opt tăng.
- p_valid, p_opt và mean ở góc chưa học chỉ để kiểm tra pipeline. Không chọn góc hoặc phương án theo bảng này.
- evaluation_seconds là một lần mô phỏng xác suất; setup_seconds ghi riêng. Đây không phải benchmark timing nhiều lần.
- RSS đo sau evaluation, không phải đỉnh RAM; null nghĩa là API hệ thống không đo được, không phải dùng0MB.

Đọc lý thuyết ở docs/domain_wall_t3_vi.md; phạm vi kiểm chứng ở N25_VALIDATION.md.
