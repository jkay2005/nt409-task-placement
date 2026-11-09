# Notebook 23 — so sánh khởi tạo QAOA trên một bộ quy chiếu

Bước tiếp theo sau Notebook 22: kiểm tra liệu thay cách khởi tạo có cải thiện chất lượng QAOA khi huấn luyện bằng exact. Dùng nguyên input **a3_dev_n5, 5 task + 3 host, 25 qubit** đã cài ở Notebook 22 v2.

## 1. Chép gói mới

Giải nén nội dung ZIP vào thư mục gốc repo, ngang cấp src/tests/notebooks/data. Gói bổ sung module, test, protocol, Notebook 23 và hướng dẫn; cần các file Notebook 22 v2 đã có trên máy bạn. Không cần chép kết quả noise_*.zip vào gói mới. Mã nguồn cũ và dữ liệu đã chạy giữ nguyên.

Trong terminal ở thư mục gốc:

```powershell
conda activate nt409-khiem
python -m unittest discover -s tests -p "test_initialization*.py"
```

Có 9 kiểm tra mới. Tiếp tục khi báo OK; nếu lỗi, giữ traceback để đối chiếu, chưa thay dependency. Mở `notebooks/23_qaoa_initialization_comparison.ipynb`, chọn kernel nt409-khiem, Restart Kernel → Run All.

## 2. Notebook sẽ chạy gì?

| Chiến lược | Ngân sách mỗi kết quả | Số kết quả |
|---|---|---:|
| Single, p=1 | Điểm hiện tại, cap 200 | 1 |
| Multistart, p=1 | Điểm hiện tại 100 + một điểm random 100 | 5 |
| Single, p=2 | Điểm hiện tại, cap 200 | 1 |
| Multistart, p=2 | Điểm hiện tại 100 + một điểm random 100 | 5 |
| INTERP p=1→2 | Học p=1 cap 100 + học p=2 cap 100 | 1 |

Tổng **13 kết quả chiến lược**, gồm **24 lượt optimizer**, tối đa **2600 đánh giá hàm huấn luyện** cho toàn campaign. Mỗi chiến lược có cap 200; nfev thực dùng có thể ít hơn vì COBYLA dừng sớm. Chọn kết quả multistart bằng mean-energy exact thấp nhất, không chọn theo P_opt. INTERP chạy mới phần p=1 của chính nó và tính cả phần đó vào ngân sách.

Huấn luyện chỉ dùng exact. Batch 1024 shots ở cuối mỗi lượt là phép chấm độc lập. Các phép chấm exact, batch cuối, đo chi phí và audit nằm ngoài cap đánh giá hàm tối ưu; chi phí này được ghi riêng. Đây không phải so sánh cùng tổng số lời gọi backend hoặc cùng thời gian.

## 3. Cấu hình khi chạy

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| RESUME_DIR | None | Tạo campaign mới; nhập đường dẫn cũ để tiếp tục |
| MAX_NEW_TRIALS | None | Chạy các lượt optimizer còn lại; đặt 1 để chia nhỏ |
| TARGET_GROUPS | None | Chạy toàn kế hoạch; có thể chọn nhóm từ bảng plan |
| PREPARE_ONLY | False | True chỉ đo chi phí, chưa tối ưu |

Ví dụ chỉ chạy INTERP: `TARGET_GROUPS = ['p2__interp']`. Nó vẫn chạy cả p=1 chuẩn bị và p=2, không dùng góc đã học ở nhóm khác. Các nhóm chưa chạy vẫn được ghi pending; campaign là partial.

Cell đo chi phí chạy một phép exact và một batch đo cho mỗi độ sâu. Bảng training_cap_hours ước lượng nếu dùng hết cap với tốc độ tại góc đó, chưa gồm khởi tạo, chấm cuối và audit. Chi phí thực tế có thể thay đổi. Cả campaign có thể kéo dài nhiều giờ; tránh máy sleep, đóng ứng dụng nặng. Aer CPU double, tối đa 4 luồng, guard RAM khả dụng 4 GiB và 7200 giây mỗi lượt được kiểm tra giữa các lời gọi native, không phải ngắt cứng.

## 4. Tiếp tục và xử lý gián đoạn

Ghi lại CAMPAIGN_DIR được in trước đo chi phí. Nếu muốn tiếp tục, đặt ví dụ sau bằng đường dẫn thật:

```python
RESUME_DIR = r"D:\repo\data\reference_results\phase4o_initialization\init_..."
MAX_NEW_TRIALS = None
TARGET_GROUPS = None
PREPARE_ONLY = False
```

Restart Kernel → Run All. Lượt hoàn tất và profile đã lưu được dùng lại. Không để RESUME_DIR=None khi muốn tiếp tục, vì như vậy sẽ tạo campaign mới. Resume yêu cầu nguyên input, protocol, nguồn và runtime.

**Nếu đang giữa lượt thì bị lỗi/ngắt**, giữ raw report và traceback. Notebook 23 ghi nhận lượt trước khi bắt đầu và không tự retry/reset cap, nhằm tránh một chiến lược được tiêu nhiều ngân sách hơn các chiến lược khác. Kill process có thể để nfev chưa biết; nhóm đó được đánh dấu chưa đủ, không tự coi là hoàn tất. Có thể dùng TARGET_GROUPS để chạy các nhóm khác còn lành mạnh. Nếu cần chạy lại nhóm lỗi, tạo campaign mới, giữ cả bản cũ và báo rõ; không tự gộp hai lần thử thành một kết quả cap 200.

Nếu còn RUNNING.lock, chỉ xóa khi đã xác nhận tiến trình cũ dừng. Không chạy hai writer cùng thư mục. Không sửa protocol hoặc xóa lượt kém giữa campaign.

## 5. Gửi kết quả

Lưu notebook có output và gửi cùng file `init_<timestamp>.zip` do cell cuối tạo. Kiểm tra cả `audit: PASS` và `complete: True`: PASS xác nhận nhất quán; complete xác nhận đủ kế hoạch chính 13 nhóm/24 lượt. ZIP partial vẫn được phép xuất để giữ dữ liệu và lỗi.

Dữ liệu thí nghiệm chính phải đến từ lượt chạy của bạn; gói ban đầu có output rỗng, không chứa raw/hình QA đã chạy. Đọc `docs/notebook23_initialization_vi.md` để biết cách kết luận, và `N23_VALIDATION.md` để biết phạm vi QA.
