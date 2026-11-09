# Notebook 13 — Ngân sách exact trên choice: 80 → 200

Mục tiêu: hoàn tất chẩn đoán còn thiếu của notebook 12. Hai lượt exact choice trước đó đều hết ngân sách 80 lần đánh giá; vì vậy chưa đủ bằng chứng chúng đã đạt tiêu chuẩn dừng số học.

## Thiết kế cố định

| Thành phần | Giá trị |
|---|---|
| Instance | p1_choice, 20 qubit |
| Số lượt mới | 2, chỉ exact |
| Khởi tạo [beta, gamma_execution] | common [0.3, 1.0]; alternative [0.8, 1.2] |
| Độ sâu; penalty | p=1; assignment=3, capacity=3 |
| Chuẩn hóa | max_abs, kappa=74.5 |
| Optimizer | COBYLA, rhobeg=1, tol=1e-4 |
| Thay đổi | maxiter: 80 → 200 |
| Phép đo cuối | 1.024 shots, seed=100060 |
| Bảo vệ tài nguyên | 600 giây/lượt; 4 luồng; Aer 2.048 MiB; RAM khả dụng tối thiểu 2 GiB |

Chạy lại từ góc ban đầu, không khởi động từ góc cuối cap80. Một bộ góc không chứa trạng thái trust region của COBYLA. maxiter là giới hạn số đánh giá hàm, không yêu cầu chạy đủ 200.

Giữ cùng seed đo cuối để cố định cấu hình; không coi hai batch ở hai ngân sách là các lần lặp thống kê độc lập. Objective exact không dùng shots. So sánh chính dùng E_exact và P_opt lý tưởng; bảng đo cuối báo riêng số mẫu tối ưu/ground state.

## Cài gói và chạy trong VS Code

1. Giải nén ZIP vào thư mục gốc `nt409-task-placement`. Cập nhật `src/convergence_campaign.py`, `tests/test_convergence_campaign.py`; thêm notebook 13 và tài liệu này. Gói kèm 9 JSON baseline choice nguyên vẹn: manifest và 8 report. Nếu đã có các tên đó, chúng phải là cùng dữ liệu ngày 08/10.
2. Trong terminal của môi trường Conda dự án, chạy:

   ```powershell
   python -m unittest discover -s tests
   ```

3. Mở `notebooks/13_qaoa_exact_budget_choice.ipynb`, chọn kernel đã dùng cho notebook 12 và Restart Kernel. Không nâng phiên bản thư viện cho riêng đối chứng này.
4. Ở Bước 2, giữ `MAX_EVALUATIONS = 200`, `RESUME_MANIFEST = None` và đường dẫn baseline có sẵn.
5. Chạy Bước 1–4. Bước 3 phải có **2 lượt exact, 20 qubit, E_min=1**. Kiểm tra bảng khác biệt môi trường. Bước 4 tái tính E_exact/P_opt ở hai góc baseline.
6. Chạy Bước 5–10. Lưu đường dẫn manifest Bước 5. Bước 6 lưu từng lượt hoàn tất; nếu không có mẫu tối ưu vẫn giữ report.
7. Cuối notebook phải hiện:

   ```text
   PASS — p1_choice: 2/2 exact completed, cap 200, independent final sampling verified.
   ```

8. Save As notebook có output thành `13_qaoa_exact_budget_choice_executed.ipynb`. Gửi file này cùng `exact_budget_choice_<timestamp>.zip` được in ở Bước 10. ZIP chứa manifest mới, 2 report và CSV so sánh.

Không chạy lại notebook 12 chỉ vì cập nhật gói. Không dùng manifest cap80 để resume cap200. Module mới bảo toàn cách tạo trial mặc định của notebook 12; chế độ đọc dữ liệu lịch sử bỏ kiểm tra *môi trường hiện tại*, nhưng vẫn kiểm tra hash thiết kế, report, cấu hình, counts, năng lượng và metric. Resume luôn kiểm tra môi trường hiện tại.

## Resume

Restart kernel; đặt `RESUME_MANIFEST` bằng đường dẫn tương đối của manifest `exact_budget_...json` đã in. Chạy từ đầu, giữ nguyên các cấu hình khác. Lượt đã lưu được xác minh rồi bỏ qua. Lượt đang chạy khi ngắt phải chạy lại từ đầu, không được xem là đã hoàn tất.

Nếu Bước 3 báo mã lõi khác baseline, cần xem xét thay đổi trước khi quy chênh lệch cho ngân sách. Nếu chỉ khác runtime, notebook ghi rõ đây là đối chứng khác môi trường. Kiểm tra năng lượng tại hai góc baseline không chứng minh toàn bộ quỹ đạo tối ưu giữa các phiên bản sẽ giống nhau.

## Cách đọc kết quả

- `delta_E = E_200 − E_80`: âm nghĩa là năng lượng thấp hơn.
- `delta_P_opt_pp`: chênh lệch xác suất placement tối ưu lý tưởng theo điểm phần trăm.
- `success_200`, `stop_200`, `nfev_200`: phân biệt hết ngân sách, dừng số học và các lý do khác. Dừng thành công không chứng minh cực tiểu toàn cục.
- `best_drop_last20`: mô tả tiến bộ của năng lượng tốt nhất trong 20 lần đánh giá cuối. Không dùng một ngưỡng tùy ý để tuyên bố hội tụ.
- `P_hit_1024`: xác suất lý thuyết gặp ít nhất một nghiệm trong 1.024 shots độc lập từ phân phối cố định; không phải tỷ lệ thành công được đo qua nhiều lần chạy.
- Placement tối ưu chỉ cần x/y đúng; ground state cần toàn bộ bit gồm slack đạt cực tiểu QUBO. Không gộp hai chỉ số.

Nếu E giảm mà P_opt không tăng, kết luận chỉ là thêm ngân sách cải thiện mục tiêu năng lượng trong trường hợp đó. Khi đó có cơ sở thử objective khác trong một đợt riêng. Nếu vẫn hết 200 và còn giảm rõ, vấn đề ngân sách chưa khép lại. Nếu dừng số học nhưng chất lượng thấp, không tiếp tục tăng maxiter một cách máy móc. Chưa triển khai CVaR/mixer/p=3 trong đợt này.

## Nguồn

SciPy, `minimize(method='COBYLA')`: `maxiter` giới hạn số đánh giá hàm; `tol` liên quan đến cận dưới bán kính trust region. https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html
