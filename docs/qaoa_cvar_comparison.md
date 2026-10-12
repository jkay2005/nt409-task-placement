# Notebook 14 — Đối chứng exact mean và CVaR trên choice

Notebook 13 đã cho thấy hai lượt mean-optimization đạt tiêu chuẩn dừng số học ở 151/105 đánh giá trên Windows. Năng lượng cuối cùng khoảng 59,2936, nhưng xác suất placement tối ưu chỉ khoảng 0,12577% mỗi shot. Notebook 14 kiểm tra một thay đổi riêng: cách tổng hợp năng lượng mà optimizer tối ưu.

## Thiết kế trước khi chạy

| Thành phần | Giá trị |
|---|---|
| Input | p1_choice, 20 qubit |
| Lượt mới | 2 lượt exact CVaR, common và alternative |
| Đối chứng | 2 report exact mean cap200 của notebook 13 trên Windows |
| Alpha | 0,1, cố định trước kết quả |
| Khởi tạo [beta, gamma_execution] | [0.3, 1.0] và [0.8, 1.2], từ đầu |
| Mạch | p=1, mixer X, cùng Hamiltonian |
| Penalty | assignment=3, capacity=3 |
| Chuẩn hóa | max_abs; kappa=74,5 |
| Tối ưu | COBYLA, rhobeg=1, tol=1e-4, maxiter=200 |
| Đo cuối | 1.024 shots, seed=100060; seed config=60 |
| Tài nguyên | CPU 4 luồng, Aer 2.048 MiB, RAM khả dụng tối thiểu 2 GiB, 600 giây/lượt |

Objective CVaR được tính chính xác từ phân phối statevector, không dùng samples huấn luyện. Thay đổi này tách tác động của objective khỏi sai số shots. Phép đo cuối vẫn tạo bitstring thực sự; không sửa bit/slack sau khi đo. Đây là đối chứng simulator, không phải quy trình tối ưu đã chạy trên QPU.

Chỉ chạy hai lượt mới. Kết quả mean cũ được dùng lại làm baseline, không tính thành hai lần lặp mới. Cùng seed giữa hai phương pháp không tạo ra các lần lặp thống kê độc lập. Báo cáo riêng theo từng khởi tạo.

## Công thức dùng trong mã

Sắp xếp các mức năng lượng E_j theo thứ tự tăng dần, với xác suất p_j. Lấy:

    w_j = min(p_j, max(0, alpha - sum_{k<j} p_k))
    CVaR_alpha = sum_j w_j E_j / alpha

Đây là trung bình của alpha khối lượng xác suất thấp nhất. Nếu alpha cắt ngang một mức năng lượng, chỉ lấy phần xác suất đủ đến alpha. Các trạng thái cùng năng lượng có thể gộp lại; không chọn 10% số bitstring.

Ví dụ E=[0,2,10], P=[0.05,0.20,0.75], alpha=0.1: lấy 0.05 ở E=0 và 0.05 ở E=2, nên CVaR=1. Với alpha=1, CVaR bằng năng lượng trung bình. Mã kiểm tra các trường hợp xác suất bằng 0, mức năng lượng trùng nhau và biên nằm trong một khối xác suất.

Optimizer nhận `(CVaR_QUBO - offset)/kappa`. Vì kappa dương, phép đổi đơn vị bảo toàn thứ tự năng lượng và tương thích với cách chuẩn hóa objective mean. Mạch cost Hamiltonian không thay đổi. Report ghi `optimizer_objective_value` cho CVaR và `exact_diagnostics.exact_mean_qubo_energy` cho trung bình; không gán nhãn CVaR thành mean.

Alpha=0.1 là lựa chọn thử nghiệm có giới hạn, chưa được chứng minh tối ưu cho bài toán này. CVaR vẫn tối ưu QUBO đầy đủ gồm slack, không trực tiếp tối đa hóa xác suất placement tối ưu của x/y.

## Chạy trong VS Code

1. Giải nén gói cập nhật vào thư mục gốc `nt409-task-placement`. Gói thêm `src/cvar_experiment.py`, test CVaR, notebook 14 và tài liệu. Bản sửa UTF-8 của `tests/test_depth_campaign.py` được kèm lại. Không thay runner mean/sampled.
2. Trong terminal của Conda `nt409-khiem`, chạy:

   ```powershell
   python -m unittest discover -s tests
   ```

   Bộ hiện tại có 72 test. Các cảnh báo deprecation/sparse có thể vẫn xuất hiện; kiểm tra dòng kết luận `OK`.
3. Mở `notebooks/14_qaoa_cvar_choice.ipynb`, chọn kernel đã chạy notebook 13, Restart Kernel.
4. Giữ `ALPHA=0.1`, `RESUME_MANIFEST=None`, đường dẫn baseline có sẵn. Gói kèm nguyên bản manifest và hai report notebook 13 bạn đã gửi.
5. Chạy Bước 1–4. Bước 3 cần hiện 2 lượt, 20 qubit, p=1, maxiter=200, E_min=1. Bước 4 kiểm tra lại các góc baseline, rồi chấm cả CVaR và mean trên cùng góc.
6. Chạy Bước 5–10. Ghi lại manifest. Bước 6 lưu từng lượt hoàn tất, kể cả khi 0 mẫu tối ưu hoặc optimizer hết ngân sách.
7. Cuối notebook cần hiện:

   ```text
   PASS — p1_choice: 2/2 exact CVaR completed, alpha=0.1, independent final sampling verified.
   ```

8. Save As thành `14_qaoa_cvar_choice_executed.ipynb`. Gửi notebook có output và ZIP `cvar_choice_<timestamp>.zip` được in tại Bước 10. ZIP chứa manifest, hai report nguồn và CSV.

Không nâng phiên bản môi trường chỉ cho đối chứng này. Nếu runtime khác baseline, ghi rõ đối chứng khác môi trường; nếu nội dung mã lõi khác, notebook dừng để review. Khác biệt xuống dòng LF/CRLF được kiểm tra riêng.

## Resume và dữ liệu

Kết quả mới nằm trong `data/reference_results/phase4f_cvar_runs/`. Điền manifest CVaR vào `RESUME_MANIFEST`, Restart Kernel, giữ cấu hình rồi chạy từ đầu. Lượt hoàn tất được xác minh/bỏ qua; lượt bị ngắt giữa chừng phải chạy lại. Không dùng manifest notebook 13 để resume CVaR.

Manifest lưu hash thiết kế, baseline, module CVaR và report. Report giữ lịch sử objective, lý do dừng, góc cuối, số shots, seed, samples, mean/CVaR và các xác suất lý tưởng. Resume từ chối dữ liệu sai phương pháp, cấu hình thay đổi hoặc report bị chỉnh sửa. Đọc/ghi JSON dùng UTF-8.

## Đọc kết quả và giới hạn kết luận

- So CVaR ở góc mean với CVaR ở góc CVaR; không so số CVaR trực tiếp với số mean rồi gọi đó là cải thiện.
- Chỉ số chất lượng chính là `delta_P_opt_pp`: P_opt lý tưởng mới trừ P_opt lý tưởng cũ, theo điểm phần trăm.
- Xem riêng P_feasible, P_ground, số mẫu optimal, E_mean, số đánh giá, stop reason và thời gian.
- Nếu CVaR giảm mà P_opt không tăng, việc cải thiện objective mới chưa cải thiện mục tiêu placement.
- Nếu P_opt tăng ở cả hai khởi tạo, đó là tín hiệu trong phạm vi đã thử, chưa phải chứng minh ổn định trên seed/instance khác.
- Hai khởi tạo cho kết quả khác nhau phải được báo cáo đầy đủ, không chỉ giữ lượt tốt nhất.
- Không tự đổi alpha, mở rộng p hoặc đổi mixer theo kết quả vừa thấy. Chọn một thí nghiệm tiếp theo có giới hạn sau khi review.

## Nguồn

Barkoutsos et al., *Improving Variational Quantum Optimization using CVaR*, Quantum 4, 256 (2020), https://arxiv.org/abs/1907.04769. Nghiên cứu này đề xuất thay cách tổng hợp năng lượng trong tối ưu lượng tử biến phân. Công thức rời rạc ở trên lấy chính xác khối lượng alpha, bao gồm phần xác suất tại biên.
