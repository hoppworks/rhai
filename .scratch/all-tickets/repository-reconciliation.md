# Repository reconciliation

Fetched fork-only origin on 2026-10-02. Classification is conservative: a missing tracking branch is labeled orphan even when the commit is reachable from main. The ancestry table below resolves that ambiguity without changing worktrees.

## Branches (default: `main`)

| Name | Kind | Category | Upstream |
|---|---|---|---|
| `archive/windows-scoped-runner-c4f87445` | local | orphan | - |
| `claude/vibrant-sagan-3g1pxn` | local | gone | origin/claude/vibrant-sagan-3g1pxn |
| `main` | local | default | origin/main |
| `task/all-tickets` | local | up-to-date | origin/task/all-tickets |
| `task/combined-package-proof` | local | orphan | - |
| `task/core-msrv-check` | local | orphan | - |
| `task/core-msrv-resolution` | local | orphan | - |
| `task/environment-fixtures` | local | orphan | - |
| `task/file-handle-compatibility` | local | orphan | - |
| `task/file-handle-docs` | local | orphan | - |
| `task/file-handles` | local | orphan | - |
| `task/file-reads` | local | orphan | - |
| `task/filesystem-contract` | local | orphan | - |
| `task/linux-net-release-features` | local | orphan | - |
| `task/linux-optional-msrv-proof` | local | orphan | - |
| `task/linux-process-native-proof` | local | orphan | - |
| `task/linux-process-native-proof-draft` | local | orphan | - |
| `task/linux-process-proof-preparation` | local | up-to-date | origin/task/linux-process-proof-preparation |
| `task/linux-process-proof-preparation-corrected` | local | up-to-date | origin/task/linux-process-proof-preparation-corrected |
| `task/linux-sys-proof` | local | orphan | - |
| `task/linux-sys-release-features` | local | orphan | - |
| `task/linux-tcp-proof` | local | orphan | - |
| `task/macos-sys-release-features` | local | orphan | - |
| `task/managed-unix-scope-close` | local | orphan | - |
| `task/net-feature-proof` | local | orphan | - |
| `task/optional-msrv-proof` | local | orphan | - |
| `task/process-api-compatibility` | local | orphan | - |
| `task/process-api-report` | local | orphan | - |
| `task/process-harness-review` | local | orphan | - |
| `task/process-io-design` | local | orphan | - |
| `task/process-prototype` | local | orphan | - |
| `task/process-rust-io` | local | orphan | - |
| `task/process-unix-run` | local | orphan | - |
| `task/remote-cleanup` | local | merged | origin/main |
| `task/review-sys-windows` | local | gone | origin/claude/vibrant-sagan-3g1pxn |
| `task/stdlib-net-assessment` | local | gone | origin/task/stdlib-net-assessment |
| `task/tcp-connect` | local | orphan | - |
| `task/tcp-docs-example` | local | orphan | - |
| `task/tcp-listener` | local | orphan | - |
| `task/tcp-stream-reads` | local | orphan | - |
| `task/tcp-stream-writes` | local | orphan | - |
| `task/unsupported-feature-proof` | local | orphan | - |
| `task/windows-real-client` | local | orphan | - |
| `task/windows-scoped-runner` | local | orphan | - |
| `task/windows-scoped-runner-corrected` | local | orphan | - |
| `origin/main` | remote | remote | - |
| `origin/task/all-tickets` | remote | remote | - |
| `origin/task/linux-process-native-proof` | remote | remote | - |
| `origin/task/linux-process-proof-preparation` | remote | remote | - |
| `origin/task/linux-process-proof-preparation-corrected` | remote | remote | - |
| `origin/task/managed-unix-scope-close` | remote | remote | - |
| `origin/task/process-harness-review` | remote | remote | - |
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
| `/Users/hoppworks/projects/rhai-all-tickets` | all-tickets | - | dirty |
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


## Exact ancestry relative to fetched fork main

| Branch | Main-only commits | Branch-only commits |
| --- | ---: | ---: |
| `archive/windows-scoped-runner-c4f87445` | 392 | 32 |
| `claude/vibrant-sagan-3g1pxn` | 417 | 0 |
| `main` | 425 | 0 |
| `task/all-tickets` | 0 | 33 |
| `task/combined-package-proof` | 223 | 0 |
| `task/core-msrv-check` | 425 | 2 |
| `task/core-msrv-resolution` | 307 | 0 |
| `task/environment-fixtures` | 398 | 0 |
| `task/file-handle-compatibility` | 380 | 0 |
| `task/file-handle-docs` | 291 | 0 |
| `task/file-handles` | 316 | 0 |
| `task/file-reads` | 304 | 0 |
| `task/filesystem-contract` | 394 | 0 |
| `task/linux-net-release-features` | 218 | 0 |
| `task/linux-optional-msrv-proof` | 194 | 0 |
| `task/linux-process-native-proof` | 2 | 5 |
| `task/linux-process-native-proof-draft` | 2 | 1 |
| `task/linux-process-proof-preparation` | 4 | 1 |
| `task/linux-process-proof-preparation-corrected` | 4 | 1 |
| `task/linux-sys-proof` | 381 | 0 |
| `task/linux-sys-release-features` | 208 | 0 |
| `task/linux-tcp-proof` | 228 | 0 |
| `task/macos-sys-release-features` | 185 | 0 |
| `task/managed-unix-scope-close` | 114 | 42 |
| `task/net-feature-proof` | 236 | 0 |
| `task/optional-msrv-proof` | 202 | 0 |
| `task/process-api-compatibility` | 129 | 2 |
| `task/process-api-report` | 118 | 2 |
| `task/process-harness-review` | 108 | 1 |
| `task/process-io-design` | 250 | 0 |
| `task/process-prototype` | 382 | 0 |
| `task/process-rust-io` | 245 | 39 |
| `task/process-unix-run` | 114 | 29 |
| `task/remote-cleanup` | 425 | 0 |
| `task/review-sys-windows` | 418 | 0 |
| `task/stdlib-net-assessment` | 400 | 0 |
| `task/tcp-connect` | 315 | 0 |
| `task/tcp-docs-example` | 227 | 0 |
| `task/tcp-listener` | 308 | 0 |
| `task/tcp-stream-reads` | 290 | 0 |
| `task/tcp-stream-writes` | 271 | 0 |
| `task/unsupported-feature-proof` | 218 | 0 |
| `task/windows-real-client` | 392 | 32 |
| `task/windows-scoped-runner` | 392 | 32 |
| `task/windows-scoped-runner-corrected` | 392 | 34 |

## First exact cleanup batch

The user authorized campaign consolidation and cleanup. These campaign-owned refs
have zero branch-only commits against fetched main and no worktree; all contents
remain reachable from main. No remote refs in this batch.

- `task/combined-package-proof`
- `task/file-handle-docs`
- `task/file-reads`
- `task/linux-net-release-features`
- `task/linux-optional-msrv-proof`
- `task/linux-sys-release-features`
- `task/linux-tcp-proof`
- `task/macos-sys-release-features`
- `task/net-feature-proof`
- `task/optional-msrv-proof`
- `task/process-io-design`
- `task/process-prototype`
- `task/tcp-docs-example`
- `task/tcp-listener`
- `task/tcp-stream-reads`
- `task/tcp-stream-writes`
- `task/unsupported-feature-proof`
