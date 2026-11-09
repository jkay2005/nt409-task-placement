# Notebook 21 — Nhánh B v1.1 (sửa cài đặt Python 3.14)

Cập nhật 22/10/2026. Bộ thuật toán: First-Fit, BFD, MILP. Bản này khóa OR-Tools **9.15.6755**, có gói Windows x64 cho Python 3.14. Xem `B21_INSTALL_FIX.md` để hiểu nguyên nhân và cách cập nhật từ v1.

Gói dùng cùng dữ liệu/handoff A trên backup `backup/a-phase4-20261013` (d88b0af). Đây là gói mã/tài liệu; notebook chưa chạy và không kèm bảng kết quả, ảnh kết quả hay thư mục QA Linux.

1. Đóng Notebook 21 hoặc lưu một bản riêng nếu bạn đã ghi chú vào notebook.
2. Giải nén NỘI DUNG ZIP vào gốc `nt409-task-placement`, chấp nhận thay thế các file B trùng tên. Giữ cấu trúc src/tests/data/notebooks/docs. Không chỉ chép mỗi requirements.
3. Chạy trong terminal ở gốc repo:

```bat
conda activate nt409-khiem
python --version
python -c "import sys; print(sys.executable)"
python -m pip install -r requirements-branch-b.txt
python -c "import ortools; from ortools.linear_solver import pywraplp; print(ortools.__version__); print(pywraplp.Solver.CreateSolver('SCIP').SolverVersion())"
python -m unittest discover -s tests
```

Version OR-Tools cần in ra `9.15.6755`. Đường dẫn Python cần nằm trong environment `nt409-khiem`. Dòng thông báo pip có phiên bản mới không phải nguyên nhân lỗi không tìm thấy OR-Tools cũ.

4. Restart kernel trong VS Code, chọn Python của nt409-khiem, mở `notebooks/21_classical_baselines_b.ipynb`, Run All.
5. Giữ máy thức khi đo, ghi MACHINE_LABEL/TIMING_NOTE phù hợp, lưu notebook bằng Ctrl+S.
6. Kết quả do bạn chạy nằm trong `data/reference_results/phase4m_classical_b/`; gửi ZIP campaign mới và notebook đã lưu để kiểm tra.

Tài liệu: `docs/branch_b_notebook21_vi.md` và `docs/branch_b_json_explained_vi.md`.

Protocol hiện hành là `data/benchmarks/nt409_classical_b_v1_1/protocol.json`; file v1 giữ nguyên để mô tả phiên bản lịch sử. Không trộn timing từ hai phiên bản solver. Bộ dữ liệu, thuật toán, số luồng, ngân sách và số lượt đo vẫn như kế hoạch ban đầu.

Gói chưa được push lên GitHub. Nếu đã giải nén v1 trước đó, các file QA Linux cũ không bị ZIP này tự xóa; Notebook 21 không cần chúng để chạy.
