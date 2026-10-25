# Combined review: native Windows memory-denial prerequisite

**Disposition: PASS, limited to the named per-process and per-Job committed-memory denial prerequisite.** This does not close the Windows custody gate, packages A–F, native Rhai API behavior, or the release OS/feature/MSRV matrix.

## Review basis

- Base: `c20c4575589d06960c71127dbba7a28d8a622140`; candidate: that base plus the current scoped working-tree changes to `PayloadFixture.cs`, `RunPayloadEnvironmentControl.ps1`, and the fixture source pin in `RunSourceFixtures.ps1`.
- Applicable rules reloaded: central common instructions SHA-256 `e1a3b95adcd4384e5c65b447c482f2ce0f86d13dab37a36a53fc2d9129b81932`; project `AGENTS.md` SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`; `mattpocock-code-review` SHA-256 `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`; `delegate-within-agent` SHA-256 `a667270143c9740f6072c3d7538602a1d6f72fe82ea28501cd87a04e0a0c4cf4`.
- No tests, builds, guest commands, or cleanup actions were run for this review.

## Standards

No actionable standards violation found. The fixture uses actual Windows Job queries, `VirtualAlloc`, bounded readiness/exit waits, exact PID/creation identities, scoped files, and explicit cleanup. The PowerShell control validates source/build pins, owns and drains the public Driver streams, checks cleanup and absence of the exact runtime, and enforces its export bounds. Existing public binaries were reused by manifest hash; only the changed payload fixture was compiled for the accepted run.

## Spec and correctness

The fixture verifies the configured 1 GiB per-process and 2 GiB per-Job committed-memory limits, then distinguishes them with native results: a 1 GiB root request and a 512 MiB Job request each failed with Windows error 1455. Before those requests, recorded global available commit was 6,267,580,416 bytes and 4,617,801,728 bytes respectively; both leaf actors had committed 768 MiB, while root private bytes remained below 512 MiB. The protected marker stayed unchanged on denial. After one exact leaf exited and was reaped, the same-size 512 MiB request succeeded without retry. The control rejects a deliberately wrong limit expectation before accepting the intended values.

`attempt03/host-accepted-readback.json` and `verify-results.py` bind the native observer, saved output, CRC-checked eight-record journal, fixture source and binary, public binary pins, manifest, and file hashes. The native control exited 0 in 2.7212673 seconds; its 37-file/567-frame export passed the saved-data verifier. `build-readback/build-export-readback.json` independently binds the compatible fixture build's 48-file/1321-frame read-only export; it is correctly marked as non-acceptance evidence. Attempt01 and attempt02 are preserved as pre-entry failures and are not counted as product results.

## Cleanup and claim boundaries

The accepted guest cleanup receipt binds the two owned scopes and five exact process generations, confirms those scopes absent, verifies the retained default build before/after, and reports no foreign resources touched. The console readback is `MEMORY_READBACK False False True`. Host retirement records five exact media hashes removed, the 73-file/16-directory staging absent, original `sdc` restored, original `sdb` preserved, and no foreign resources touched. The retirement script's Python optimization bypass was fixed with fail-closed `__debug__` guards in both local and embedded remote interpreters before retirement; the recorded retirement used the reviewed script hash.

The earlier native acceptance readback retains `fresh_census_at_cleanup: pending` because it predates cleanup. The later guest cleanup receipt and host cleanup readback provide that separate census and are the evidence for the final cleanup claim; the earlier artifact was not rewritten.

The README, gate, plan, and coordinator state describe this as one accepted prerequisite and leave failed backend export/cleanup, bounded real project commands, full Windows custody, native Rhai behavior, and release coverage open. No broader completion is inferred.
