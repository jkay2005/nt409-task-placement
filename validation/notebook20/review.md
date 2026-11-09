# Software validation — Notebook20 v1

This packet validates implementation, not scientific performance.

- Baseline source recovered from GitHub branch `backup/a-notebook18-20261012`, commit `dae62dc5ba49decec2bd23890d7d36ee753beaae`, plus the released Notebook19 packet. All19 inherited source hashes match the Windows19 campaign modulo LF/CRLF.
- Baseline119tests passed before the change. Full final suite:128tests,34.690s,OK; no skipped tests. New tests exercise fixed balanced90row plan, active/idle/crash budget, clipping without changing planned quality config, resume without completed reruns, semantic tamper after checksum update, interruption recovery, exhausted-budget partial export, preflight gate, pre-C2 frozen-protocol gate, and completed-zero versus missing summaries.
- Real Windows19 archive audited again using restored sources:14 completed trial reports,8passed probe groups, checksums and semantic raw counts. No quantum rerun of Windows19.
- Notebook structure validated with nbformat; all9codecells executed sequentially through IPython. Native Jupyter kernel startup was attempted with TCP then IPC; the execution sandbox does not permit the required sockets. VSCode/Jupyter kernel startup is therefore not verified here. The product notebook does not require a special execution workaround on Windows.
- For notebook software execution, all6test IDs retained but inputs were replaced with identical1task/11qubit fixtures,32shots/cap8,1Aer thread. The external C2-to-context boundary was substituted after separately validating the real C2 archive. This allows testing the pipeline without consuming the official test study. The modified validation notebook and context clearly label this substitution.
- All90fixture trial slots completed and18fixture probes passed; all9cells completed without error. Wall time35.506s; metered charged35.336s. These times do not forecast full-shot Windows20 performance.
- Final result ZIP has unique members, a complete SHA256 manifest, and campaign/summary bytes equal the closed state on disk. All budget sessions closed. Raw reports,21source modules and frozen fixture context are retained for auditing.
- Six-panel plot was inspected: titles/axes/baselines/legend visible, seed coverage shown. Identical fixture curves across original IDs are expected and carry no size/instance-quality interpretation. The plotted controls are for the substituted fixture, not the official dataset.
- Historical source modules are unchanged. No dependencies were added to product requirements. Only new test-campaign modules/protocol/notebook/docs were shipped. Git commits are local; no push/merge was performed.

Remaining verification: user executes Notebook20 with the official unchanged inputs,1024training/finalshots,cap200,6-hour cumulative budget, original Windows kernel; then uploads the cell9 ZIP and saved notebook. Formal test performance and Phase4 closure remain pending.
