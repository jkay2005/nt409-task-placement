# Sửa lỗi cài OR-Tools — Notebook 21 v1.1

## Nguyên nhân

Thông báo `Could not find a version that satisfies the requirement ortools==9.14.6206 (from versions: 9.15.6755)` cho biết pip không có distribution phù hợp cho phiên bản đang khóa trong môi trường hiện tại. Bản 9.14 có Windows wheels đến CPython 3.13; bản 9.15.6755 có wheel `cp314-cp314-win_amd64` cho CPython 3.14 Windows x64. Điều này phù hợp với lỗi trên môi trường Python 3.14. Lựa chọn phiên bản 9.14 trong gói trước chưa phù hợp với môi trường này.

Nguồn kiểm tra ngày 22/10/2026:
- https://pypi.org/project/ortools/9.14.6206/#files
- https://pypi.org/project/ortools/9.15.6755/#files

Không cần đổi bài toán hoặc hạ Python chỉ để xử lý lỗi này. Bản vá chọn OR-Tools 9.15.6755 và đồng bộ mọi chỗ kiểm tra phiên bản. Xem README_FIRST để chạy các lệnh cài đặt.

## Các thay đổi

- `requirements-branch-b.txt`: khóa OR-Tools 9.15.6755.
- `src/classical_baselines.py`: kiểm tra đúng phiên bản mới; FF/BFD và mô hình MILP giữ cùng định nghĩa.
- `data/benchmarks/nt409_classical_b_v1_1/protocol.json`: tạo phiên bản mới, không sửa protocol v1 đã tồn tại.
- `src/classical_campaign.py`: đọc protocol v1.1 và kiểm tra hash tương ứng.
- `tests/test_classical_campaign.py`: kiểm tra requirements/protocol/mã dùng cùng version, dữ liệu và chính sách thực nghiệm không đổi; kiểm tra thay input với đường dẫn mới.
- Notebook 21, README và hai tài liệu hướng dẫn: mô tả version/path mới. Notebook được xóa output trước bàn giao.
- `timing_policy` trong v1.1 được diễn đạt đầy đủ, gồm trạng thái heuristic `no_placement_found` đã được mã v1 xử lý từ trước; không thay hành vi đo.

Không chỉ sửa dòng trong requirements rồi giữ code/protocol cũ: bước kiểm tra version/hash sẽ chặn cấu hình không nhất quán. Cần chép đầy đủ file trong ZIP mới.

## Kết quả và nguồn gốc

Cập nhật solver có thể thay backend SCIP, cách chọn một nghiệm trong tập đồng tối ưu và thời gian thực thi. Vì vậy, campaign mới ghi runtime/backend version thực tế và hash protocol v1.1; không coi timing của v1 và v1.1 là cùng một cấu hình.

Gói cập nhật chỉ chứa source, tests, protocol, tài liệu và notebook chưa chạy. Kết quả của người dùng sẽ được tạo khi chạy notebook trên máy của người dùng. Các kiểm thử phát triển chỉ xác minh việc sửa lỗi và được thực hiện trong thư mục tạm.

## Nếu vẫn gặp lỗi

Chạy và gửi đầu ra các lệnh sau cùng nguyên văn lỗi cài đặt:

```bat
conda activate nt409-khiem
python --version
python -c "import sys, platform; print(sys.executable); print(platform.machine())"
python -m pip --version
```

Sau khi cài xong, restart kernel để phiên làm việc cũ không giữ module/version đã import. Nếu xuất hiện lỗi yêu cầu 9.14 hoặc protocol cũ, kiểm tra đã chép đủ `src/classical_baselines.py`, `src/classical_campaign.py` và protocol v1.1 vào đúng repo hay chưa.

## Kiểm tra bản sửa

- Cài thành công OR-Tools 9.15.6755 trong môi trường kiểm tra Linux/Python 3.12.
- Bộ kiểm thử nhánh B: 12 tests, OK; toàn bộ repo: 140 tests, OK (62.745 giây).
- pip tải được đúng wheel `ortools-9.15.6755-cp314-cp314-win_amd64.whl` khi chọn đích Windows x64/Python 3.14. Đây là kiểm tra có gói cài phù hợp, chưa phải thực thi solver trên Windows.
- Các code cell Notebook 21 biên dịch được; notebook bàn giao có output rỗng.
- Campaign trong các test dùng thư mục tạm; gói bàn giao không chứa kết quả benchmark mới để nộp thay lần chạy của người dùng.
