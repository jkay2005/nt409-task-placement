# Kiểm chứng phần mềm — không phải campaign Windows chính thức

Các báo cáo trong thư mục này chỉ dùng kiểm chứng runner. Không ghép vào45
lượt Notebook16 trên máy Khiêm. Tests/log phản ánh môi trường Linux.

- 87 tests OK, gồm13 kiểm thử mới; không phải87 lượt benchmark QAOA.
- Cả8 code cell Notebook16 được chạy bằng Python/Agg, thay hàm display của
  IPython bằng in text. Phiên chọn choice cho probe; bước runs cố ý giả lập
  thiếu RAM. Kết quả mong đợi là1 resource_blocked +45 pending, export PARTIAL.
  Đây là phép thử đường lỗi, không phải thiếu RAM thật hay campaign hoàn tất.
- Lượt reference p3 standalone dưới timeguard600/cap200 dùng training/final
  shots1024, seed70/100070, hội tụ sau53 đánh giá. Tổng runner217,506s,
  optimizer211,456s. Report đầy đủ đã qua cùng audit counts/bits/energy/output.
  Không sửa report thành2400 giây hoặc đổi nhãn thành lượt v1.1 chính thức.
- Chín probe đầu dùng guard600 giây của v1. Status vượt thời gian p2/p3 là
  kết quả ước lượng ban đầu được giữ nguyên, không phải lỗi mô phỏng.
  Chúng là cơ sở điều chỉnh v1.1 trước campaign chính thức. Probe chỉ ước lượng;
  một lượt hội tụ sớm không đảm bảo mọi seed luôn dưới600 giây.

| Instance | p | Thời gian ước lượng với dự phòng (s) | Status của probe v1 |
|---|---:|---:|---|
| p0_reference | 1 | 478.11 | passed |
| p0_reference | 2 | 1799.67 | time_estimate_exceeds_budget |
| p0_reference | 3 | 2300.56 | time_estimate_exceeds_budget |
| p1_choice | 1 | 182.24 | passed |
| p1_choice | 2 | 201.65 | passed |
| p1_choice | 3 | 224.81 | passed |
| p1_tight | 1 | 133.09 | passed |
| p1_tight | 2 | 128.42 | passed |
| p1_tight | 3 | 156.34 | passed |

Probe choice trong notebook.log chạy lại với v1.1 và đều passed. Máy người
triển khai không thay thế bằng chứng thực nghiệm trên Windows. Time guard và
RAM guard hoạt động tại boundary, không phải giới hạn cưỡng bức OS. Khóa file
được thử trên Linux; nhánh Windows dùng msvcrt chưa được chạy ở đây.
