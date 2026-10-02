# Repository reconciliation

Current verified fork main: `7f4229a9012876ec75a24dba967e0d3ade6cd9d5`. Original full inventory and first17
exact cleanup targets are retained at commit5269bcb2 in this file. Fetch was
fork-only; no upstream writes. Classification uses conservative orphan/foreign
labels, so absence of tracking metadata does not prove unmerged code or ownership.
No foreign or dirty worktree has been modified.

## Branches (default: `main`)

| Name | Kind | Category | Upstream |
|---|---|---|---|
| `archive/windows-scoped-runner-c4f87445` | local | orphan | - |
| `claude/vibrant-sagan-3g1pxn` | local | gone | origin/claude/vibrant-sagan-3g1pxn |
| `main` | local | default | origin/main |
| `task/all-tickets` | local | up-to-date | origin/task/all-tickets |
| `task/core-msrv-check` | local | orphan | - |
| `task/core-msrv-resolution` | local | orphan | - |
| `task/environment-fixtures` | local | orphan | - |
| `task/file-handle-compatibility` | local | orphan | - |
| `task/file-handles` | local | orphan | - |
| `task/filesystem-contract` | local | orphan | - |
| `task/linux-process-native-proof` | local | orphan | - |
| `task/linux-process-native-proof-draft` | local | orphan | - |
| `task/linux-process-proof-preparation` | local | up-to-date | origin/task/linux-process-proof-preparation |
| `task/linux-process-proof-preparation-corrected` | local | up-to-date | origin/task/linux-process-proof-preparation-corrected |
| `task/linux-sys-proof` | local | orphan | - |
| `task/managed-unix-scope-close` | local | orphan | - |
| `task/process-rust-io` | local | orphan | - |
| `task/process-unix-run` | local | orphan | - |
| `task/remote-cleanup` | local | merged | origin/main |
| `task/review-sys-windows` | local | gone | origin/claude/vibrant-sagan-3g1pxn |
| `task/stdlib-net-assessment` | local | gone | origin/task/stdlib-net-assessment |
| `task/tcp-connect` | local | orphan | - |
| `task/windows-real-client` | local | orphan | - |
| `task/windows-scoped-runner` | local | orphan | - |
| `task/windows-scoped-runner-corrected` | local | orphan | - |
| `origin/main` | remote | remote | - |
| `origin/task/all-tickets` | remote | remote | - |
| `origin/task/linux-process-native-proof` | remote | remote | - |
| `origin/task/linux-process-proof-preparation` | remote | remote | - |
| `origin/task/linux-process-proof-preparation-corrected` | remote | remote | - |
| `origin/task/managed-unix-scope-close` | remote | remote | - |
| `origin/task/process-unix-run` | remote | remote | - |
| `origin/task/windows-real-client` | remote | remote | - |
| `origin/task/windows-scoped-runner` | remote | remote | - |
| `origin/task/windows-scoped-runner-corrected` | remote | remote | - |

## Worktrees

| Path | Branch | Category | Tags |
|---|---|---|---|
| `/Users/hoppworks/projects/rhai` | main | default | - |
| `/Users/hoppworks/.codex/worktrees/linux-process-proof-preparation/rhai` | linux-process-proof-preparation-corrected | - | foreign |
| `/Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai` | stdlib-net-assessment | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-all-tickets` | all-tickets | - | - |
| `/Users/hoppworks/projects/rhai-core-msrv-check` | core-msrv-check | - | foreign |
| `/Users/hoppworks/projects/rhai-core-msrv-resolution` | core-msrv-resolution | - | foreign |
| `/Users/hoppworks/projects/rhai-environment-fixtures` | environment-fixtures | - | foreign |
| `/Users/hoppworks/projects/rhai-file-handle-compatibility` | file-handle-compatibility | - | foreign |
| `/Users/hoppworks/projects/rhai-file-handles` | file-handles | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-filesystem-contract` | filesystem-contract | - | foreign |
| `/Users/hoppworks/projects/rhai-linux-process-native-proof` | linux-process-native-proof | - | foreign |
| `/Users/hoppworks/projects/rhai-linux-sys-proof` | linux-sys-proof | - | foreign |
| `/Users/hoppworks/projects/rhai-managed-unix-scope-close` | managed-unix-scope-close | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-process-rust-io` | process-rust-io | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-process-unix-run` | process-unix-run | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-remote-cleanup` | remote-cleanup | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-review-sys-windows` | review-sys-windows | - | dirty, foreign |
| `/Users/hoppworks/projects/rhai-tcp-connect` | tcp-connect | - | foreign |
| `/Users/hoppworks/projects/rhai-windows-real-client` | windows-real-client | - | foreign |
| `/Users/hoppworks/projects/rhai-windows-scoped-runner` | windows-scoped-runner-corrected | - | dirty, foreign |


## Executed consolidation and cleanup

- Root source-only documentation/evidence fast-forwarded to fork main and read back.
- First17 listed unoccupied campaign refs were already reachable from main; ordinary
  git branch -d removed them. See prior5269bcb2 inventory for exactnames.
- process-api-report and process-api-compatibility cleanly merged, with empty
  git diff HEAD^1 HEAD for each. No file changed; their histories now belong to main.
  After verified push/readback, their two unoccupied local refs were deleted.
- process-harness-review likewise cleanly merged with empty parent diff. After
  verified push/readback its local ref and exact fork remote ref were deleted;
  git ls-remote confirms remoteabsence.
- Total20 local refs and1 fork remote ref retired. No worktree deletion.
- Remaining25 local branches and20 worktrees include unfinished source and foreign/
  dirty work. Final main-only request remains open. No process production gate waived.
