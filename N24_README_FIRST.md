# Notebook 24 — so sánh mean-energy và CVaR

Gói bổ sung cho repo NT409 đã có Notebook 23 và mã nguồn các notebook trước, gồm `src/cvar_experiment.py` từ Notebook 14. Dùng nguyên **a3_dev_n5: 5 task + 3 host, 25 qubit**. Thí nghiệm này kiểm tra objective sau khi đã chọn INTERP; không đổi bộ quy chiếu.

## 1. Cài gói và chạy

Giải nén ZIP vào thư mục gốc repo, ngang cấp src/tests/notebooks/data. Không cần chép ZIP kết quả Notebook 23 vào repo để chạy bước mới; không nhập góc đã học từ file cũ. Không có dependency mới.

Trong terminal tại thư mục gốc:

```powershell
conda activate nt409-khiem
python -m unittest discover -s tests -p "test_cvar_campaign.py"
```

Có **8 test mới**; tiếp tục khi báo OK. Nếu thiếu module nguồn cũ, giữ traceback và bổ sung đúng bộ nguồn của repo; không tự thay dependency để bỏ lỗi. Mở `notebooks/24_qaoa_mean_vs_cvar.ipynb`, chọn kernel nt409-khiem, Restart Kernel → Run All.

## 2. Kế hoạch cố định

| Nhóm | Chuẩn bị p=1 | Tối ưu p=2 | Cap mỗi kết quả |
|---|---|---|---:|
| p2__mean | Mean, 100 | Mean, 100 | 200 |
| p2__cvar_025 | Mean, 100 | CVaR 25%, 100 | 200 |
| p2__cvar_010 | Mean, 100 | CVaR 10%, 100 | 200 |

Có **3 kết quả chiến lược, 6 lượt optimizer, tối đa 600 đánh giá huấn luyện**. Mỗi nhóm chạy mới p=1 từ [0.3,1] và dùng INTERP sang p=2. Chỉ objective ở p=2 thay đổi. Không tối ưu p=1 bằng CVaR, không dùng miễn phí góc từ Notebook 23.

CVaR 25% lấy năng lượng trung bình của 25% khối xác suất có năng lượng thấp nhất, có xử lý phần xác suất tại biên; không phải chọn 25% số bitstring. Huấn luyện exact; batch cuối1024 shots chỉ chấm độc lập. Chi phí profile, chấm endpoint và audit nằm ngoài cap 600, được ghi riêng. Cap bằng nhau không bảo đảm nfev thực tế hoặc thời gian bằng nhau.

## 3. Chia nhỏ hoặc đo trước chi phí

| Biến | Mặc định | Tác dụng |
|---|---|---|
| RESUME_DIR | None | Tạo campaign mới; nhập đường dẫn cũ để tiếp tục |
| MAX_NEW_TRIALS | None | None chạy các lượt còn lại; 1 chạy thêm một lượt optimizer |
| TARGET_GROUPS | None | None chạy toàn bộ; ví dụ ['p2__cvar_025'] chọn một nhóm |
| PREPARE_ONLY | False | True chỉ profile, chưa tối ưu |

Để xem chi phí trước: PREPARE_ONLY=True rồi Run All. Ghi lại CAMPAIGN_DIR; lần sau đặt RESUME_DIR bằng thư mục đó và PREPARE_ONLY=False. Nếu RESUME_DIR vẫn None thì sẽ tạo campaign mới.

Ví dụ resume trên Windows, thay đường dẫn bằng giá trị thực:

```python
RESUME_DIR = r"C:\repo\data\reference_results\phase4p_cvar\cvar_..."
MAX_NEW_TRIALS = None
TARGET_GROUPS = None
PREPARE_ONLY = False
```

Profile đo riêng mean/CVaR ở mỗi loại giai đoạn. training_cap_hours là ước lượng từ góc profile, chưa gồm khởi tạo/chấm cuối/audit; không dùng như cam kết thời gian. Tránh máy sleep. Aer CPU double dùng tối đa 4 luồng. Guard RAM khả dụng 4 GiB và 7200 giây mỗi lượt chỉ được kiểm tra giữa các lời gọi native, không phải ngắt cứng.

## 4. Khi lỗi hoặc gián đoạn

Lượt được ghi running trước khi bắt đầu. Hoàn tất thì lưu history, góc và endpoint. Resume dùng lại lượt/profile đã hoàn tất, yêu cầu giữ nguyên nguồn/input/protocol/runtime.

Nếu lỗi/ngắt: giữ report và traceback, không tự xóa lượt để chạy lại dưới tên cap 200. Nếu process bị kill, nfev có thể chưa biết; nhóm vẫn được giữ là chưa đủ và không tự reset. Có thể chọn TARGET_GROUPS để chạy nhóm khác. Muốn thử lại nhóm lỗi thì tạo campaign mới, giữ cả bản cũ và công bố lần thử; không gộp hai lần thử thành một kết quả cap 200. Chỉ xóa RUNNING.lock sau khi xác nhận tiến trình cũ đã dừng; không chạy hai writer vào cùng thư mục.

## 5. Đọc và gửi kết quả

Bảng cuối chấm mọi góc p=2 bằng P_opt, P_valid, P_ground, mean-energy, CVaR 25%, CVaR 10%, nfev và thời gian. Chỉ so sánh objective giữa các phương án trong cùng một cột; không so raw CVaR 10% với mean rồi kết luận thắng. Tiêu chí chất lượng chính vẫn là P_opt trên toàn phân phối.

Gửi notebook đã lưu output và `cvar_<timestamp>.zip` do ô cuối tạo. Cần xem cả **audit: PASS**, **complete: True**, **common_p2_start: True**. PASS không chứng minh CVaR cải thiện chất lượng. Complete xác nhận đủ ba nhóm/sáu lượt; không xác nhận hội tụ. ZIP partial vẫn xuất được để giữ dữ liệu lỗi.

Gói bàn giao có notebook output rỗng và protocol chính software_validation=False; không chứa kết quả QA. Đọc `docs/notebook24_cvar_vi.md` để hiểu thiết kế, và `N24_VALIDATION.md` để biết phạm vi kiểm chứng.
