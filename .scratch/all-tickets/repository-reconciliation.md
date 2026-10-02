# Repository reconciliation

Fork: https://github.com/hoppworks/rhai.git

The owner requested all fork development histories and changes consolidated into
main, with main as the only remote branch. Fork main was pushed and independently
read back at61edd5993a76bff68588476b7e1f4028f54da259. git ls-remote --heads origin
returned exactly one head: refs/heads/main. No public upstream write occurred.

## Preserved and removed remote branches

Every exact tip below was verified as an ancestor of the pushed main before its
remote ref was deleted. Original commits remain reachable in main's history.

| Removed branch | Preserved tip |
|---|---|
| task/all-tickets | 7f4229a9012876ec75a24dba967e0d3ade6cd9d5 |
| task/linux-process-native-proof | 643033531581c8e8d556cfc025c75610c8a44585 |
| task/linux-process-proof-preparation | 85cb9abef802f75de874adf8a230b6dd2c7a0e4c |
| task/linux-process-proof-preparation-corrected | 60488ce5967831f21374fe3d4ed8013b18666861 |
| task/managed-unix-scope-close | c9aa8723b4ca6d1ce0ee29f9454c2c9c64467c12 |
| task/process-unix-run | 4a8d4e5cfa4e76ae62ebfcd1c4a77e3ee6207dd2 |
| task/windows-real-client | f9cc7372c12122dc2a88f0cd0049863161261d82 |
| task/windows-scoped-runner | dc63c38e061e2e5afc9d232421c075f177634563 |
| task/windows-scoped-runner-corrected | b6c8219d9bb507ae1e3b8ecb8db9ae75dbbd0028 |

## Verification and continued work

Unix production source matches the accepted native inputs: Linux80 restored owner
21/public32 and macOS81 restored owner21/public29 passed, with meaningful failure
controls, restored manifests and independent exact cleanup receipts. Five Windows
real-client scaffolding checks passed; native Windows custody/fixtures/real-client
acceptance remains open. Consolidation is not release acceptance. A source-only
PowerShell setup repair is being integrated directly into main after review.

Future campaign commits publish to fork main through coordinator integration;
remote task branches must not be recreated. Local isolated worktrees remain while
active. Foreign/dirty worktrees and uncommitted evidence are preserved.

Earlier local cleanup removed20 exact unoccupied integrated campaign branches,
and the earlier process-harness-review remote ref. This continuation removed nine
more remote refs. No worktree was deleted. Full prior branch/worktree inventory
is preserved in this file at0e868b3a and5269bcb2; local worktree retirement remains
separate from the verified remote-only-main result.
