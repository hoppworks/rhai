# File streaming read acceptance review

Accepted source7131f25337bc4830b225f842af0f1cbf6e42ddb2 on task/file-reads.
OCR deterministic commit preview selected three files; all three reviewed,
zero skipped. Checked arithmetic, shared cursor, allocation errors, strict UTF-8,
negative rejection before cursor access, host cap under unchecked and cfg omission.
No material source findings. Additive max_file_read default8MiB; zero host cap returns
empty. Positive reads issue one capped OS read; omitted/zero + unlimited Engine
uses capped read_to_end, matching retained pinned compatibility facts. Whole-file
APIs stay unchanged. UTF-8 errors consume the actual bytes and are catchable.

Real Engine + private OS files + independent readback prove shared cursor, actual
short reads/EOF, invalid lengths, INT::MAX, host/Engine caps, malformed/split UTF-8,
write-only errors and exact blob bytes. Full sys_fs base34, sync/no_index24,
unchecked32 pass. Final blob negative/EOF assertion changes pass affected tests
in all applicable profiles; unchanged full-suite evidence applies. Meaningful RED
is missing read_string registration; deliberate wrong payload control compares
actual abc to wrong expectation and fails at that assertion.

Proof and scripts retained at /Users/hoppworks/projects/rhai-file-reads/.scratch/file-reads/.
Original12:51:28–13:51:28UTC allowance and all ten launches preserved. Setup errors,
one zero-prefill correction and portable error-class correction remain recorded.
Coordinator independently checked exact logged runtimes agent-build-_1qfzah0,
agent-build-87yr753w and agent-build-b0d3b2m_ absent under the recorded temp parent.
Two-job setting and serial tests explicit in scripts. Peak storage and exact
fixture-count cap compliance were not measured and remain unverified. Native
macOS behavior only; release/MSRV/other platform gates remain open. Retain owned
worktree for required untracked proof; no redundant evidence copies.
