## Checklist hiện hành — chỉ nhánh A, protocol v1.1 (10/10/2026)

Checklist này có ưu tiên với các phần lịch sử bên dưới. B/C nằm ngoài yêu cầu
hiện tại và không phải điều kiện nghiệm thu A.

- [x] U1: giữ bốn JSON v1, khóa45 lượt và negative smoke riêng.
- [x] Tạo phụ lục/manifest/protocol v1.1: time guard QAOA2400 đồng đều, giữ v1.
- [x] U2: runner/campaign/notebook16, RAM/time guards, lưu/resume/lock và audit.
- [x] Kiểm chứng87 tests,9 probe Linux và một lượt p3 reference/cap200/1024shots.
- [x] Kiểm tra cell notebook và đường export partial bằng Python không UI.
- [x] Hướng dẫn Windows, phiên chạy từng instance, snapshot và ZIP kết quả.
- [ ] Khiêm chạy tests và probe tài nguyên Windows trong nt409-khiem.
- [ ] U3: đủ45 lượt chính thức completed + negative-control riêng trên Windows.
- [ ] Review ZIP nguồn và notebook executed; giữ đầy đủ failure/interruption/0nghiệm.
- [ ] U4: chốt bảng/kết luận/giới hạn và đóng phần A, không mở sweep ngoài thiết kế.

**English:** Software delivered for branch A only; formal Windows execution
and final evidence review remain open. Historical checklists are retained for
traceability, not additional blockers for this A campaign.

---

> **English version below.**

## Lưu trữ — checklist benchmark v1 trước yêu cầu chỉ làm A

Thay checklist RAM/35 lượt trước đó theo yêu cầu thống nhất mọi phương pháp. Tài liệu chuẩn: docs/unified_benchmark_v1.md; công việc lịch sử bên dưới giữ để truy vết.

- [x] U1: chốt bộ choice/tight/reference và negative-control infeasible, giữ nguyên JSON gốc.
- [x] Đếm qubit/kiểm tra optimum và tạo manifest SHA256 canonical cùng protocol v1.
- [x] Chốt ma trận 45 lượt sampled mean p1/p2/p3; bỏ mở rộng 5 task/8/4 khỏi nghiệm thu hiện tại.
- [ ] A/B/C nhận cùng manifest/protocol; ghi nhận điều chỉnh proposal với nhóm/GV khi cần. Chưa gửi tin nhắn hoặc xác nhận thay người khác.
- [ ] U2: triển khai runner/notebook chung, input/protocol hashes, resource stop, start-state và resume tests.
- [ ] Checkpoint: probe p3/RAM trên máy Khiêm đạt trước campaign; không đổi thiết kế sau xem chất lượng.
- [ ] U3: 45 trạng thái QAOA và ba baseline trên cùng 3 instance; kiểm tra vô nghiệm riêng.
- [ ] Audit nguồn/counts/validator/timing; giữ lượt không tìm được nghiệm hoặc bị dừng.
- [ ] U4: tổng hợp bảng cuối, tách lịch sử/exact/CVaR và mode/best-valid, ghi giới hạn.
- [ ] Đóng gói tái lập và đóng Phase 4 theo phạm vi benchmark v1.

**English update:** This checklist supersedes prior open scope-expansion tasks. Inputs and protocol are frozen; implementation, formal execution, baseline verification and final handoff remain pending.

---

# Công việc nhánh A

## Các mốc đã thực hiện

- [x] Chuẩn bị và kiểm tra notebook 06.
- [x] Review 12 lượt Windows tight/choice và 6 lượt reference của A1.
- [x] Ghi nhận A1 bằng tài liệu/PDF chỉ tiếng Việt.
- [ ] A gửi C hai chỉ mục A1 và toàn bộ 18 báo cáo nguồn mới; chưa có xác nhận.
- [x] Chuẩn bị notebook 07, chẩn đoán và hướng dẫn khảo sát P chung.
- [x] Kiểm thử 11 bài kiểm tra và 24 lượt Aer rút gọn trước khi bàn giao notebook 07.
- [x] A chạy đủ 60 lượt P chung trên tight/choice; đã kiểm tra toàn bộ mẫu thô.
- [x] A chạy đủ 30 lượt P chung trên reference; đã kiểm tra mẫu thô, manifest và notebook.
- [x] Đối chiếu các đối chứng P=3 với A1; không tính thành lần lặp độc lập mới.
- [x] Review cả ma trận P chung và lập kế hoạch penalty độc lập/độ sâu.
- [ ] A gửi C hai campaign P chung, đủ 90 báo cáo nguồn và kết luận review; chưa có xác nhận.

## Đợt tiếp theo, theo thứ tự phụ thuộc

- [x] Task 1: triển khai mô hình hai penalty; kiểm tra hồi quy P chung, công thức/QUBO/Ising và nghiệm tham chiếu.
- [x] Task 2: hỗ trợ hai penalty trong báo cáo/chẩn đoán/run key/resume; kiểm tra bằng lượt Aer ngắn.
- [x] Checkpoint: 23 kiểm tra tự động đạt; mô hình và báo cáo đúng trước khi chạy pilot dài.
- [x] Task 3, chuẩn bị: notebook 08 và hướng dẫn song ngữ; 24 tổ hợp chạy rút gọn trên Linux, resume không chạy lại; thêm 4 lượt tight/vô nghiệm và đối chiếu 3 báo cáo Windows cũ.
- [x] Task 3, thực nghiệm A: chạy/review 24 lượt choice/reference mặc định (6 cặp, 2 khởi tạo, seed 42); toàn bộ mẫu đo/manifest/bảng khớp.
- [x] Chọn một ứng viên (3,12); cố định khởi tạo/đối chứng theo từng instance trước khi xem seed mới.
- [x] Chuẩn bị notebook 09 và hướng dẫn; kiểm thử 20 lượt Aer rút gọn, bảng năm seed, metadata và resume.
- [x] A chạy/review notebook 09 trên Windows: choice 10 lượt, reference 10 lượt, seed 45–49; đủ 20.480 shots, manifest/bảng khớp.
- [x] Checkpoint: đóng ma trận penalty hiện tại; (3,12) có tín hiệu hạn chế ở choice và kém (1,1) ở reference.
- [x] Chuẩn bị notebook 10: (3,3) chung, p=1, ba cấu hình thang/khởi tạo, seed 50–54; chấm năng lượng QUBO gốc.
- [x] Kiểm chứng 34 bài kiểm tra và 30 lượt Aer Linux rút gọn, bảng ghép seed, lưu/resume và kiểm tra instance.
- [x] A chạy/review notebook10 Windows: 30 lượt/30.720 shots, seed50–54; toàn bộ mẫu và bảng khớp.
- [x] Chốt protocol độ sâu dùng chuẩn hóa và khởi tạo chung; chưa có cải thiện đồng thời trên choice/reference.
- [x] Chuẩn bị notebook11, depth module, kiểm tra và hướng dẫn song ngữ; 42 kiểm tra tự động và 20 lượt Aer Linux rút gọn đạt.
- [x] A chạy/review notebook11 Windows:20 lượt/20.480 shots, p1/p2, (3,3), seed55–59; mẫu/manifest/bảng khớp.
- [x] Review lại Phase0–11: đại số/scaling/bit nhất quán;20 replay lý tưởng, phép đo seed lặp và đối chứng exact có giới hạn.
- [x] Sửa runner: seed cuối tách training; thống kê năng lượng và lý do dừng số học thật của SciPy.
- [x] Chuẩn bị notebook12 và hướng dẫn song ngữ, oracle exact, ma trận6 sampled+2 exact mỗi input, manifest/resume riêng.
- [x] Kiểm chứng59 bài kiểm tra và16 lượt Aer Linux rút gọn trên20/23qubit; dữ liệu kiểm thử tách khỏi thực nghiệm Windows.
- [ ] A chạy/review notebook12 Windows: 8 lượt choice + 8 lượt reference, p1/P3/cap80, hai khởi tạo, batch cuối1024 shots bằng seed riêng.
- [ ] Đối chiếu E_train/E_eval/E_exact, lý do dừng, one-hot/P_opt/mode/thành công và chi phí; chọn một thay đổi tiếp theo từ bằng chứng.
- [ ] Task 4: đo thử rồi khảo sát p=1/2/3; dùng khởi tạo từ độ sâu trước theo đúng tên tham số.
- [ ] Khi tăng maxiter, có đối chứng p=1 cùng ngân sách; ghi riêng tác động độ sâu và tác động ngân sách.
- [ ] Xác nhận cấu hình được chọn bằng seed mới; báo cáo khả thi, tối ưu, tỷ lệ thành công, thời gian và RAM.
- [ ] Task 5: đối chiếu FF/BFD/MILP của B và chuyển số liệu cho C; công bố quy tắc chọn đầu ra.
- [ ] Checkpoint cuối: báo cáo kết quả có giới hạn rõ; không loại lượt hoàn tất có 0 nghiệm và không yêu cầu QAOA phải thắng MILP.

Chi tiết phạm vi, tiêu chí nghiệm thu và tệp dự kiến nằm trong tasks/plan.md. B/C tiếp tục phân công đã bàn giao; tình trạng baseline/phân tích chưa được xác nhận.

Mốc 07/10/2026: notebook11 đã review đủ20 lượt Windows; choice p1/p2 có12/8 mẫu tối ưu và5/5,4/5 lượt thành công, reference6/4 mẫu và3/5 lượt mỗi nhóm. Không có ground state; năng lượng giảm chưa đồng nghĩa tăng P_opt. Notebook12 đã triển khai/kiểm chứng phần mềm;8+8 lượt Windows mặc định đang chờ. Giữ riêng protocol và seed42,45–49,50–54,55–59,60–62. p3 và baseline chưa hoàn tất; B/C tiếp tục việc đã bàn giao.

---

# Branch A tasks

- [x] Prepare/verify notebook 06 and review all 18 A1 Windows trials.
- [x] Record A1 in a Vietnamese-only document/PDF.
- [ ] Confirm delivery of both A1 indexes and 18 reports to C.
- [x] Prepare notebook 07 and verify 11 tests plus 24 short Aer trials.
- [x] Review all 60 real tight/choice common-P trials.
- [x] Review all 30 real reference common-P trials, manifest and notebook.
- [x] Confirm P=3 controls reproduce A1 without counting them as new independent repetitions.
- [x] Assess the complete common-P matrix and plan independent-penalty/depth work.
- [ ] Confirm delivery of both common-P indexes, all 90 reports and review findings to C.
- [x] Task 1: independent-penalty model, common-P regression and formula/QUBO/Ising/exact-reference checks.
- [x] Task 2: weighted diagnostics, report provenance, run keys and safe resume, verified with short Aer runs.
- [x] Checkpoint: 23 automated tests pass; model and reports correct before the longer pilot.
- [x] Task 3 preparation: bilingual notebook/docs, 24 reduced-budget Linux Aer combinations, exact resume without reruns, four tight/infeasible boundary runs and three archived Windows reports.
- [x] Task 3 A's pilot: review all 24 default Windows trials and verify raw samples/manifest/tables.
- [x] Select one candidate (3,12), with fixed per-instance starts/controls before fresh-seed outcomes.
- [x] Prepare bilingual notebook 09/docs and verify twenty reduced-budget Aer trials, five-seed tables, study identity and resume.
- [x] Execute/review A's Windows confirmation: ten choice plus ten reference trials, seeds 45–49, all 20,480 shots/manifest/tables consistent.
- [x] Checkpoint: close the bounded grid; limited (3,12) signal on choice and worse results than (1,1) on reference.
- [x] Prepare notebook 10: shared (3,3), depth 1, three scale/start arms, seeds 50–54 and original-QUBO scoring.
- [x] Verify 34 automated tests and thirty reduced-budget Linux Aer trials, paired tables and persistence/resume guards.
- [x] Execute/review A's thirty Windows notebook10 trials and all 30,720 shots; sources/manifests/tables agree.
- [x] Fix normalized coordinates/shared initialization for the depth protocol without claiming joint improvement.
- [x] Prepare notebook11/depth module/tests/bilingual docs; 42 automated tests and twenty reduced-budget Linux Aer trials pass.
- [x] Execute/review all20 Windows notebook11 trials/20,480 shots; source reports/manifests/tables agree.
- [x] Review Phase0–11 model/scaling/bit consistency, twenty ideal replays, repeated-seed measurements and bounded exact controls.
- [x] Update the runner with independent final sampling, energy statistics and actual SciPy numerical termination metadata.
- [x] Prepare Notebook12/bilingual docs, exact oracle and separate six-sampled/two-exact design per input with verified resume.
- [x] Verify59 tests and16 reduced-budget20/23qubit Linux Aer trials, separate from Windows benchmark evidence.
- [ ] Execute/review Notebook12 Windows: 8 choice + 8 reference, p1/P3/cap80, two starts and 1024 independently seeded final shots.
- [ ] Assess training/independent/ideal energy, stopping, one-hot/P_opt/output rules and separate costs before changing another factor.
- [ ] Task 4: resource-probed p=1/2/3 study with named-parameter initialization and matched depth-1 controls for increased optimizer budgets.
- [ ] Validate selected settings on fresh seeds and record quality/success/runtime/memory.
- [ ] Task 5: compare with B's baselines and deliver evidence to C, disclosing the output selection rule.
- [ ] Final checkpoint: retain completed zero-feasibility trials and state limits; outperforming MILP is not required.

Acceptance criteria, dependencies and expected files are in tasks/plan.md. Teammates' completion and delivery of new reports remain unconfirmed.

Checkpoint 7 October 2026: Notebook11's20 Windows trials are fully reviewed. Choice p1/p2 has12/8 optimal shots and5/5,4/5 successes; reference6/4 shots and3/5 successes in each arm. No ground state is observed; lower energy does not establish improved P_opt. Notebook12 is software-verified;8+8 default Windows trials remain pending. Keep protocols/seeds42,45–49,50–54,55–59,60–62 separate. p3 and baseline comparison remain open; B/C continue their assigned work.
