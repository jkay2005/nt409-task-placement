# Notebook19 — kiểm chứng phần mềm Linux,12/10/2026

Đây là QA của gói cài đặt, không phải campaign Windows chính thức và không là
bằng chứng chất lượng thuật toán hoặc lợi thế tốc độ. Không dùng projection của
QA64shots/cap8 để dự báo campaign1024shots/cap200.

## Kết quả

- 119 tests PASS,33,751s,không skip. Harness chỉ sửa psutil default PID khi procfs
  container dùng host PID; các số RSS/available và guards vẫn là phép đo OS thật.
- Kiểm chứng tiny full2^11bits cho QUBO/Ising/decoder/mean/uniform/ground.
- N5 ví dụ và capacity4 regression khớp độc lập placement oracle/ground proof.
- Pool sinh lại508/82,informative146/47; split/CPU-RAM-swap uniqueness/hash đạt.
- Runner test giữ final32shots seed riêng và đếm cả Qiskit extra eigenstate batch.
- Report metrics/output/parameters bị sửa rồi rehash vẫn bị semantic audit từ chối.
- Pilot tiny resume không chạy lại completed; kernel crash ghi interrupted;
  thay protocol hoặc yêu cầu test instance bị từ chối.
- Notebook19 thực thi9code cells bằng Python tuần tự, IPython display thay bằng
  text, MatplotlibAgg,không dùng GUI Jupyter. Tám bước đầu chạy cùng namespace;
  bước export được thực thi lại ở process mới để hoàn thiện output recording,
  không chạy thêm quantum jobs. Executed validation notebook có counts1..9.
- QA dùng nguyên10input frozen, nhưng giảm64shots/cap8 và time guard600s.
  Resource guards8GiB/4GiB/4GiB/Aer2048MiB/4threads được giữ.
- 8probes PASS (6dev+2control),14trials completed (12dev+2control),test chưa submit.
- Mạch dev23/25qubit thực tế,peak process lifetimeRSS khoảng706MiB. Đây là
  Linux QA,không chứng nhận RAM hoặc thời gian Windows.
- Plot development đã xem:2panel,axes/legend/title rõ,zero-optimal outcomes giữ
  nguyên. QA không được dùng chọn p hoặc đánh giá mục tiêu chất lượng.
- 16module lịch sử vẫn khớp nguồn đã audit Notebook17Windows moduloLF/CRLF.

## Review

Correctness: polynomial/bijection oracle,invalid label/no repair,infeasible null,
shot accounting/independent sampling,partial recovery và source guards đã kiểm tra.
Architecture:4module mới,import helper có sẵn; không sửa lịch sử vì source hash
đang ràng buộc kết quả16–18. Không thêm thư viện hoặc generic framework mới.
Boundaries:loader có frozen canonical hashes và path containment;archiveexport
giữ raw reports và checksums. Source/runtime resume phải khớp phiên cũ.
Performance:base reference8192vectors,không dựng2^25cost lookup;gate simulation
chạy tuần tự. Guards ở boundary không ngắt native call;peakRSS lifetime có cả hoạt
động kernel trước đó. Warm classical timing loại imports/calibration/reference.

## Bước tiếp

Khiêm chạy Notebook19 trên Windows nt409-khiem theo README. Review ZIP và saved
notebook trước budget C2/Notebook20. Chưa FF/BFD/MILP trong gói A này; không gọi
đã hoàn tất đối chiếu tất cả classical proposal. Không có tiêu chí27/30,24/30
và không chọn p qua2seed development.
