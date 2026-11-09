# N25/T3 — Phạm vi kiểm chứng

Ngày24/10/2026. Base triển khai: commit76042f1 (Notebook24). Phạm vi khoa học cố định a3_dev_n5,5 task ×3 host,25 qubit; không huấn luyện trong T3.

## Đã kiểm chứng

- Tám test mới trong test_domain_wall_mixer.py đạt: khóa input; trạng thái đầu; ma trận mixer có thứ tự; unitarity/leakage; liên thông; y/slack và một beta chung; mask243 mã hợp lệ; ba cấu hình; API RSS không khả dụng. Một số yêu cầu được kiểm tra cùng một test.
- Toàn bộ unittest của repo đạt167/167 trong102,46giây trên Linux; không có regression failure. Các warning deprecation Qiskit và SparseEfficiencyWarning được giữ nguyên, không tắt test để lấy OK.
- Full probe: ba cấu hình ×p1/p2, cùng input25 qubit. Ba kiểm tra phân phối đầu và sáu đánh giá góc cố định đều PASS; không có optimizer.
- Khối cổng so với exp(-iβB)exp(-iβA): sai lệch lớn nhất4,44e-16, leakage0, liên thông cả ba mã. Cổng cục bộ4×4 là phép chứng minh khối, không phải thay input bài toán.
- valid_dw giữ P_domain≈1 ở cả p1 vàp2 trong dung sai1e-10. valid_x có P_domain≈0,61110884 và0,37662815 ở các điểm đã định.
- Input hash và QUBO fingerprint trùng Notebook22–24. Source hashes và runtime được ghi trong probe.json; package có N25_PACKAGE_SHA256.json.
- Notebook có6 ô mã: tất cả parse được; chạy phần môi trường, bảng, assertions và export qua Python. Tại lời gọi run_probe của cell4, QA dùng lại đúng full probe đã hoàn tất để tránh mô phỏng lần thứ hai. Sáu mạch đã được chạy thật qua CLI cùng hàm run_probe.
- Notebook bàn giao output rỗng, không trộn dữ liệu QA với lần chạy Windows của người dùng.

## Số đo Linux

| Cấu hình | eval p1 (s) | eval p2 (s) | depth p1/p2 sau compile Aer |
|---|---:|---:|---|
| standard_x | 18,630 | 26,512 | 37/63 |
| valid_x | 13,566 | 22,297 | 38/64 |
| valid_dw | 18,608 | 16,977 | 39/69 |

Setup/diagonal/compile được ghi riêng, khoảng24–32giây/circuit trong lần chạy này. Một evaluation không bao gồm mọi chi phí của optimizer/campaign. Chỉ có một timed call cho mỗi circuit, không đủ kết luận variant nào nhanh hơn. RSS sau evaluation không đo được trong môi trường process hiện tại nên null; không báo0 hoặc gọi đó là peakRAM.

Lần full probe đầu dừng ở psutil.Process() sau mô phỏng do NoSuchProcess. Đã thêm regression test và optional_rss_mib(), giữ thiếu telemetry là null; lần full probe mới chạy lại cả sáu cấu hình PASS. Không bỏ qua lỗi mạch hoặc hạ guardRAM.

## Chưa được chứng minh

- Chưa chạy T4 gồm huấn luyện mean+INTERP cho ba cấu hình; chưa có winner theo P_opt.
- Chưa chạy trực tiếp GUI Jupyter/VSCode trên Windows; cần notebook output và ZIP kết quả của người dùng để đo chi phí máy đó.
- Không có phần cứng quantum/noise model; không có speedup hoặc cải thiện RAM từ việc giữ miền.
- Không coi tích AB là exponential chính xác của A+B, không suy liên thông thành hội tụ tối ưu.

## Kiểm tra trên máy nhận

```powershell
conda activate nt409-khiem
python -m unittest discover -s tests -p "test_domain_wall_mixer.py"
```

Sau8 test OK, chạy Notebook25 theo N25_README_FIRST.md. Kết quả và source của campaign cũ được giữ; không resume chúng sau thay sourcehash.
