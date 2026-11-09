> **English version below.**

# Phase 1 — Đặc tả bài toán xếp đặt tác vụ v1

## Mục tiêu

Đặt mọi task lên host và tối thiểu hóa số host được bật.

## Dữ liệu đầu vào

- Mỗi task có ID, nhu cầu CPU và nhu cầu RAM.
- Mỗi host có ID, dung lượng CPU và dung lượng RAM.
- Nhu cầu và dung lượng CPU/RAM là các số nguyên dương.
- Nhu cầu và dung lượng dùng cùng đơn vị đối với từng tài nguyên.
- ID task không trùng nhau; ID host không trùng nhau.
- Thứ tự trong danh sách xác định chỉ số task và host.

## Biến quyết định

- `x[i,h] = 1` nếu task `i` được đặt trên host `h`; ngược lại bằng 0.
- `y[h] = 1` nếu host `h` được bật; ngược lại bằng 0.
- Mọi biến quyết định đều là biến nhị phân.

## Hàm mục tiêu

Tối thiểu hóa `sum_h y[h]`.

## Ràng buộc

Với mỗi task `i`:

```text
sum_h x[i,h] = 1
```

Với mỗi host `h`:

```text
sum_i cpu[i] * x[i,h] <= cpu_capacity[h] * y[h]
sum_i ram[i] * x[i,h] <= ram_capacity[h] * y[h]
```

Phương trình thứ nhất bắt buộc mỗi task nằm nguyên vẹn trên đúng một host. Hai
bất đẳng thức tiếp theo giới hạn tổng CPU và RAM của các task trên từng host;
host không bật (`y[h] = 0`) không được nhận task.

## Quy ước đánh giá

- Một placement chứa đúng một chỉ số host cho mỗi task.
- Khi đánh giá placement, chỉ bật các host thực sự có task.
- Khi đánh giá `x,y` tường minh, giữ nguyên vector `y` được cung cấp.
- Phương án không hợp lệ có `objective = None`.

---

# Phase 1 — Task placement problem specification v1

## Objective

Minimize the number of activated hosts while placing every task.

## Input

- Each task has an ID, CPU demand and RAM demand.
- Each host has an ID, CPU capacity and RAM capacity.
- CPU and RAM values are positive integers.
- Demand and capacity use the same unit for each resource.
- Task IDs are unique; host IDs are unique.
- List order determines task and host indices.

## Decision variables

- x[i,h] = 1 if task i is assigned to host h; otherwise 0.
- y[h] = 1 if host h is activated; otherwise 0.
- All decision variables are binary.

## Objective function

Minimize sum_h y[h].

## Constraints

For every task i:

```text
sum_h x[i,h] = 1
```

For every host h:

```text
sum_i cpu[i] * x[i,h] <= cpu_capacity[h] * y[h]
sum_i ram[i] * x[i,h] <= ram_capacity[h] * y[h]
```

The first equation assigns each task in full to exactly one host. The two
inequalities limit the total CPU and RAM demands on each host; an inactive
host (`y[h] = 0`) cannot receive a task.

## Evaluation conventions

- A placement contains one host index per task.
- When evaluating a placement, activate exactly its occupied hosts.
- When evaluating explicit x,y, preserve the supplied activation vector.
- An infeasible result has objective = None.
