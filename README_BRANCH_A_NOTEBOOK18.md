# Notebook 18 — Tổng hợp đối chứng và đo chi phí, chỉ nhánh A

## Cài đặt và chạy trên Windows

1. Giải nén `nt409_notebook18_controlled_summary_v1.zip` vào thư mục gốc `nt409-task-placement`, nơi có `src/`, `tests/`, `notebooks/`. Giữ nguyên cấu trúc thư mục. Gói này bổ sung vào dự án đã cài Notebook17; không thay thế cả repository.
2. Gói có nguyên archive Notebook17 Windows `20261011T034920393465Z`, đặt tại `data/benchmarks/nt409_summary_v1/notebook17_results.zip`. Bên trong có baseline16. Không cần chép lại kết quả thủ công hoặc chạy lại Notebook13–17.
3. Trong terminal ở gốc dự án:

```bat
conda activate nt409-khiem
python -m unittest discover -s tests
```

Trên bộ nguồn hiện tại có107 tests. Nếu bạn bổ sung test riêng, số lượng có thể khác; điều kiện là `OK`, không có fail/error. Không cài lại dependencies nếu kernel hiện tại đã chạy được Notebook17.

4. Mở `notebooks/18_branch_a_controlled_summary.ipynb`, chọn kernel `nt409-khiem`, Restart Kernel rồi chạy lần lượt tám bước. Đóng ứng dụng nặng trước bước5 để giảm nhiễu timing. Giữ cấu hình mặc định trong lượt chính thức.
5. Bước2 audit báo tiến độ mỗi5 report, có thể mất vài phút. Đây là kiểm tra mẫu cũ, không phải tối ưu/mô phỏng lại QAOA. Nếu báo source/hash mismatch, giữ traceback và gửi lại; không tắt kiểm tra hoặc xóa dữ liệu.
6. Bước8 in ZIP kết quả trong `data/reference_results/phase4j_summary/summary_<timestamp>/`. Save notebook rồi gửi **ZIP này + notebook đã Save**. Không cần gửi từng CSV/PNG riêng.

Notebook18 không cần resume chiến dịch lượng tử vì không chạy QAOA. Mỗi lần chạy bước1 tạo thư mục tổng hợp mới. Nếu chạy lại một bước trong cùng kernel, chỉ dữ liệu dẫn xuất trong thư mục mới có thể được cập nhật; hai archive đầu vào không bị sửa.

## Tám bước làm gì?

| Bước | Việc thực hiện | Cách hiểu |
|---|---|---|
| 1 | Đọc benchmark đóng băng, chọn archive và cấu hình timing | Giữ cùng dữ liệu, tạo nơi xuất mới |
| 2 | Audit toàn bộ archive16/17 và dựng lại CSV từ report | Chỉ tổng hợp sau khi dữ liệu nhất quán |
| 3 | Duyệt16 phân công để tính đối chứng chính xác | Tách uniform bit và random chọn host |
| 4 | Tổng hợp45 lượt/encoding theo instance và p | Phân biệt tỷ lệ mẫu tối ưu và tỷ lệ lượt thành công |
| 5 | Đo exact enumeration và random1024 bằng nhiều block | Số đo thật của máy đang chạy, không giả định thời gian |
| 6 | Đặt chất lượng và chi phí cạnh nhau, nêu phạm vi phép đo | Không đồng nhất trial timing với toàn notebook |
| 7 | Vẽ ba đồ thị có cả hai đối chứng | Cải thiện QAOA cũ chưa đủ để vượt random |
| 8 | Xuất bảng, timing thô, audit, provenance, ảnh và input | Có thể kiểm tra lại nguồn của mọi con số |

## Những khái niệm quan trọng

- **P_opt:** số mẫu cuối có phân công tối ưu / tổng mẫu cuối. Một mẫu có thể có placement tối ưu nhưng slack chưa tối ưu; vì vậy P_opt khác P_ground.
- **P_feasible:** tỷ lệ mẫu cuối giải mã thành phân công hợp lệ. Không sửa task/y của QAOA để tăng chỉ số.
- **Run success:** batch cuối của một lượt QAOA có ít nhất một nghiệm tối ưu. 45/45 không có nghĩa P_opt=100%.
- **Uniform:** lấy đều các bit trong từng encoding. Compact loại bỏ vi phạm one-hot nên uniform của nó khác mã hóa cũ.
- **Random assignment:** mỗi task chọn host0/1, y được suy ra từ host có task. Không sửa quá tải. P_opt chính xác choice/tight/reference lần lượt6,25%/25%/6,25%.
- **Exact enumeration:** duyệt đủ16 phân công, trả một nghiệm tốt nhất hoặc kết luận không có nghiệm. Đây là đối chứng nhỏ, không thay việc triển khai FF/BFD/MILP.
- **SD:** độ lệch chuẩn giữa năm seed, không phải khoảng tin cậy và không phải chứng nhận xác suất thành công99%.

Xác suất tìm ít nhất một nghiệm trong1024 lượt random được tính bằng `1-(1-q)**1024` vì q là xác suất chính xác của cùng phân phối IID. Không dùng công thức này với P_opt gộp nhiều mạch QAOA đã huấn luyện khác nhau. Input vô nghiệm có P_opt=null/ô trống.

## Phạm vi đo thời gian

Classical: warm process, calibration tự chọn số lần giải/block, sau đó bảy block. Mỗi lần giải gồm input validation, RNG nếu có, sinh/kiểm tra ứng viên và xây dựng đầu ra. Có overhead lặp/bookkeeping nhỏ được giữ nguyên, không trừ một con số ước đoán. Không gồm import/calibration/chuẩn bị ground truth; thời gian calibration được ghi riêng. Không truyền optimum vào solver để dừng sớm.

QAOA: dùng thời gian trial đã lưu ở16/17; số shot bao gồm training, batch eigenstate phụ và đánh giá cuối. Model/reference preprocessing được ghi riêng như archive gốc, không chia tùy ý vào từng trial. Không đo lại QAOA, không bổ sung thời gian audit18 vào chi phí giải cũ.

Hai nguồn thời gian là khác phiên, có thể khác tải máy. Bảng này là so sánh mô tả solver trên các triển khai được chỉ rõ; chưa phải phép đo end-to-end đồng thời, chưa so với mọi classical solver và không chứng minh quantum advantage. Nếu notebook được chạy ở Linux kiểm thử thì không trộn timing đó với Windows chính thức.

## File kết quả

- `quantum_runs.csv`:92 hàng (90 lượt chính +2 negative-controls của hai encoding), đường dẫn report thuộc archive nguồn tương ứng.
- `quantum_groups.csv`:18 nhóm chính (2encoding×3instance×3p).
- `controls.csv`:12 hàng đối chứng (3loại×4instance), có negative-control tách qua cột role.
- `classical_timings.csv`:6 phép đo (2solver×3instance), gồm thời gian block thô và calls/block.
- `cost_comparison.csv`:bảng trình bày chất lượng/thời gian ở bước6, ghi rõ cách xác định thành công.
- `summary.json`, `audit.json`:nguồn, thiết kế, môi trường, source SHA và số liệu có cấu trúc.
- `summary_quality.png`, `interpretation.md`, `sha256.json` và nguyên `notebook17_results.zip`.

## Thay đổi phần mềm

Thêm `src/branch_a_evidence.py`, `src/branch_a_summary.py`, hai tệp test và notebook/docs. Không đổi các module tạo kết quả16/17, không đổi benchmark, không thêm dependency. Đợt này không triển khai CVaR, bộ dữ liệu mới hoặc công việc B/C.

## Kiểm chứng bàn giao

Audit toàn bộ archive Windows thành công; kiểm thử có trường hợp sửa metric rồi tính lại hash vẫn bị phát hiện. Mười test mới bao phủ đối chứng/giải mã, vô nghiệm, ngân sách random, xác suất batch, timing, aggregation, ZIP/CSV và xuất bằng chứng.

Tám code cell được kiểm tra tuần tự bằng Python ở Linux: audit đầy đủ chạy một lần, sau đó kết quả audit của cùng archive bất biến được tái sử dụng trong lượt kiểm tra notebook để tránh lặp lại phép kiểm tra nặng. IPython display thay bằng xuất text và Matplotlib dùng Agg; không phải một lần chạy GUI Jupyter trên Windows. Nhật ký kiểm chứng kèm gói không thay kết quả timing máy của Khiêm.
