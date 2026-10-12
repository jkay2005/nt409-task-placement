# Notebook 14 — CVaR exact choice

Giải nén vào thư mục gốc nt409-task-placement (cùng cấp src/, tests/, notebooks/, docs/).
Xem docs/qaoa_cvar_comparison.md để đọc thiết kế và giải thích từng bước.

1. Chạy trong Conda nt409-khiem: python -m unittest discover -s tests
   Bộ hiện tại gồm 72 test; cần dòng kết luận OK.
2. Mở notebooks/14_qaoa_cvar_choice.ipynb; chọn kernel notebook 13; Restart Kernel.
3. Giữ ALPHA=0.1, RESUME_MANIFEST=None và đường dẫn baseline mặc định.
4. Chạy Bước 1–10. Thiết kế: 2 lượt CVaR mới, p1_choice 20 qubit,
   hai khởi tạo ban đầu, p=1, penalty (3,3), maxiter=200, 1024 shots cuối.
5. Save As: 14_qaoa_cvar_choice_executed.ipynb.
6. Gửi notebook có output và ZIP cvar_choice_<timestamp>.zip do Bước 10 tạo.

Gói thêm module/test CVaR, notebook và hướng dẫn; kèm lại test_depth_campaign.py
đã sửa UTF-8. Không thay các runner hiện có. Baseline là manifest và 2 report
notebook 13 Windows nguyên vẹn. Không cần chạy lại notebook 13.

CVaR và năng lượng trung bình là hai đại lượng khác nhau. Kiểm tra delta_P_opt_pp,
không kết luận placement tốt hơn chỉ vì CVaR giảm. success=False do MAXFUN là
một kết quả thí nghiệm cần giữ; khác với unittest FAILED.

verification/notebook14 chứa kiểm chứng Linux tách riêng: 72 test đạt;
10 code cells chạy tuần tự bằng Python với chuyển đổi display sang in bảng
(không phải một lượt Jupyter kernel); 2 lượt mặc định đầy đủ; resume không
chạy lại; CVaR cuối khớp cách tính phân vị độc lập và batch cuối tái lập đúng seed.
Không giải nén linux_cvar_reports.zip vào campaign Windows.
