# Phase 4A — khảo sát ba host, protocol pilot v2

Ngày 12/10/2026. Đây là phần tiếp tục nhánh A sau checkpoint Notebook18.

## Mục tiêu

Khảo sát thay đổi P_feasible, P_opt, lift và chi phí từ 4 lên 5 task với 3 host,
cùng mã hóa domain-wall và mean-energy/X/COBYLA. Đây là khảo sát kích thước nhỏ,
không chứng minh quy luật scaling, tốc độ vượt classical hoặc quantum advantage.
Kết quả hai host16–18 là lịch sử riêng, không là đối chứng chỉ thay số host.

## Giả thuyết và đánh giá

- H1: tăng task có thể giảm xác suất khả thi/tối ưu; chiều thay đổi lift chưa biết.
- H2: tăng p có thể giảm mean QUBO energy nhưng không tăng chất lượng placement.
- H3: lift so uniform mã hóa có thể dương trong khi thấp hơn random placement.
- Báo p1/p2/p3 ngang nhau; pilot không chọn p thắng để công bố như chọn trước.
- Bỏ ngưỡng27/30,24/30. Chấm per-shot lift/difference và observed batch success
  so với xác suất control IID chính xác của từng instance.
- Không áp công thức IID cho pooled P_opt từ nhiều mạch/seed training.
- Đơn vị dữ liệu là instance; seed là lần lặp trong instance. Sáu test chỉ hỗ trợ
  case study, không suy ra độ khó tổng thể từ30 lượt hoặc CI theo shots.

## Bài toán và mô hình

Giữ CPU/RAM nguyên dương, mỗi task đúng một host, min_active_hosts=sum(y).
Hai bit/task:00→host0,10→host1,11→host2;01 bị từ chối, không sửa bit hay y.
x0=1-u,x1=u-v,x2=v; penalty domain=4*v*(1-u), capacity=4*residual².
Y/slack giữ nguyên. X mixer không bảo toàn miền hợp lệ. Với instance khả thi,
năng lượng feasible<=3, invalid/capacity violation nguyên>=4, nên ground QUBO
phải tương ứng placement tối ưu. Vô nghiệm giữ optimum/P_opt=null.

## Dữ liệu và đối chứng

Pool cơ sở có demand/capacity1..3, task/host multiset, optimum2 và nghiệm3host:
508 instance4task,82 instance5task; uniform encoded batch1024 informative0.2..0.7
có146/47. Generator phải tự tái lập các số này. Đây là miền có điều kiện,
không phải toàn pool q<=25: capacity4 vẫn có thể thỏa khi các capacity khác nhỏ.
Split dự kiến2 dev,6 test (3 mỗi kích thước),2 functional controls; chọn theo
thuộc tính/exact counts, trước QAOA. Loại trùng permutation và CPU/RAM swap.
Lưu snapshot test trong cùng manifest; Notebook19 chỉ chạy dev/controls.

Controls: uniform bit domain-wall+y (slack marginal), random host assignment
với y inferred, và exact enumeration solver đo trong phiên hiện tại. Tất cả
cùng input hash; exact reference không được truyền đáp án vào training.
FF/BFD/MILP chưa triển khai trong gói pilot A; không gọi đây là hoàn tất nhánh B.

## Ngân sách

Domain-wall+y+slack<=25q. Statevector16*2^q bytes không phải whole RSS.
Windows chạy tuần tự, start available>=8GiB, reserve>=4GiB, processRSS<=4GiB,
Aer2048MiB/4threads, không tự nâng guard. Boundary guards không ngắt native call.
Notebook19:6 dev probes,12 dev training runs,2 functional smokes ngoài test.
Mean/max_abs,COBYLA cap200,train/final1024shots,final seed riêng,p1/2/3.
Pilot time guard2400s/lượt để chẩn đoán, không là cam kết campaign budget.
Sau pilot mới khóa90 test runs và budget toàn quá trình đề xuất6h trong study mới.
Không đủ RAM/cost→blocked hoặc scope phiên bản4task riêng trước test.

## Nghiệm thu

Mô hình, oracle và decoding đúng; đủ pilot hoặc status thiếu rõ; source/input/
config/raw samples được audit; giữ zero-feasibility và failed attempts.
Có thể hoàn tất pilot với chất lượng thấp; không tự tuning để cứu kết quả.
Notebook20 và campaign test chưa được khởi chạy bởi Notebook19.

Nguồn: https://arxiv.org/abs/1903.05068 ;
https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html .
