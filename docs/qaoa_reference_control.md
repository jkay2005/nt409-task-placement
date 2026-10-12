# Notebook 15 — Đối chứng mean/CVaR trên p0_reference

## Mục đích

Đây là phần thí nghiệm tương ứng với notebook 13 (exact mean) và 14 (exact CVaR), chuyển sang `p0_reference` và gom vào một notebook riêng. Không sửa các notebook cũ hoặc dùng baseline `p1_choice` cho reference.

| Lượt | Objective | Khởi tạo [beta, gamma_execution] |
|---|---|---|
| 1 | Mean | common: [0.3, 1.0] |
| 2 | Mean | alternative: [0.8, 1.2] |
| 3 | CVaR, alpha=0.1 | common: [0.3, 1.0] |
| 4 | CVaR, alpha=0.1 | alternative: [0.8, 1.2] |

Cả bốn lượt: p=1, penalty (3,3), X mixer, max_abs, COBYLA/rhobeg=1/tol=1e-4, tối đa 200 lần đánh giá, 1.024 shots cuối, seed cuối 100060. Chạy mới hai lượt mean để có đối chứng cùng ngân sách và môi trường với CVaR. Hai nhánh bắt đầu từ cùng góc gốc, không dùng góc mean tối ưu làm warm start.

## 1. Chép file

Giải nén gói cập nhật rồi chép ba thư mục `notebooks`, `tests`, `docs` vào thư mục repo hiện có:

`C:\Users\Khiem\quang-tum-com-pu-ting\nt409-task-placement`

Ba file mới:

- `notebooks/15_qaoa_reference_control.ipynb`
- `tests/test_reference_control_notebook.py`
- `docs/qaoa_reference_control.md`

Gói này cần repo đã có bản notebook 14, gồm `src/cvar_experiment.py`. Không phải bản repo đầy đủ. Gói không chứa kết quả Linux để tránh lẫn với dữ liệu Windows bạn sắp chạy.

## 2. Kiểm tra môi trường

Trong Anaconda Prompt:

```bat
cd /d C:\Users\Khiem\quang-tum-com-pu-ting\nt409-task-placement
conda activate nt409-khiem
python -m unittest discover -s tests
```

Với bộ test của bản notebook 14 và hai test mới này, dự kiến 74 tests và `OK`. Nếu repo bạn đã thêm test khác, tổng số có thể khác; cần đọc dòng trạng thái cuối. Các DeprecationWarning/SparseEfficiencyWarning đã thấy không tự làm test thất bại. Nếu có ERROR/FAIL, gửi đầy đủ traceback trước khi chạy thí nghiệm.

## 3. Mở notebook

Trong VS Code, mở repo, mở `notebooks/15_qaoa_reference_control.ipynb`, chọn kernel `nt409-khiem` và Restart Kernel. Chạy lần lượt bước 1–4 trước.

- Bước 1: đường dẫn Python phải thuộc môi trường `nt409-khiem`.
- Bước 2: giữ `RESUME_DIR=None` ở lần đầu. Output phải là `p0_reference`, 23 qubit, E_min=2, 4 lượt.
- Bước 3: lưu dòng `RESUME_DIR = 'data/reference_results/phase4g_reference_control/reference_...'`.
- Bước 4: đọc RAM và ước lượng thời gian. Đóng notebook/kernel nặng khác. Nếu bước này báo thiếu RAM hoặc vượt time guard, gửi output bước 4; chưa tự đổi ngân sách.

Sau khi bốn bước trên thành công, chạy bước 5–8 theo thứ tự. Bước 5 thực hiện bốn lượt tuần tự; không chạy song song các notebook thí nghiệm.

## 4. Hoàn tất và gửi file

Bước cuối phải in:

```text
PASS — p0_reference: 4/4 completed, matched mean/CVaR controls verified.
```

Sau đó Save As notebook có output thành `15_qaoa_reference_control_executed.ipynb`. Gửi:

1. Notebook executed đó.
2. File `reference_<timestamp>.zip` tại đường dẫn được in cuối notebook.

ZIP tự gom hai manifest, bốn report, CSV so sánh, đồ thị và SHA256. Report mean và CVaR vẫn nằm trong thư mục kết quả riêng của runner; không cần gom file bằng tay.

`success=False` do hết 200 lần đánh giá vẫn có thể là một report hoàn tất hợp lệ. Tương tự, 0 mẫu tối ưu trong 1.024 shots không làm lượt bị loại. Không yêu cầu mọi lượt phải có cùng số lần đánh giá thực tế.

## 5. Chạy tiếp nếu bị gián đoạn

Ở bước 2, điền đúng đường dẫn đã in ở bước 3, ví dụ:

```python
RESUME_DIR="data/reference_results/phase4g_reference_control/reference_<timestamp-cua-ban>"
```

Thay toàn bộ tên thư mục bằng tên thực tế; không dùng nguyên phần giữ chỗ. Restart Kernel rồi chạy lại từ bước 1. Lượt đã lưu được bỏ qua; lượt đang chạy dở sẽ chạy lại từ đầu. Giữ nguyên mã nguồn, môi trường và tham số giữa hai lần. Không để `None` khi muốn resume vì `None` sẽ tạo thí nghiệm mới.

## Diễn giải

Chỉ số chính là xác suất placement tối ưu lý tưởng tại góc cuối (`P_opt`). So theo cùng khởi tạo, đồng thời báo cáo E_mean, CVaR, P_feasible, P_ground, nfev và thông báo dừng.

CVaR nhỏ hơn không tự chứng minh placement tốt hơn. Chênh lệch `delta_P_opt_pp` là điểm phần trăm. Đây là thí nghiệm statevector lý tưởng, không phải QPU và chưa có khảo sát nhiễu phần cứng. Hai khởi tạo và hai instance chưa đủ để tuyên bố ưu thế tổng quát hay quantum advantage.

## Kiểm chứng gói

Đã thực thi toàn bộ code cell trên Linux với p0_reference 23 qubit, cap200 và 1.024 shots cuối, đủ bốn report; kiểm tra resume không viết lại report đã lưu. Môi trường kiểm chứng dùng bộ thay thế hiển thị cho `IPython.display`, không chạy qua kernel Jupyter. Hai test mới dùng fixture nhỏ để kiểm tra ngắt sau lượt đầu, resume đủ bốn lượt và từ chối liên kết baseline sai/đường dẫn ngoài repo. Kết quả thực nghiệm Windows cần lấy từ lượt chạy của bạn.
