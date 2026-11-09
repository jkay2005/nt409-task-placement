# Notebook 29 — T5: đối chứng cổ điển trên bốn input 5 task × 3 host

N27 đã hoàn tất development; N28 đã hoàn tất ba case validation. Bước tiếp theo là bổ sung First Fit, BFD và MILP, rồi đặt cạnh các kết quả QAOA p=2 đã có. Mọi input vẫn là **5 task × 3 host**. Không tạo/chọn lại dữ liệu, đổi penalty, tăng p hoặc chạy lại optimizer lượng tử trong bước này.

## 1. Notebook trả lời câu hỏi gì?

1. First Fit/BFD tìm được nghiệm hợp lệ không, dùng bao nhiêu host?
2. MILP tìm được nghiệm nào và có chứng minh tối ưu không?
3. Khi đặt cạnh các đối chứng này, kết quả QAOA nên được diễn giải như thế nào?

| Input cố định | Vai trò | Assignment khả thi / 243 | Assignment tối ưu | Optimum từ vét cạn |
|---|---|---:|---:|---:|
| a3_dev_n5 | Development | 90 | 8 | 2 host |
| v5x3_1 | Validation 1 | 78 | 4 | 2 host |
| v5x3_2 | Validation 2 | 1 | 1 | 3 host |
| v5x3_3 | Validation 3 | 14 | 14 | 3 host |

Đây là đáp án tham chiếu đã biết từ bộ dữ liệu đóng băng. Solver chỉ nhận input task/host, không nhận optimum, assignment tối ưu hoặc warm start từ vét cạn. Oracle được dùng để kiểm tra kết quả sau khi giải.

## 2. Đặt các file vào repo hiện tại

Giải nén `nt409_notebook29_classical5x3_v1.zip` vào thư mục gốc repo đã chạy N28, nơi có `src/`, `experiments/`, `notebooks/`, `data/`. Ghép thư mục trùng tên. Gói chỉ thêm runner N29, test, notebook, dependency bổ sung và tài liệu; không sửa `src/`, N27 hoặc N28.

Trong PowerShell tại thư mục gốc repo, có thể dùng:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\nt409_notebook29_classical5x3_v1.zip" -DestinationPath .
```

Giữ nguyên hai con trỏ và các thư mục mà chúng trỏ tới:

- `data/reference_results/phase5_domainwall_training/N27_ACTIVE.json`
- `data/reference_results/phase5_domainwall_validation/N28_ACTIVE.json`

N29 đọc raw JSON và kiểm tra SHA256 của cả hai lượt chạy. Chỉ có ZIP nằm trong Downloads chưa đủ. Nếu đã di chuyển thư mục kết quả, khôi phục đúng vị trí cũ theo con trỏ; không tạo lượt chạy N27/N28 mới.

## 3. Kiểm tra môi trường trước khi cài thêm

Mở `notebooks/29_classical_baselines_validation.ipynb`, chọn kernel **nt409-khiem**, restart kernel rồi chạy ô mã 1. Ô này chỉ kiểm tra; không tự cài package và không giải bài toán.

Nếu ô 1 thành công, chuyển sang ô 2. Nếu báo thiếu OR-Tools/dependency, tại Terminal PowerShell ở gốc repo chạy:

```powershell
conda activate nt409-khiem
python -c "import sys; print(sys.executable); print(sys.version)"
python -m pip install --no-deps -r requirements-n29.txt
```

Sau đó **restart kernel** và chạy lại ô 1. Đường dẫn `sys.executable` ở terminal phải thuộc cùng môi trường với đường dẫn notebook in ra. Nếu không trùng, sửa lựa chọn môi trường trước khi cài.

Gói solver được khóa `ortools==9.15.6755`, backend SCIP, một thread. OR-Tools yêu cầu numpy ≥2.0.2 và pandas ≥2.0; môi trường hiện tại được kiểm tra trực tiếp. `--no-deps` giúp tránh pip tự nâng cấp numpy/pandas/Qiskit. File bổ sung vẫn liệt kê các dependency solver còn lại để pip cài khi thiếu. Không dùng `pip install -U`, không cài lại toàn bộ `requirements-lock.txt`. Nếu preflight báo dependency không tương thích, gửi nguyên lỗi trước khi thay đổi môi trường tiếp.

## 4. Chạy lần lượt 10 ô mã

| Ô | Công việc | Kết quả cần xem |
|---:|---|---|
| 1 | Tìm repo, kiểm tra Python/package/SCIP | Có solver SCIP, threads=1 |
| 2 | Kiểm tra N27/N28, mở một campaign N29, chụp nguồn/input/runtime | 4 case; N27 có 6 stage, N28 có 18 stage; 12 hàng QAOA p2 |
| 3 | Development a3_dev_n5: FirstFit → BFD → MILP | 3 kết quả và ZIP checkpoint |
| 4 | Validation v5x3_1 | 3 kết quả và ZIP checkpoint |
| 5 | Validation v5x3_2 | Heuristic có thể không tìm được nghiệm; vẫn tiếp tục MILP |
| 6 | Validation v5x3_3 | Đủ 4 case |
| 7 | Tổng hợp chất lượng nghiệm cổ điển | 12 hàng; objective, bound, gap và chứng nhận |
| 8 | Đọc xác suất QAOA cũ và hai đối chứng ngẫu nhiên | Bảng 20 hàng và biểu đồ 4 ô |
| 9 | Tổng hợp chi phí thực thi đã ghi nhận | Hai bảng riêng cho classical và QAOA |
| 10 | Xuất kết quả cuối | ZIP `t5_...zip`, summary, CSV, hình và đường dẫn con trỏ |

Mỗi cặp algorithm–case chỉ có **một lần giải**, tổng cộng 12 lần: 8 heuristic và 4 MILP. Mỗi MILP có giới hạn 600 giây; đây là giới hạn, không phải thời gian phải chờ đủ. N29 không chạy statevector 25 qubit. Chi phí chuẩn bị tham chiếu, kiểm chứng và xuất file không được nhập vào `solve_seconds`.

Được nghỉ sau khi một ô case hoàn tất. Mở lại notebook sẽ dùng `N29_ACTIVE.json`: case đã xong được bỏ qua, không giải lại. Giữ nguyên input, source và runtime trong một campaign.

Nếu một ô bị lỗi/ngắt, giữ nguyên thư mục và gửi lỗi cùng ZIP checkpoint đã xuất. Không xóa con trỏ, raw JSON hay `RUNNING.lock` để ép chạy tiếp. Trường hợp máy tắt đột ngột có thể giữ lock; cần kiểm tra lần chạy đó trước khi tiếp tục. Không tự tạo thêm lượt rồi chỉ chọn lượt đẹp hơn.

## 5. Lý thuyết: MILP đang giải bài toán nào?

Đặt x[i,h] ∈ {0,1}: task i được đặt lên host h; y[h] ∈ {0,1}: host h được bật.

```text
Minimize:  y[0] + y[1] + y[2]
For each task i:  sum_h x[i,h] = 1
For each host h:  sum_i cpu[i] x[i,h] <= CPU[h] y[h]
For each host h:  sum_i ram[i] x[i,h] <= RAM[h] y[h]
```

Có 15 biến x và 3 biến y, tổng **18 biến nhị phân**. Mỗi task phải nằm trên đúng một host; tổng CPU/RAM trên một host không vượt khả năng của host đó. Vì các task có nhu cầu dương, y=0 buộc host không chứa task.

MILP biểu diễn trực tiếp ràng buộc này. Mô hình QAOA đang dùng 25 qubit vì có mã domain-wall, bit y và slack để đưa ràng buộc vào QUBO. **18 biến MILP và 25 qubit vẫn biểu diễn cùng bài toán 5 task × 3 host**, không phải thay đổi kích thước thí nghiệm.

First Fit xét task theo thứ tự input và chọn host đầu tiên còn đủ CPU/RAM. BFD của đồ án sắp task giảm dần theo nhu cầu lớn nhất sau chuẩn hóa, ưu tiên host đã mở còn đủ chỗ rồi chọn phần dung lượng dư chuẩn hóa nhỏ nhất; hòa thì dùng thứ tự host. Cả hai là quy tắc tham lam, không có chứng nhận tối ưu.

Ví dụ MILP tìm nghiệm 2 host: nghiệm đó cho ta một cận trên UB=2. Nếu solver chứng minh mọi nghiệm phải dùng ít nhất 2 host, cận dưới LB=2; hai cận gặp nhau nên tối ưu được chứng minh. Nếu LB vẫn là 1, chỉ biết có nghiệm 2 host, chưa có chứng nhận từ solver dù vét cạn cũng cho optimum=2.

Gap được ghi là `(objective - bound) / max(1, abs(objective))`, chặn sai số âm rất nhỏ về 0. Đây là gap từ nghiệm và cận của **bài toán số host**, không phải mean QUBO energy hay P_opt.

## 6. Cách đọc kết quả

| Trường | Cách hiểu |
|---|---|
| `status=optimal` | MILP báo tối ưu, được kiểm tra cùng bound/gap |
| `status=feasible_not_proven` | Có nghiệm hợp lệ; solver chưa chứng minh tối ưu |
| `status=no_placement_found` | Heuristic không tìm được cách đặt theo quy tắc của nó |
| `found_valid` | Nghiệm x/y thỏa các ràng buộc gốc, không sửa nghiệm để chấm |
| `objective` | Số host bật; càng ít càng tốt khi nghiệm hợp lệ |
| `oracle_objective_gap` | Số host dư so với vét cạn; 0 là trùng optimum |
| `matches_oracle` | Nghiệm đạt optimum đã biết; riêng cột này không phải chứng nhận của solver |
| `solver_certified_optimal` | Có chứng nhận tối ưu của MILP, tách khỏi việc trùng oracle |
| `solver_bound` | Cận dưới do MILP cung cấp |
| `solver_gap` | Khoảng cách tương đối giữa objective và bound |

Case v5x3_2 có đúng một assignment khả thi. First Fit/BFD không tìm được nó không có nghĩa input vô nghiệm. Một solver báo infeasible trên input đã được vét cạn chứng minh khả thi sẽ bị N29 đánh dấu lỗi để kiểm tra.

Bảng QAOA giữ nguyên p2 của N27/N28 và các xác suất P_domain, P_valid, P_opt, P_ground. Không thay một lần giải classical bằng xác suất 100%. Không dùng mean QUBO energy để so trực tiếp với số host classical.

Biểu đồ chỉ so **P_opt** của ba nhánh QAOA với hai đối chứng: uniform_encoded lấy đều bitstring mã hóa; random_host_inferred_y lấy đều một trong 243 assignment host rồi suy ra y. Đối chứng thứ hai có bước suy ra y, phải nêu rõ khi trình bày. Bốn ô có thang trục đứng riêng; so độ cao cột trong cùng một ô.

Đây là một development và ba validation tổng hợp có điều kiện. Không coi 12 lượt classical là 12 input độc lập. Thời gian mỗi thuật toán chỉ đo một lượt/case, QAOA có quy trình và overhead khác; chỉ mô tả chi phí, chưa kết luận lợi thế tốc độ từ các bảng này.

## 7. Xuất và gửi lại

Sau ô 10, bấm Ctrl+S lưu notebook có output, rồi gửi:

1. `29_classical_baselines_validation.ipynb` đã chạy và lưu.
2. ZIP kết quả `data/reference_results/phase5_classical_validation/t5_<timestamp>.zip`.
3. `data/reference_results/phase5_classical_validation/N29_ACTIVE.json`.

ZIP cài đặt `nt409_notebook29_classical5x3_v1.zip` chứa mã/hướng dẫn. ZIP `t5_...zip` do notebook tạo chứa bằng chứng chạy của bạn; đây mới là ZIP cần gửi để đánh giá.

ZIP kết quả gồm raw từng case, model MILP `.lp`, source/input/runtime, bản sao bằng chứng N27/N28, summary JSON, ba CSV, hình và manifest SHA256. N29 không sửa lượt N27/N28 gốc.

T5 chỉ được chốt sau khi kết quả trên máy bạn được kiểm tra. Tiếp theo theo kế hoạch tháng là T6: phân tích độ vững và giới hạn; rồi khóa phiên bản, tái lập/demo và bàn giao. Chưa tăng số task/host hoặc mở thêm nhánh thuật toán vì kết quả hiện tại chưa thắng classical.

## Tài liệu chính thức

- OR-Tools 9.15.6755: https://pypi.org/project/ortools/9.15.6755/
- Trạng thái solver: https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Solver.html
- BestBound: https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Objective.html
