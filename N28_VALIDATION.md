# N28 — kiểm tra trước bàn giao

Bàn giao ngày26/10/2026; kiểm tra ngày25–26/10/2026. Base N27:8db083b. Phạm vi bổ sung là T4c trên ba input khóa trong nt409_validation5x3_v1;không thay protocol sau kết quả N27.

## Thay đổi và tương thích

- Thêm experiments/domain_wall_validation.py:18stage theo đúng thứ tự3case×3nhánh×p1/p2;cap100/stage,cùng quy tắc mean-energy/COBYLA/INTERP như N27.
- Thêm notebook28 với13ô mã,9ô huấn luyện độc lập theo từng nhánh/case và checkpoint ZIP sau mỗi ô.
- Không thay byte của src/*.py hoặc notebook27. N27 theo dõi mọi module src/,nên mã N28 được đặt ngoài src/ để không làm mất khả năng kiểm tra campaign cũ.
- Identity N28 theo dõi dữ liệu,cả source src/ và runner mới,runtime,cấu hình,ba QUBO và receipt của N27 chính thức đã completed. Source mới không dùng góc/kết quả N27 để chọn tham số.
- N28 dùng TrainingEvaluator đã kiểm của N27. Vòng stage được giữ thành bản riêng nhằm giữ nguyên nguồn N27;đối chiếu AST cho thấy giống N27 sau các thay đổi đã nêu về nguồn input,factory guard và seed theo case. Không monkeypatch engine trong mã sản phẩm.
- Không thêm hoặc nâng cấp dependency. Seed final lần lượt20261025/26/27 trên ba case;không ảnh hưởng objective huấn luyện exact.

## Kiểm thử tự động

`python -m unittest discover -s tests`: **187/187 PASS**,47,593giây trong môi trường Linux ở lần kiểm cuối ngày26/10/2026. Gồm178test có sẵn và9test N28 mới. Đã chạy chu trình RED→GREEN cho plan/identity,runner và pointer/resume.

Các hành vi được kiểm:1800cap và dependency p1 riêng từng case/nhánh;dataset snapshot và thứ tự case cố định;N27 identity không đổi;primary N28 đòi N27 completed;builder từ chối development/input bị sửa;ngân sách reservation giữ khi mô phỏng lỗi;không retry stage lỗi;completed stage bỏ qua;không bỏ case/nhánh;writer lock;hash/raw/source/runtime;export incomplete;con trỏ ổn định khi mở lại.

Test điều khiển dùng simulation double tại biên mô phỏng,không dùng một instance nhỏ hơn để thay thế thực nghiệm5×3. Không xem output từ double là kết quả lượng tử. Đã kiểm thêm trên checkout có N27 completed để đảm bảo test không giả định repo người dùng chưa có dữ liệu;test thiếu N27 dùng thư mục độc lập.

## Notebook và gói overlay

- 13ô mã được parse và notebook schema hợp lệ;bản bàn giao không có output/execution_count.
- Trên checkout N27 sạch,đã thực thi cả13ô bằng InteractiveShell với simulation double. Thực thi lại13ô không đổi campaign ledger hoặc tiêu thêm ngân sách. Có marker CONTROL_FLOW_FAKE_ONLY riêng trong thư mục QA,không đóng vào gói.
- Kiểm tra này xác nhận luồng notebook/export và resume;không phải chạy1800objective thật. Chưa kiểm GUI VS Code/Jupyter hoặc runtime Windows của người dùng trước bàn giao.

## Qualification Aer thật — PASS, 17stage và một kiểm tra bổ sung

Đã kiểm cả18tổ hợp3case×3nhánh×p1/p2 trên full25qubit,software_validation=True,cap6/stage. Tổng **108objective calls và135simulation calls** cho18stage duy nhất;gồm18final exact và9final sampling×1024shot. Không huấn luyện lại với cap100 và không dùng kết quả QA chọn lại phương pháp.

Chiến dịch QA đầu hoàn tất17stage;tiến trình không còn khi quay lại phiên,stage cuối v5x3_3/valid_dw/p2 còn ởsetup,0objective/0final-exact/0sampling,history rỗng. Giữ nguyên campaign/raw/lock gốc,không xóa hay reset. Stage cuối được kiểm bằng một integration test riêng,dùng đúng p1 đã chạy làm fixture có hash và ghi nguồn. Test bổ sung chỉ thực hiện6objective+1finalexact+1sampling mới;không tính p1 fixture thành lượt chạy mới. **Không gọi campaign QA gốc là completed18/18** và không coi đây là resume nội bộ COBYLA.

Tất cả18stage được kiểm có statuscompleted và6/6objective. Mọi nhánh valid_dw giữ P_domain≈1;ởcase2/3,P_opt=P_valid và số shot tối ưu=khả thi. Seed1024shot mỗi case đúng20261025/26/27. Artifact bổ sungCRC và45checksum đạt;hash ledger gốc không đổi. Tổng elapsed các stage hoàn tất khoảng1135.937giây,không gồm thời gian setup chưa ghi nhận của lần bị gián đoạn và không dùng làm benchmark.

Runtime:Python3.12.14,NumPy2.3.5,SciPy1.17.0,Qiskit2.5.2,Qiskit Optimization0.7.0,Aer0.17.2,Linux. Bằng chứng được giữ trong qa28/native_25q,qa28/native_last_stage_integration_20261026 và qualification_combined.json tại môi trường chuẩn bị;không đóng kết quả QA vào gói scientific notebook.

## Mô hình từng case

| Case | Qubit | Offset | Max_abs scale | Pauli terms |
|---|---:|---:|---:|---:|
|v5x3_1|25|248.5|65.5|184|
|v5x3_2|25|362.5|71.5|184|
|v5x3_3|25|336.5|77.5|184|

Các đại lượng này được dựng lại từ input,không hard-code theo development.

## Giới hạn và tiêu chí nghiệm thu lượt người dùng

Scientific run Windows mặc địnhcap100/stage vẫn phải được người dùng chạy và gửi lại. Qualificationcap6/stage tách riêng,không dùng xếp hạng phương án hoặc sửa protocol. Không gắn nhãn kết quả QA thành validation chính thức.

Để nghiệm thu T4c:đúng3input/hash/25qubit,đúng18stage/phụ thuộc/budget,nguồn/runtime truy vết được,hash/archive/notebook hợp lệ,rawhistory vàfinal metrics/counts nhất quán,không chọn lại góc theo P_opt,không bỏ case thất bại. completed không đồng nghĩa hội tụ;MAXFUN ởcap100 được báo đúng.

RAM/time guards kiểm giữa native calls;không ngắt một lời gọi native đang chạy. Lưu raw và ledger là hai thao tác atomic riêng,mất điện đúng giữa hai thao tác có thể làm hash không khớp;runner sẽ chặn để giữ bằng chứng. Không resume nội bộ COBYLA giữa stage. Chưa có timing benchmark lặp,peakRAM chứng nhận hoặc mapping hardware;không tuyên bố quantum advantage.

T4c chỉ hoàn tất sau khi kiểm toán lượt chính thức. MILP T5,tổng hợp/T6–T7,tái lập/demo/T8 và bàn giao/T9 vẫn theo kế hoạch một tháng;đây không phải gói đóng toàn bộ đồ án.
