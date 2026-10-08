# Accepted Darwin integer-only process example rows

Accepted on 2026-10-08 after independent combined review and final export/cleanup.
Scope: X23 `sys,no_float` and `sys,sync,no_float`, native Darwin arm64,
macOS 27.0.1 (26A434), Rust/Cargo 1.77.2. Other native/features and the overall
A–F/release package remain open. No test or build was repeated for finalization.

Source revision: `ef423a516617e128835d54af16d75f559b2b1bce` plus only the owned
example patch. Input/recipe/source hashes: `inputs.json`, `recipe.sha256`,
`finalization-readback.json`; exact artifact/cwd/argv/status in original command
JSON and build logs. Pinned lock SHA-256:
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

The example chooses `child.wait(0)` for no_float at all three pending/terminal/
cleanup sites, retaining `child.wait(0.0)` otherwise. Both affected profiles built
with --locked in their owned source cwd. Each same-profile executable ran twice:
wrong expected exit8 produced exit101 at the named assertion left7/right8; the
restored expected exit7 produced exit0. Every phase recorded fresh run/spawn
child-written files read independently by the host, pending wait before release,
identical cloned terminal maps, and contemporaneous ESRCH for its spawned child.
PID readbacks are historical; no later numeric PID signal was used.

| Profile | RED / GREEN | Build seconds | RED / GREEN seconds |
|---|---|---|---|
| sys,no_float | 101 / 0 | 21.760 | 0.458 / 0.179 |
| sys,sync,no_float | 101 / 0 | 7.819 | 0.456 / 0.040 |

Original result: [result.json](result.json). Independent combined standards/spec/
assertion/native-input/closure review: [review.md](review.md), no findings.
Scope retirement: [cleanup.json](cleanup.json). Final exported-file integrity:
`manifest.sha256`. These results do not certify Windows, exception-path fault
injection, all X23/24 features or the entire process package.
