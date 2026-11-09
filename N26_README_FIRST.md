# Notebook 26 — kiểm toán tập dữ liệu 5×3 trước huấn luyện

Gói này chứa code/notebook chạy được, không chỉ là tài liệu. Giải nén vào **thư mục repo đang chạy được Notebook25**, giữ cấu trúc `src/`, `data/`, `notebooks/`, `tests/`, `docs/`. Gói chỉ thêm file; không sửa source/input cũ của Notebook22–25. Nếu đã import module N26 trong kernel trước khi cập nhật gói, restart kernel.

## Chạy trên Windows

1. Mở VS Code ở thư mục repo; chọn kernel `nt409-khiem` như Notebook25.
2. Mở `notebooks/26_validation_dataset_5x3.ipynb`, chọn Run All.
3. Xem `PASS`, bảng bốn case và hai loại chứng cứ CPU/RAM. Notebook có sáu ô code, không optimizer/statevector, không cần cài thêm package so với Notebook25. Không cần OR-Tools cho bước này.
4. Save notebook đã chạy. Gửi lại notebook và ZIP có đường dẫn ở ô cuối: `data/reference_results/phase5_validation5x3/audit_<timestamp>.zip`.

Không sửa `dataset.json`, seed hoặc thứ tự task/host. Nếu báo lỗi hash, dừng và giữ output lỗi; không tắt kiểm tra. Có thể chạy lại Run All; mỗi lượt tạo thư mục mới, không ghi đè lượt cũ.

## Vì sao có bước này?

Case a3_dev_n5 cũ có CPU dư thừa so với RAM trong bài toán placement. Nó vẫn dùng cho development và kiểm chứng mixer, nhưng không đủ để đánh giá hai tài nguyên. Bộ mới giữ kích thước **5 task ×3 host/25 qubit**, thêm ba case có CPU/RAM không suy ra nhau. Mọi phương pháp được so cùng input/hash trong từng case.

Đã duyệt pool25.740 cấu hình multiset;752 có nghiệm,416 qua điều kiện độc lập tài nguyên và không đồng nhất; sau loại tương đương/lịch sử còn217. Chọn bằng SHA256 với seed20261025 theo ba tầng có5/106/106 phần tử. Quy tắc đầy đủ trong `docs/validation5x3_protocol_vi.md` và trong notebook. Việc chọn không dùng kết quả QAOA/FF/BFD.

Các demand/capacity vẫn là số nguyên nhỏ và có thể lặp. Tính khách quan được cải thiện bằng quy tắc có thể tái lập, công bố điều kiện chọn và giữ nguyên case thất bại; không xác định bằng việc dãy số “trông ngẫu nhiên”. Đây là mẫu tổng hợp có điều kiện, chưa đại diện workload thực tế.

## Kết quả chuẩn Linux

| Case | Khả thi/243 | Tối ưu/243 | Số host tối ưu | FF | BFD |
|---|---:|---:|---:|---|---|
| a3_dev_n5 |90|8|2|3|3|
| v5x3_1 |78|4|2|3|3|
| v5x3_2 |1|1|3|Không tìm được|Không tìm được|
| v5x3_3 |14|14|3|3|3|

Số3 trong FF/BFD là số host của nghiệm tìm được. “Không tìm được” không chứng minh vô nghiệm: oracle đã tìm được một assignment khả thi ở v5x3_2. Với optimum3 thì P_opt=P_valid theo mục tiêu số host. MILP chưa chạy trong notebook này; T5 chưa hoàn tất.

QUBO/Ising khớp326 vector bậc2 mỗi case;8192 base kiểm chính xác slack;25 qubit/case. T3 đã chứng minh tính đúng khối mixer; chưa có optimizer trên ba input mới. Các kết quả lịch sử giữ nguyên, không gắn nhãn lại thành test mới.

## Bước sau

T4 sẽ chạy ba nhánh standard_x/valid_x/valid_dw trên development trước, sau đó áp dụng nguyên cấu hình cho ba case mới. Mỗi nhánh/instance100 evaluation p1 +100 p2 INTERP, mean-energy/COBYLA, không chọn góc theo P_opt. Tổng cap2400 objective evaluations; final scoring, setup và sampling được tính thêm, không coi là miễn phí. Notebook huấn luyện sẽ được triển khai sau khi chốt kiểm toán N26; không dùng hàm `make_evaluator` chỉ chấp nhận a3_dev_n5 của Notebook25 để lách kiểm tra input mới.

Thử kiểm tra tập trung nếu cần:

```bash
python -m unittest discover -s tests -p "test_validation5x3.py"
```
