# Mã hóa domain-wall ba host

Mỗi task dùng hai bit u,v. Miền hợp lệ u>=v có00,10,11 tương ứng host0,1,2.
Indicator x=(1-u,u-v,v). Ngoài miền,01 cho x=(1,-1,1): decoder từ chối domain,
không coi -1 là lượng tài nguyên âm hợp lệ và không repair bit/y.

Đặt E=sum(y)+4*sum(v*(1-u))+4*sum((usage+s-C*y)^2). Usage tuyến tính trong u,v;
biểu thức là đa thức bậc2 nên QUBO/Ising không cần ancilla bổ sung.

Mô hình được dựng bằng affine substitution của QUBO one-hot đã kiểm chứng,
và thêm domain penalty. Assignment penalty cũ bằng0 đại số vì tổng ba indicators
bằng1 kể cả trên miền không hợp lệ. Domain penalty là phần bắt buộc bù lại.
Capacity slack dùng cùng bounded binary weights và có thể có nhiều encoding.
Generic report giữ trường penalties.assignment=4 của mô hình one-hot cha;
assignment term đó triệt tiêu khi substitution. Domain penalty thực tế=4 được
ghi trong certificate domain_and_capacity_penalty và công thức/mã nguồn mới.

## Chứng nhận ground state

Với CPU/RAM/capacity nguyên dương, residual và domain violation đều nguyên.
Nếu có bất kỳ domain violation hay capacity equality violation, E>=4 vì các
penalties không âm và sum(y)>=0. Mọi placement khả thi có cách chọn slack trong
0..C để đạt E=sum(y)<=3. Vì vậy ground QUBO không thể vi phạm; trên miền hợp lệ
ground tương ứng min_active_hosts. Khi input vô nghiệm, mệnh đề có nghiệm feasible
không áp dụng; ground QUBO vẫn tồn tại nhưng optimum/P_opt placement lànull.

## Kiểm chứng thực thi

- Complete degree2 basis: zero, từngbit1, từngcặpbit1. So độc lập formula,
  QUBO mới và QUBO cũ affine+domain penalty.
- Duyệt3^n assignments dùng validator gốc để lấy optimum/histogram.
- Duyệt2^(2n+3)base bits và tối ưu slack theo clip(-residual,0,C).
  Clip upperC là bắt buộc khi miền invalid làm usage âm. Tính multiplicity của
  mọi slack encoding để kiểm chứng ground-state probability.
- Instance tiny duyệt toàn2^qbits: energy/Ising, decoded quality, uniform và
  ground/conditional mean phải trùng kết quả duyệt độc lập.

Uniform encoded dựa trên bit u/v/y; slack marginal vì decoded placement không
phụ thuộc slack. Random placement dựa trên3^n choices và y inferred. Ví dụ6
optimal assignments,n5: encoded q=6/(4^5*8),random q=6/3^5; không đánh đồng.
Batch success controls=1-(1-q)^1024. Required lift=(1-(1-s)^(1/1024))/q;
đây là diagnostic theo instance, không phải cam kết outcome.

Với sáu capacities3,slack12bits: q=2n+3+12 (n4→23,n5→25).
Capacity>3 vẫn có thể thỏa q<=25 nếu các capacity khác nhỏ. Test regression
[(4,3),(2,3),(1,1)]n5 có24qubit và optimum2.

Domain-wall chỉ giảm register, không bảo toàn feasibility khi dùng X mixer.
Không suy luận lift phải tăng/giảm từ giới hạn lý thuyết cho permutation encoding.
Tham khảo: https://arxiv.org/abs/1903.05068 .
