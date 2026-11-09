# Notebook 22 v2 — một bộ quy chiếu 5 task + 3 host

Bản này thay thế gói Notebook 22 hai-host chưa chạy. Input duy nhất là **a3_dev_n5**: t0–t3 mỗi task CPU=1,RAM=1; t4 CPU=1,RAM=2; h0 CPU=2,RAM=2; h1,h2 mỗi host CPU=3,RAM=3. Mô hình domain-wall hiện có dùng 25 qubit, penalty 4. Mục tiêu là kiểm tra tác động của nhiễu shots lên chất lượng QAOA trên đúng input này.

## 1. Chép vào repo

Giải nén ZIP, chép **nội dung bên trong** vào thư mục gốc `nt409-task-placement`, ngang cấp `src`, `tests`, `notebooks`, `data`. Không đặt cả thư mục ZIP vào `notebooks`. Không cần tải hoặc áp dụng gói v1 trước.

Gói cung cấp input và protocol v2 riêng. Nó cần các module nhánh A đã có: `three_host_encoding.py`, `placement.py`, `qubo.py`, `ising.py`, `qaoa_experiment.py`, `qaoa_optimizer.py`. Không thay nguồn các notebook cũ, Notebook 21 hoặc kết quả A/B/C. Không cần cài thêm thư viện cho dự án.

## 2. Kiểm tra bằng môi trường hiện tại

Trong Anaconda Prompt hoặc terminal ở thư mục gốc:

```powershell
conda activate nt409-khiem
python -m unittest discover -s tests -p "test_shot_noise*.py"
```

Tiếp tục khi 14 kiểm tra mới báo `OK`. Nếu lỗi, giữ nguyên traceback, chưa tự nâng/hạ thư viện. Những kiểm tra nhỏ là QA, không phải các lượt thí nghiệm chính; fixture nhỏ chỉ dùng trong kiểm thử phần mềm.

## 3. Chạy notebook

1. Mở `notebooks/22_qaoa_shot_noise_diagnostic.ipynb`, chọn kernel `nt409-khiem`.
2. Cell đầu in Python đang chạy; kiểm tra đúng conda env.
3. Lần đầu giữ `RESUME_DIR=None`, `MAX_NEW_RUNS=None`, `RETRY_FAILED=False`, `PREPARE_ONLY=False`.
4. Restart Kernel → Run All. Ghi lại đường dẫn `CAMPAIGN_DIR` được in trước hiệu chuẩn.
5. Cell hiệu chuẩn đo chi phí **trên máy bạn** cho p=1,2. Bảng `training_cap_hours` ước lượng thời gian nếu dùng hết cap; chưa gồm khởi tạo, đo cuối và audit, không phải ETA bảo đảm.
6. Mặc định notebook tiếp tục chạy cả 12 lượt. Có thể kéo dài nhiều giờ; tránh máy sleep, đóng ứng dụng nặng.
7. Cell cuối kiểm chứng lại dữ liệu và in đường dẫn ZIP kết quả.

Thiết kế: **1 input × 2 độ sâu × (1 exact + 5 shots) = 12 lượt**. Mỗi lượt có trần 200 lần đánh giá; COBYLA có thể dừng sớm. Training và batch cuối dùng 1024 shots. Mỗi độ sâu có 20 batch hiệu chuẩn tại cùng góc đầu; dữ liệu hiệu chuẩn đã lưu được dùng lại khi resume.

Muốn chỉ đo chi phí trước, đặt `PREPARE_ONLY=True` trước Run All. Kết quả lúc này là `partial`, chưa có lượt huấn luyện. Lần sau đặt `RESUME_DIR` đúng thư mục vừa tạo, đổi `PREPARE_ONLY=False`. Không giữ `RESUME_DIR=None`, vì sẽ tạo một campaign mới.

Muốn chia nhỏ phiên huấn luyện, đặt `MAX_NEW_RUNS=1` hoặc số lượt mong muốn; khi tiếp tục phải resume đúng thư mục cũ. Số lượt mỗi phiên không thay kế hoạch 12 lượt.

## 4. Resume và lỗi

Ví dụ cấu hình, thay bằng đường dẫn thật đã in:

```python
RESUME_DIR = r"D:\duong-dan-repo\data\reference_results\phase4n_shot_noise\noise_..."
PREPARE_ONLY = False
MAX_NEW_RUNS = None
RETRY_FAILED = False
```

Chạy lại từ đầu notebook. Lượt hoàn tất và nhóm hiệu chuẩn đã ghi được giữ lại. Nếu lượt huấn luyện có `failed`/`interrupted`, xem `error` và `traceback` trong raw report, xử lý nguyên nhân rồi mới đặt `RETRY_FAILED=True`. Retry có bản ghi mới; không ghi đè lần lỗi. Nếu hiệu chuẩn lỗi, giữ traceback; nhóm chưa hiệu chuẩn xong cần chạy lại.

Nếu kernel/process bị kill, lượt đang chạy có thể chưa kịp ghi. Chỉ xóa `RUNNING.lock` sau khi xác nhận tiến trình cũ đã dừng; không chạy hai writer cùng campaign. Không resume dữ liệu v1 hai-host. Resume yêu cầu nguyên input, protocol, nguồn và runtime.

Aer chạy CPU double, tối đa 4 luồng và giới hạn bộ nhớ backend 8192 MiB. Chương trình yêu cầu RAM khả dụng tối thiểu 4 GiB trước đánh giá; đây không phải giới hạn tổng RAM tiến trình. Guard 7200 giây/lượt được kiểm tra giữa các lời gọi native, không phải ngắt cứng. Guard không bảo đảm tránh mọi tình huống thiếu RAM. Nếu dừng vì tài nguyên, giữ bản ghi; nếu cần đổi protocol/runtime, tạo campaign riêng và báo rõ.

## 5. Gửi lại

Lưu notebook có output và gửi kèm `noise_<timestamp>.zip` do cell cuối tạo. Kiểm tra cả `audit: PASS` **và** `complete: True`; PASS chỉ kiểm tra tính nhất quán, dữ liệu vẫn có thể chưa đủ 12 lượt. Không xóa seed kém hoặc chọn kết quả đẹp để thay thế.

Gói ban đầu không có kết quả QA hay kết quả thí nghiệm chính. Xem `docs/notebook22_shot_noise_vi.md` để đọc chỉ số và giới hạn kết luận.
