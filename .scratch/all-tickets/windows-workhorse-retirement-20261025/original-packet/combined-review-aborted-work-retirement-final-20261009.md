# Combined source and packet review — 2026-10-09

READY for exactly the bounded BuildOnly plus real Exit-42 work-retirement prerequisite in this candidate. No remaining concrete source or packet blocker was found. This records the completed read-only review; no additional analysis or execution was performed to persist it.

## Exact candidate binding

| Artifact | SHA-256 |
|---|---|
| Start.ps1 | `890cdc7a21a880b9eb6b70f5696ef4396aebfd8fb0de8bc1781b938e4bf4cbeb` |
| input-manifest.json | `d7c82e92af18ef7367dd73478c3509baf63d2ff92c9f1af804c4f93cc75dc133` |
| workhorse-aborted-work-retirement.iso | `70cf18f7a107e4c0b3c0bdd5626417bb11c51422d8338db0967ff85c1332a4f6` |

## Concrete findings and resolved defects

- All 18 ISO files were independently compared byte-for-byte with the packet; all 15 source inputs matched the manifest and canonical LLLM source. The marker, invocation ID, nonce, manifest guard and harness source pins agree. The final graft-point image contains the required `input/` directory.
- Start copies the inputs once into the absent, invocation-owned private scope. It rejects existing build/control scopes, checks ancestor and input reparse points, and verifies the complete copied file inventory and every hash before launching. Bootstrap and control paths, SourceRoot and child WorkingDirectory use the verified private copy. Copy or verification failure preserves the scope rather than overwriting it on restart.
- The abort branch no longer reads the environment-only marker. Successful export requires the build observer and original bootstrap stdout/stderr from their actual outer build-session root, together with the build receipt and compiler logs. Start obtains its own hash from the verified read-only medium instead of relying on PSCommandPath. The explicit control result is propagated to Start's exit; exceptions or an absent result fail with exit 2.
- The unchanged production path treats a signalled payload exit 42 as PayloadExited. Native exact-Job accounting, root status, checked handle closure and complete output drain must succeed before closure authorization. That authorization precedes identity-bound work retirement, bounded evidence capture, outcome metadata and runtime removal. This candidate uses the production Driver/PayloadJob route, not the earlier scripted closure fixture.
- The finite payload fixture independently constructs 2,050 one-byte files, nine 65 MiB files and a long-path leaf: at least 2,060 files, 613,419,011 logical bytes and a 265-character relative path. These exceed the old entry, total-byte, per-file and path bounds. The observer requires the actual child witness, rejects an impossible work-entry expectation, restores the correct count/byte expectation, and checks the retirement journal, bounded snapshot and runtime absence.
- Bounds remain BuildOnly 930 seconds plus a 30-second termination reserve, compiler 180 seconds, fixture Driver 180 seconds, and serial export 180 seconds with 64 files, 4 MiB per file, 16 MiB total and 3,500 encoded characters per frame. Unconfirmed process custody and partial-export evidence are retained; there is no cleanup authorization for foreign resources.

## Acceptance boundary

READY establishes source and packet readiness for this one bounded prerequisite. It does not establish that the native run, RED/GREEN assertions, exact closure, retirement or host export/readback have passed. Those require the resulting original native evidence. A nonzero PayloadExited case does not establish an external monitor interruption. Full Windows custody, Windows Cargo/Rust acceptance, all A–F criteria and the overall plan remain open. Prior accepted evidence and rejected packet history remain applicable within their original bindings.

Rule revision read: central `1b6e1da85f87cad25f7aafc91aa782319ac6ef93`; Common `f71e8f97`, build-efficiently `58f676b4`, completion-gates `ea87fa62`, e2e-proof `4fdf5ef0`, resource-lifecycle `102bc29d`, project AGENTS `37f95ff6`. Mac memory entrypoints were read; the checked LLLM memory entrypoints and ~/.agents/AGENTS.md were absent. No archived run slots, PIDs or model mappings supplied authority.
