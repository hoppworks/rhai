# Combined independent review — PASS

Standards: PASS. Spec/acceptance: PASS only for four named setup selectors across
base, sync, unchecked and sync+unchecked profiles on native Darwin arm64/macOS
27.0.1, Rust/Cargo1.77.2 (sixteen GREEN rows), plus four base-profile assertion REDs.

The complete evidence manifest verifies. Candidate source is integrated revision
7638f2684ff2f06bb7587359eeb8c82e9c86a360. Restored Unix source, Cargo.toml and
canonical lock hashes match the original receipts. There is no product/test diff.

The mutation patch changes only each named test's final marker-absence assertion.
Each RED exits 101 with its intended assertion message and exactly one failed
test, after helper cleanup, public run setup error, absent marker and retired
reservation. The source restoration hash is the expected 2eee89d2…; all sixteen
selector/profile GREEN statuses are 0 and cover public run and spawn. Native base
assertion sensitivity transfers at unchanged selector/assertion/OS/compiler/lock
scope to the other three profiles; no fresh profile-specific RED is claimed.

The retained Python observer ran after runner exit, confirms all 36 recorded
RED/GREEN child PID and group identities absent, accepts only ESRCH, confirms the
exact session scope empty and retires it. Scoped runner status is 0. The earlier
accepted Darwin Rust1.93 kernel-denial packet is untouched. The reviewer made no
edits and ran no builds/tests.

Current central rules: d6024420 plus applicable uncommitted core/skill changes;
project AGENTS SHA37f95ff6… remains unchanged. Other X36 OS/profile/MSRV rows,
Windows custody, Ticket03 and the full A–F acceptance remain open.
