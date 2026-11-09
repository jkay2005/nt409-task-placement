# Kiểm chứng phần mềm — Notebook 22 v2

Ngày chuẩn bị: 23/10/2026. Đây là ghi nhận QA, không phải báo cáo kết quả chiến dịch thí nghiệm chính.

## Thay đổi của v2

- Thống nhất **một input a3_dev_n5, 5 task + 3 host**, cung cấp ngay trong gói; bỏ hai input hai-host khỏi kế hoạch Notebook 22.
- Dùng domain-wall ba-host và penalty 4 hiện có; 25 qubit, scale 65.5. Hai độ sâu p=1,2 có tổng 12 lượt chính.
- Tạo đường chéo QUBO theo block để hạn chế RAM phụ; nhánh exact khi huấn luyện chỉ tính mean-energy. Thêm hiệu chuẩn và ước lượng chi phí trước huấn luyện, cùng tùy chọn PREPARE_ONLY.
- Giữ nguồn cũ, Notebook 21 và kết quả A/B/C; không đổi dependency, chưa push remote.

## Bằng chứng kiểm tra

Môi trường QA: Linux x86_64, Python 3.12.14, Qiskit 2.5.2, Aer 0.17.2, qiskit-optimization 0.7.0, NumPy 2.3.5, SciPy 1.17.0.

- **14/14 kiểm thử mới qua; 142/142 kiểm thử toàn bộ nhánh A qua.** Có kiểm tra đa thức năng lượng độc lập, decoder/domain-wall, Statevector độc lập, counts, hai nhánh huấn luyện, seed, resume, audit, input bị đổi/nhân đôi và resource guard. Fixture nhỏ chỉ dùng cho unit test, không phải bộ dữ liệu nghiên cứu thứ hai.
- **9/9 cell Python chạy tuần tự bằng IPython**, trên chính input a3_dev_n5 25 qubit với protocol QA rút gọn: p=1, 1 exact + 1 shots, cap 6, training 32 shots, final 64 shots, 2 batch hiệu chuẩn. Kiểm tra được huấn luyện, lưu, summary, hình và ZIP có audit PASS/complete True cho kế hoạch QA hai lượt. Điều này không có nghĩa đủ 12 lượt chính.
- **Kiểm tra riêng p=2 tại 25 qubit**, điểm cố định [0.23,-0.11,0.7,1.2] có cả hai lớp khác 0, chạy exact và đo 1024 shots. Đối chiếu thêm năng lượng và tính hợp lệ của 64 bitstring đo được với công thức/decoder độc lập. Chưa chạy tối ưu đầy đủ p=2 hoặc campaign chính trên máy người dùng.
- Đánh giá p=1/p=2 trên 25 qubit hoàn tất trong môi trường QA. RSS đỉnh từng tiến trình khoảng 1.3 GiB; không phải tổng RAM bảo đảm trên Windows, cũng không phải số đo toàn campaign nhiều evaluator. Chi phí thực tế cần đọc từ cell hiệu chuẩn trên máy chạy.
- Định dạng notebook hợp lệ bằng nbformat; bản bàn giao có output rỗng, execution_count=None. Hình QA có nhãn KIỂM THỬ PHẦN MỀM; dữ liệu/hình/notebook QA đã chạy không nằm trong gói bàn giao.
- Môi trường QA không cho khởi động kernel Jupyter qua socket (TCP/IPC: Operation not permitted). Vì vậy kiểm tra cell dùng IPython trực tiếp; chưa xác nhận tích hợp VS Code/Jupyter hoặc thực thi trên Windows.

## Nguồn nền và giới hạn

Nguồn nền kiểm tra tương thích: nhánh backup/a-phase4-20261013, commit `d88b0af59cb29e058b86da21d3d88e121572e7db`. Không yêu cầu checkout/reset repo hiện có về commit đó. Các nguồn nền không bị thay đổi; input và QUBO v2 có fingerprint cố định.

Nếu fingerprint/test không khớp, giữ traceback để đối chiếu phiên bản trước khi sửa. Các cảnh báo deprecation Qiskit/sparse SciPy không làm kiểm thử thất bại. SHA256SUMS.json trong ZIP kiểm tra byte bàn giao, không phải chữ ký xác thực tác giả. Kết luận về chất lượng chỉ được đưa ra sau khi có dữ liệu từ chiến dịch chính đủ kế hoạch.
