# Notebook 28 — hướng dẫn T4c, ba input kiểm chứng 5 task × 3 host

## Mục đích và vị trí trong kế hoạch

N27 đã hoàn tất trên development a3_dev_n5. Ở p2, valid_dw có P_opt cao hơn nhánh chuẩn trên input đó; điều cần kiểm chứng tiếp là kết quả có lặp lại trên dữ liệu khác không. N28 dùng đúng ba input đã khóa từ N26, không tạo/chọn lại input sau khi xem N27.

Mỗi input riêng vẫn **5 task × 3 host, 25 qubit**. Ba case không gộp thành bài toán15task hoặc9host. Giữ cả ba nhánh standard_x,valid_x,valid_dw. Kết quả tốt/xấu/không tìm thấy optimum đều phải giữ và báo cáo.

| Case | Assignment khả thi /243 | Assignment tối ưu | Optimum | Ý nghĩa |
|---|---:|---:|---:|---|
| v5x3_1 |78|4|2host|Tách P_valid và P_opt|
| v5x3_2 |1|1|3host|Case chặt;P_opt=P_valid|
| v5x3_3 |14|14|3host|P_opt=P_valid|

Đây là oracle đã có từ N26, không phải kết quả QAOA dự đoán. Cỡ mẫu validation là3; không phải9nhánh hay18stage. Đây là mẫu tổng hợp có điều kiện, không đại diện mọi workload.

## Bước1 — đặt gói vào repo hiện có

1. Giữ nguyên repo/môi trường nt409-khiem đã chạy N27 và toàn bộ thư mục kết quả N27. Lưu notebook N27 cùng ZIP đã gửi.
2. Giải nén nt409_notebook28_validation5x3_v1.zip **vào thư mục gốc repo**, nơi có src/,notebooks/,tests/,data/. Các thư mục trùng tên được ghép; không tạo repo mới và không đặt cả gói lồng thêm một cấp.
3. Mở notebooks/28_domain_wall_training_validation.ipynb bằng VS Code/Jupyter, chọn kernel **nt409-khiem**. Nếu vừa dùng notebook khác, restart kernel trước khi chạy N28 để nạp đúng mã.

Gói chỉ thêm experiments/domain_wall_validation.py,notebook28,test và hai README. Không sửa src/ hoặc N27. Vì vậy guard nguồn của N27 vẫn sử dụng được. Chưa cần cập nhật/cài thêm package. Những thay đổi package hoặc src/ bên ngoài gói có thể làm guard N27/N28 chặn; gửi lỗi để kiểm tra, không xóa guard.

Nếu dùng PowerShell, tại đúng thư mục repo có thể giải nén bằng:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\nt409_notebook28_validation5x3_v1.zip" -DestinationPath .
```

Điều chỉnh đường dẫn ZIP nếu trình duyệt lưu nơi khác. Không chạy lệnh từ bên trong notebooks/.

## Bước2 — chạy hai ô mã đầu để kiểm tra

Ô1 tìm repo,import runner và in RAM. Ô2 đọc N27_ACTIVE.json,kiểm campaign N27 đã hoàn tất,khóa dữ liệu/source/runtime cho N28; chưa chạy optimizer. N27 của bạn có570/600lượt vẫn hợp lệ; không cần chạy bù30lượt.

Lần đầu phải thấy:

```text
software_validation: False
v5x3_1 | qubits 25 | cap 600
v5x3_2 | qubits 25 | cap 600
v5x3_3 | qubits 25 | cap 600
Stages: 18 | total objective cap: 1800
Completed: 0 /18 | objective: 0 / 1800
```

Các dòng thực tế còn có hash và đường dẫn. Nếu mở lại lượt đang chạy dở, Completed/objective sẽ tiếp tục từ giá trị cũ, không trở về0. N28 tạo con trỏ data/reference_results/phase5_domainwall_validation/N28_ACTIVE.json để tránh vô tình tạo nhiều lượt chính.

## Bước3 — chạy lần lượt từng case, từng nhánh

Notebook có13ô mã:2ô chuẩn bị,9ô huấn luyện và2ô tổng hợp/xuất. Thứ tự huấn luyện:

| Thứ tự | Case | Ba ô nhánh phải chạy theo thứ tự | Cap/case |
|---|---|---|---:|
|1|v5x3_1|standard_x → valid_x → valid_dw|600|
|2|v5x3_2|standard_x → valid_x → valid_dw|600|
|3|v5x3_3|standard_x → valid_x → valid_dw|600|

**Mỗi ô nhánh tự chạy p1 rồi p2**:p1 khởi tạo[beta,gamma]=[0.3,1.0],cap100;p2 dùng INTERP từ điểm mean-energy tốt nhất của chính p1 trong cùng case/nhánh,cap100. Không lấy góc N27 hoặc case trước làm góc mới. Đây là kiểm chứng cùng quy trình học trên input khác, không phải kiểm thử chuyển nguyên góc đã học sang input mới.

COBYLA,rhobeg1,tol1e-4,exact mean-energy,max_abs scaling,penalty4,Aer CPU4threads,RAM còn≥4GiB giữ nguyên. Mô hình/Hamiltonian/offset/scale được dựng riêng từ mỗi input; không dùng lại offset248.5 hoặc scale65.5 của development. Oracle chỉ chấm điểm, không chọn góc.

Trước eval1,code dựng diagonal và biên dịch mạch nên có thể chờ hàng chục giây hoặc hơn. Sau đó log in ở eval1 và mỗi10lượt. Cuối mỗi ô có bảng trạng thái và xuất checkpoint ZIP. Mỗi nhánh hoàn tất sẽ in thông báo có thể nghỉ rồi tiếp tục ô kế tiếp.

Dự trù một buổi khoảng3–4giờ cho cả ba case, dựa trên N27 khoảng51phút/case; đây chỉ là ước lượng, không phải giới hạn hay cam kết. Có thể chia nhiều phiên và nghỉ **sau khi ô nhánh kết thúc**. Chỉ chạy một runner,giữ máy đủ nguồn và tránh sleep trong ô đang huấn luyện. Không đổi kernel/package/source khi tiếp tục campaign dở.

## Bước4 — đọc bảng và trạng thái dừng

- completed nghĩa stage hoàn tất tối ưu hóa và chấm cuối theo protocol,không bảo đảm hội tụ toàn cục.
- success=False/MAXFUN ở cap100 là kết thúc theo ngân sách. Không tự tăng cap.
- Optimizer dừng sớm theo tiêu chí của nó có thể dùng ít hơn100lượt; không chạy bù hoặc chuyển lượt dư sang stage khác.
- P_domain: assignment đúng mã;P_valid: CPU/RAM và y đo được hợp lệ;P_opt: đạt optimum placement;P_ground: cả slack cũng tạo năng lượng QUBO tối thiểu.
- Với v5x3_2 và v5x3_3,optimum3 nên P_opt=P_valid. Đó là đặc điểm objective,không phải lỗi đánh giá.
- Zero optimal shots không chứng minh vô nghiệm hoặc P_opt=0. Exact metrics là chính;final1024shot chỉ minh họa.
- Cùng phương pháp có thể tốt ở case này,xấu ở case khác. So sánh các nhánh **trong cùng case**;raw mean-energy giữa các case khác nhau không phải thang chất lượng chung.

Final seed theo thứ tự ba validation case là20261025,20261026,20261027. Cùng case,các nhánh dùng cùng seed để tái lập,không tạo thêm instance độc lập. Huấn luyện dùng mean-energy exact,không dùng shot ngẫu nhiên làm objective.

Tối đa1800objective +18final exact +9final sampling =1827lời gọi mô phỏng native nếu mọi stage hoàn tất;9sampling call chứa tổng9216shot. Có thêm setup/kiểm dữ liệu/lưu và export. elapsed_stage_seconds không phải toàn bộ wall-clock campaign. Không kết luận ưu thế tốc độ từ một lượt chạy hoặc từ thời gian mô phỏng CPU.

## Bước5 — nghỉ, tiếp tục hoặc xử lý lỗi

Chạy lại hai ô đầu và các ô nhánh đã chạy là an toàn khi dữ liệu còn nhất quán:các stage completed được bỏ qua,không nhận ngân sách mới. Runner không cho bỏ qua case/nhánh chưa chạy. Lần mở lại dùng đúng N28_ACTIVE.json và cùng campaign.

Checkpoint mỗi evaluation lưu điểm/energy/ngân sách,**không lưu đầy đủ trạng thái nội bộ COBYLA**. Vì vậy chỉ resume tự động ở ranh giới stage đã hoàn tất. Nếu stage failed/interrupted/running,giữ nguyên bằng chứng;runner dừng để kiểm tra,không tự bắt đầu lại stage từ đầu.

Nếu có lỗi:

1. Giữ nguyên output lỗi và Save notebook.
2. Chạy ô export cuối nếu writer đã dừng và dữ liệu còn nhất quán.
3. Nếu kernel/PC chết cứng để lại RUNNING.lock hoặc raw/ledger không khớp,nén thư mục t4c_<timestamp> bằng Explorer và gửi cùng lỗi.

Không xóa N28_ACTIVE.json,RUNNING.lock,raw hoặc ledger;không sửa input/góc/cap để ép tiếp tục. Giới hạn2400giây/stage và guardRAM4GiB được kiểm giữa native calls;không phải cơ chế ngắt cưỡng bức một lời gọi native đang chạy,không cam kết peakRAM.

## Bước6 — tổng hợp,xuất và gửi kết quả

Sau ba case,chạy hai ô cuối. Kết quả hoàn tất cần có COMPLETE:True và Completed18/18;objective có thể nhỏ hơn1800. Save notebook rồi gửi:

- notebooks/28_domain_wall_training_validation.ipynb đã chạy.
- ZIP t4c_<timestamp>.zip theo đường dẫn ô cuối in ra.
- data/reference_results/phase5_domainwall_validation/N28_ACTIVE.json.

Không cần gửi toàn repo. ZIP chứa ba input,dataset,nguồn,ledger,18raw report khi hoàn tất,summary và checksum. Giữ bằng chứng N27 để truy vết tiền đề.

## Bước tiếp trong kế hoạch một tháng

T4c chỉ được đánh dấu hoàn tất sau khi kết quả chính thức của bạn được kiểm toán. Phần còn lại là MILP cùng bốn input ở T5,tổng hợp giới hạn/T6,bảng kết quả/T7,người khác tái lập/demo/T8 và bàn giao/T9. Giữ mốc06/11 quyết định hướng mixer,13/11 khóa kết quả,20/11 bàn giao kỹ thuật. Báo cáo/thuyết trình thực hiện sau tháng thực nghiệm như đã thống nhất.

Kiểm tra phần mềm của người chuẩn bị dùng software_validation=True,cap6/stage nhưng vẫn đúng5×3/25qubit. Đây là QA tách riêng,không phải kết quả chính thức1800cap và không dùng để chọn lại protocol. Bạn chỉ chạy notebook mặc định software_validation=False.
