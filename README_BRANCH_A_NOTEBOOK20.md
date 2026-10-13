# Chạy Notebook 20 trên Windows

Gói này thêm campaign test vào dự án đã chạy Notebook19. Chỉ nhánh A.
Giải nén vào root `nt409-task-placement`. Không cần chạy lại Notebook13–19.
Không đổi hoặc ghi đè nguồn/kết quả 19.

## Trước khi chạy

```bat
conda activate nt409-khiem
python -m unittest discover -s tests
```

Kết quả mong đợi:128 tests, OK. Giữ kernel/môi trường đã dùng cho Notebook19.
Nếu import module mới báo lỗi, kiểm tra ZIP được giải nén vào đúng root, không
lồng thêm folder. Không cần cài dependency mới.

Mở `notebooks/20_three_host_frozen_test_campaign.ipynb`. Chọn kernel
`nt409-khiem`, Restart Kernel → Run All. Mỗi lượt chạy tuần tự, không mở hai
kernel cùng campaign. Pilot ZIP19 được audit trước khi cho tạo campaign.

Cell1 mặc định dùng đường dẫn ZIP19 vừa chạy:

```
data/reference_results/phase4k_three_host_pilot/pilot_20261012T073256184704Z/pilot_20261012T073256184704Z.zip
```

Nếu ZIP ở chỗ khác trong dự án, sửa `PILOT_ARCHIVE` trong cell1. File phải là
ZIP đầy đủ chứa raw attempts, không chỉ assessment/CSV hoặc ảnh. Không cần
copy lại nếu đường dẫn mặc định đã tồn tại.

## Lần đầu và các phiên tiếp theo

- Lần đầu: `RESUME_DIR=None`, `RETRY_FAILED=False`.
- `MAX_NEW_TRIALS=None` chạy toàn bộ còn lại trong ngân sách. Có thể đặt18
  để chia theo vòng seed; không giảm90 planned trials.
- Cell2 in đường dẫn `RESUME_DIR`; lưu ngay đường dẫn này.
- Lần sau Restart Kernel, đặt `RESUME_DIR` bằng đúng đường dẫn đã lưu rồi
  Run All. Lượt completed không chạy lại, source/runtime/config phải khớp.
- Giữ nguyên file code/protocol/seed/shots. Không cập nhật môi trường giữa
  campaign. Ngân sách6giờ được tích lũy, không reset khi resume.

Đợi từng cell kết thúc. Không cần kết quả tối ưu mới tiếp tục; kết quả âm và
lượt lỗi đều được ghi. Nếu phải dừng giữa training, ưu tiên Interrupt/ Ctrl+C,
đợi report lưu xong rồi chạy cell7–9 để xuất snapshot. Nếu kernel chết hẳn,
resume sẽ xử lý interruption và tính phần thời gian không xác nhận bảo thủ;
khoản đó có thể gồm cả thời gian máy nghỉ. Không xóa campaign để né khoản này.

`RETRY_FAILED=False` giữ các lỗi không phải interruption. Đừng tự bật retry
nếu chưa xác định nguyên nhân; retry và thời gian của nó vẫn nằm trong ledger.
Khi hết ngân sách, việc chỉ còn90 row với một số pending là bình thường, không
phải lỗi export. Dự báo4,39giờ từ pilot không bảo đảm hoàn tất90 lượt.

## Notebook thực hiện gì

1. Nạp dataset/protocol đã khóa và khai báo lựa chọn phiên.
2. Audit pilot19, tạo/resume campaign90 lượt, in lịch cố định.
3. Kiểm chứng6model/reference và đo baseline cổ điển trên cùng input.
4. Hiển thị hai control riêng: uniform bit và random placement.
5. Chạy18resource probes; xuất snapshot dù training chưa bắt đầu.
6. Chạy các trial theo lịch khi đủ probes/ngân sách; giữ mọi status.
7. Audit và tổng hợp theo instance/p; plot SD theo completed seeds.
8. Đối chiếu timing warm-process với QAOA; hiển thị phạm vi đo.
9. Xuất ZIP cuối, coverage/budget và hướng dẫn resume.

Gửi lại **ZIP ở cell9** và **notebook đã Save sau khi chạy**. Có thể gửi bản
partial nếu dừng do thời gian/RAM. File quan trọng nằm trong ZIP: raw reports,
`test_results.csv`, `summary.json`, `campaign.json`, plot và checksum; ảnh
riêng không đủ để đánh giá.

Chi tiết khoa học và accounting: `docs/three_host_test_protocol.md`.
Kiểm thử Linux đi kèm chỉ xác nhận phần mềm trên dữ liệu tiny; không thay thế
test chính thức hoặc dự báo thời gian Windows.
