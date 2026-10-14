# Notebook 16 — chạy benchmark thống nhất cho nhánh A

Gói này bổ sung bộ chạy và Notebook16 vào đồ án hiện có đã chạy Notebook15.
Phạm vi là A: QUBO/Ising/QAOA. Không cần thực hiện B/C để chạy hay nghiệm thu A.
Không cần chạy lại Notebook13–15.

## 1. Cài gói vào đúng vị trí

Giải nén gói `nt409_branch_a_notebook16_v1_1.zip` vào thư mục tạm. Sao chép các
thư mục `src`, `tests`, `notebooks`, `docs`, `data`, `tasks` vào thư mục gốc:

`C:\Users\Khiem\quang-tum-com-pu-ting\nt409-task-placement`

Merge các thư mục cùng tên. Notebook phải nằm tại
`nt409-task-placement\notebooks\16_qaoa_unified_benchmark_a.ipynb`, không lồng
thêm một thư mục tên gói ở giữa. Gói chỉ thêm hai module mới; không thay các
module mô hình/runner lịch sử. Bốn input JSON và đặc tả v1 trong gói là bản gốc
đã khóa; nếu bạn có thay đổi riêng trong các file này, giữ bản sao để đối chiếu.

Protocol mới nằm trong `data/benchmarks/nt409_benchmark_v1_1/`. Bản v1 vẫn giữ
nguyên để truy vết. A v1.1 chỉ tăng time guard QAOA từ 600 lên 2400 giây, đều
cho mọi p, dựa trên probe thời gian. Dữ liệu, seed, shots, cap và mô hình giữ
nguyên. Xem `docs/benchmark_a_protocol_v1_1.md`.

## 2. Kiểm thử trước khi chạy

Trong Anaconda Prompt:

```bat
cd /d C:\Users\Khiem\quang-tum-com-pu-ting\nt409-task-placement
conda activate nt409-khiem
python -m unittest discover -s tests
```

Với bộ 74 kiểm thử từ Notebook15 và 13 kiểm thử mới, kết quả là **87 tests,
OK**. Nếu repo có thêm kiểm thử riêng, số lượng có thể cao hơn. Các cảnh báo
DeprecationWarning/SparseEfficiencyWarning không tự làm bài kiểm thử thất bại;
đọc dòng kết quả cuối. Nếu FAILED/ERROR, gửi nguyên traceback trước khi chạy
campaign. Không cần nâng package khi môi trường hiện có vẫn đạt các kiểm thử.

Notebook cần SciPy >=1.16, Qiskit2.x/Aer0.17 và các package đã có trong
requirements của đồ án. Không cập nhật môi trường giữa campaign vì resume
kiểm tra cả source và phiên bản runtime.

## 3. Chạy Notebook16

Mở notebook, chọn kernel `nt409-khiem`, **Restart Kernel**, chạy lần lượt:

1. **Bước 1:** kiểm tra đường dẫn Python và RAM available.
2. **Bước 2:** lần đầu giữ `RESUME_DIR=None`, `RETRY_FAILED=False`. Lưu lại đường
   dẫn `RESUME_DIR` được in ra. Mặc định chạy cả choice/tight/reference.
3. **Bước 3:** kiểm tra 20/18/23 qubit và optimum 1/2/2 host; negative control
   20 qubit có optimum `None`. Thời gian tạo QUBO/reference được lưu riêng,
   có nhãn cho biết có dùng cache hay không.
4. **Bước 4:** probe cho từng instance/p: ba điểm với các lớp thật sự hoạt động,
   phép đo cuối và giải mã. Chỉ sang bước 5 khi tất cả cấu hình được chọn PASS.
5. **Bước 5:** chạy tuần tự, lưu report sau từng lượt. Một negative smoke riêng,
   rồi **45 lượt = 3 instance × 3 p × 5 seed**. Cap200 là số đánh giá tối đa;
   COBYLA có thể hội tụ sớm hơn. Không đặt yêu cầu nfev phải bằng 200.
6. **Bước 6–8:** audit, bảng/đồ thị và xuất ZIP. Save As notebook có output thành
   `16_qaoa_unified_benchmark_a_executed.ipynb`.

Máy có 28 GB RAM tổng vẫn cần **available >=8 GiB** lúc bắt đầu. Runner giữ
ngưỡng available4 GiB/RSS Python4 GiB, Aer2048 MiB/4 threads; chạy tuần tự.
Đóng các tiến trình nặng nếu cần. Theo dõi tại ranh giới lời gọi không phải giới
hạn cưỡng bức OS; thời gian/RAM có thể tăng trong một lời gọi Aer đang chạy.
Không mở nhiều kernel chạy benchmark cùng lúc.

Probe ước lượng thời gian bằng evaluation chậm nhất, cap200 và hệ số1,5;
không đảm bảo thời gian thực tế. Nếu `time_estimate_exceeds_budget` hoặc thiếu
RAM, dừng bước5, chạy riêng bước8 để xuất ZIP partial và gửi lại để xem xét.
Không chỉnh protocol/manifest nhằm vượt qua kiểm tra. Có thể chọn chỉ một
instance đã probe đạt cho phiên này mà vẫn giữ đầy đủ ma trận45 trong campaign.

## 4. Tạm dừng và tiếp tục

Muốn chạy từng phần, sửa danh sách ở bước2, ví dụ:

```python
RUN_INSTANCE_IDS=["p1_choice"]
```

Ở phiên sau, điền đúng đường dẫn đã in và chọn phần còn lại:

```python
RESUME_DIR="data/reference_results/phase4h_benchmark_a/benchmark_a_<mã_được_in>"
RUN_INSTANCE_IDS=["p1_tight","p0_reference"]
RETRY_FAILED=False
```

Chạy lại từ bước1. `RESUME_DIR` là đường dẫn tới **thư mục**, không phải file ZIP
hay campaign.json. Giữ source, input, protocol và môi trường không đổi.
Lượt completed luôn được bỏ qua, kể cả khi không tìm được nghiệm. Lượt
interrupted được thử lại từ đầu với cùng seed/config; không tiếp nối trạng thái
nội bộ COBYLA. Mọi attempt trước vẫn giữ trong sổ và ZIP.

Để dừng, chọn Interrupt Kernel một lần, chờ runner lưu trạng thái rồi Save.
Nếu kernel bị tắt đột ngột, lần mở lại sẽ ghi nhận interrupted hoặc khôi phục
report đã ghi xong trước khi manifest kịp cập nhật. Phần chưa ghi trước khi
process chết có thể không có history/counts; được đánh dấu thiếu, không bịa số.

Sau khi xử lý nguyên nhân resource/time/error, có thể đặt `RETRY_FAILED=True`
để thử lại cấu hình chưa hoàn tất; báo cáo cũ vẫn giữ. Bật cờ này không thay
ngân sách và không chạy lại lượt completed để chọn kết quả đẹp hơn. Nếu chưa
xử lý nguyên nhân, giữ False và gửi ZIP partial.

## 5. Đọc kết quả và điểm dừng A

- Chất lượng đầu ra: best-valid từ 1024 mẫu cuối; ưu tiên objective nhỏ nhất,
  rồi tần suất cao nhất, rồi thứ tự bits. Không sửa bit và không phá hòa bằng
  slack energy. Mode và toàn bộ đồng hạng được báo riêng.
- P_opt/P_feasible là tần suất batch cuối với seed độc lập, không phải xác suất
  exact. Lượt completed có 0 nghiệm vẫn nằm trong mẫu thống kê.
- `optimizer_success=False` do chạm cap200 không tự có nghĩa chạy bị lỗi;
  đọc status của lượt và thông điệp dừng. Resource/time/error có status riêng.
- Nhóm chưa đủ5 completed là nhóm chưa hoàn tất. Mean của nhóm partial phải
  đọc cùng số completed; không dùng riêng seed tốt nhất làm kết luận.
- `total_seconds` là thời gian trong runner, có setup/solver/final sampling và
  hậu xử lý. Model/reference ở bước3 và probe được lưu riêng. Audit/ghi file và
  thời gian nghỉ giữa các phiên không nằm trong số này; không gọi nó là tổng
  wall-time end-to-end. RSS peak là đỉnh vòng đời process, có thể gồm hoạt động
  trước đó trong kernel; các mẫu RSS tại boundary cũng được lưu.

**PASS của notebook:** đủ45/45 lượt chính thức completed, negative control
completed và không có mẫu hợp lệ, report nguồn qua audit. **PARTIAL:** chưa đủ,
vẫn xuất được ZIP đầy đủ trạng thái. Không coi việc giảm danh sách instance hay
chạy lại notebook là đã giảm số lượt nghiệm thu.

Gửi lại **ZIP do bước8 tạo** và **notebook executed**. ZIP chứa campaign.json
(snapshot input/protocol/source/runtime), toàn bộ attempts, CSV46 dòng và
checksums; có đồ thị nếu đã chạy bước7. Có thể gửi partial khi bị chặn.

Sau khi review đủ kết quả và chốt nhận xét/giới hạn của A, đóng phần benchmark
nhánh A. Không tự mở thêm penalty/CVaR/seed sweep vì P_opt thấp, không cần chờ
B/C. Phạm vi vẫn4 task/2 host; không tuyên bố thực nghiệm8/4 hay lợi thế lượng tử.

## 6. Kiểm chứng trước bàn giao

Mã được kiểm thử trên Linux: 87 bài kiểm tra, gồm khởi tạo p1/p2/p3 tương
đương, phép đo thật p3, output tie, RAM/time/interrupt, ledger phục hồi khi crash,
resume bỏ qua completed, khóa tránh hai process và export giữ pending/failure.
Đã probe cả9 tổ hợp instance/p trên 18/20/23 qubit. Probe v1 cho reference p2/p3
vượt600 giây ước lượng, là cơ sở tạo v1.1. Một lượt reference p3/cap200/1024
shots hội tụ sau53 đánh giá trên máy kiểm thử. Đây là dữ liệu kiểm chứng phần
mềm, không nằm trong45 lượt Windows của bạn.

Notebook được kiểm tra cú pháp và thực thi các cell bằng Python ở chế độ
không có giao diện Jupyter, gồm đường xuất partial. Bộ ma trận45 trên Windows
chưa được chạy trong môi trường này; probe tại máy bạn và file kết quả gửi lại
mới là bằng chứng cho campaign chính thức. Nhánh khóa file Windows dùng
msvcrt; hành vi trên Windows cần được xác nhận qua lần chạy thực tế của bạn.
