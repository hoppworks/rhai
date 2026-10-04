# Linux final-drop consolidated correction

Frozen local correction for the six consolidated findings and the bounded missing-patch-tool setup repair. Writer worktree only: branch `task/linux-managed-success`, based on `ad51284c97f70cd82214c5c0d417da8861dcc5d2`. The exact c5422e helper dependency is retained and independently hash checked; no writer history was merged into the recovery/main worktree. Root's Native1 stopped before compiler/tests with `FileNotFoundError` for the absent `patch` executable; no tests ran. Outer and run-scoped statuses were 1; PID readback, runtime cleanup and scope cleanup statuses were 0, and 42 raw files plus 5 directories were preserved and hash checked (original tar SHA-256 `ecc85271f0750fa2085bfbcc66b1c492e918cbdef61439fe8ba9366fb712212f`). This setup repair does not run SSH, Cargo, native execution or signals.

## Findings closed by local checks

1. **Rust RED producers:** completed direct and managed identity emitters; managed positional expression count and tuple mapping were checked against actual patch source expressions and format placeholders. Strict `git apply --check --whitespace=error` and `git apply` against exact 523 test bytes passed; output digest `90d55b205d93816b156dd0c592d05d1987d92f851dc8031f91dadaac0e040166` matches the independent original patch-tool result. The regression ran with an isolated PATH containing Git only.
2. **`run_case` classification:** ordinary Cargo process identity remains available without classifying a RED case as a successful observer handshake. Probe invokes actual `run_case` with command-boundary substitution and RED-shaped output.
3. **Partial evidence:** observer, terminal and RED-control receipts are persisted incrementally and retain explicit incomplete/error state. Probes cover Cargo/host failure, managed leaf `PermissionError` after Cargo/host/sentinel/leader/worker reads, terminal failure after host, and control-terminal failure after host.
4. **Isolated custody namespace:** executed the full `CUSTODY` source with its actual argument positions/import namespace and localized proc/ps/pin boundaries. The exact synthetic fixture passed; `hashlib` resolves within the isolated namespace.
5. **Managed group and provenance:** complete managed/sentinel group census is bound to request/live/RED receipts, managed group equals leader PID, argv provenance uses exact stage paths, and physical stage absence is checked in retirement logic. Full CUSTODY rejected an empty group census and a foreign helper argv path.
6. **Source and pins:** stage derives the repository from its owned script location before resolving helper and lock paths; fixed `$repo` use before initialization under `set -u`. Executed the actual stage prefix with `bash -eu`, stopping before its first SSH command; it resolved repo, lock and c5422e helper paths and validated every local pin. The helper is c5422e; lock, archive helper, test, contract, patch, observer and proof pins are refreshed consistently.

## Verification and limits

Passed Python compilation for observer, proof, collector and recipe probe; `bash -n` for stage and launch scripts; `git diff --check`; actual recipe probes; strict Git patch check/application against immutable 523 test bytes; and the actual stage prefix under `bash -eu`, stopping before its first SSH. The new regression first failed against the old proof helper because the strict Git applier was absent, then passed after the repair. The Git-only PATH probe verifies patched-source digest `90d55b205d93816b156dd0c592d05d1987d92f851dc8031f91dadaac0e040166`, removing the missing external `patch` binary dependency that stopped Native1 before compiler/tests. Final probe output confirms actual patch request producer, live observer, RED terminal consumer, shared exporter validation, managed later-member preservation and full isolated CUSTODY positives/corruptions. The follow-up also ran actual coupled `run_case` + observer GREEN for direct and managed cases with requests both before and after the Cargo identity callback. It checked original recorder-before-thread ordering, full identity publication at observer entry, ACK before command return, terminal success, callback restoration, and rejection of missing Cargo identity, wrong Cargo start time and wrong host parent. The expected failing GREEN probe reproduced the 772 no-ACK boundary before the correction.

All new interaction evidence is synthetic local evidence with only process-table and pin boundaries localized. Linux/native acceptance remains **0**; Cargo behavior, real process ancestry/group retirement and remote execution remain unverified. This setup repair authorizes no further launch.

The earlier correction package consumed an estimated 56/60 minutes; exact cumulative active time remains unknown. This distinct missing-patch-tool setup repair uses a fresh 30-minute active planning checkpoint, not a history reset; approximately 15 additional minutes have been used so far (about 71 estimated cumulative minutes). Two earlier failed corrections, first Expert20, the one authorized handshake follow-up, and this separate setup cause remain recorded. No hard limit was reset or raised. Root-owned preflight must be repinned to the frozen proof hash before its next use.

## Frozen content pins

- `check-linux-current-msrv-examples.py`: `c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9`
- `archive-build-source.py`: `a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b`
- `drop-false-observer-handshake.patch`: `78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd`
- `drop-false-observer.py`: `07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2`
- `linux-drop-false-proof.py`: `61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53`

- `recipe-probes.py`: `015b5048c0f9bcfbc1a2199715263321687847f92549ce297f77cde7f91dbea0`
