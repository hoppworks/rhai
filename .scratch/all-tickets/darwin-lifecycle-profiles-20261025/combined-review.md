# Combined independent review — PASS

Standards: PASS. Spec/acceptance: PASS for only eleven new native Darwin
arm64/macOS27.0.1, Rust/Cargo1.77.2 selector/profile rows. No actionable findings.

All package hashes verify; source is integrated c0fc47e4. Current Cargo.toml,
canonical lock, Unix source and complete capture test-file hashes match the
original receipts. All eleven selectors report one passed test/status0; the
scoped runner returns0. The reviewer made no edits and ran no builds/tests.

The public kill cases record leader/worker/leaf absence, bounded wait and a live
unrelated sentinel. Final-drop cases record nonfinal liveness and final member
absence with sentinel survival. Capture cases record the escaped holder/sentinel
live after kill/cancel, leader reap, incomplete capture, Darwin EPIPE and exact
fixture cleanup. The separate retained observer checks 38 PIDs and ten explicitly
recorded kill/drop groups using signal0, accepts only ESRCH, and retires only the
exact empty owned scope. No capture-group readback is claimed.

Reused source controls are applicable: relevant kill/drop tests and support have
no source hunks since76fdebd7; Unix delta there is an unrelated internal unit-test
cfg. The complete current capture file matches its accepted native base source.
Existing X25 base/unchecked and X27 managed final-drop base controls have combined
PASS records; X38 base proof remains valid. The X27 base selector also covers this
named X37 host/sentinel subset. No fresh profile-specific RED or base rerun is
claimed; the historical pending header is superseded by the recorded acceptance.

Current central/project/skill hashes remain at the previously loaded d6024420
plus applicable local uncommitted rules. This package closes no whole ticket,
Windows custody or other platform/profile/MSRV rows.
