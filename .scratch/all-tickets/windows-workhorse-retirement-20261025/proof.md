# Native Windows private-work retirement and affected environment acceptance

Status: combined independent review PASS for these two infrastructure criteria.
Base is fork main `b0b3656394ba8b76172e5b3b7daabbc2c916455d`. This is not full
Windows custody, Windows Rust/Cargo/product acceptance, or A–F completion.

## Changed behavior and actual entry

The production Windows monitor retires its recorded private `work` tree only
after this allocation's exact closed-Job proof, before capturing bounded evidence.
Disposable work has separate entry/depth/path/byte bounds; immutable inputs and
result snapshots retain their existing limits. Identity changes, missing closure,
unsupported entries or limit failures retain custody/evidence and fail closed.
The public Driver accepts the added retirement fields in the canonical journal.

The exact previously source-reviewed packet was recovered from the task-owned
LLLM archive and executed on the owner-selected workhorse VM, UUID
`dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`. It was shut off and started normally;
other guests and LLLM's running guest were preserved. Native scope: Windows
10.0.26300.0, RhaiTest, 64-bit PowerShell5.1.26100.9444, C#compiler fingerprint
`cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1`.
The real Driver/Runner/CreateProcessW/Job route ran the finite payload.

Before the one BuildOnly allocation, actual reads confirmed 81GiB available host
RAM,231GiB free /var,68.01GiB free guest C and5733052KiB free guest memory.
Both exact new guest scopes were absent. All15 immutable inputs and the reviewed
Start/ISO hashes matched. No installation, reset or credential operation occurred.

## Native results and independent readback

| Case | Real result and acceptance |
|---|---|
| Abort after large work | Public Driver0; real payload42/PayloadExited; exact cleanup and absent runtime. Independent child stdout records2060 minimum entries,613419011 expected bytes and265-character relative path. CRC-bound EVIDENCE records2107 entries/613419011bytes and proofEXACT. Snapshot hashes match; its manifest excludes work. Wrong99999-entry expectation fails; restored2060 passes. |
| Affected child environment | Same native build, fresh control scope, Driver0/payload0; all five private paths and cwd match the independent allocation/journal. Parent variables/cwd are preserved; exact cleanup/runtime removal pass. Wrong TMP expectation is rejected on the fresh saved child record, then correct expectations pass. The original native RED and unchanged assertion-method binding are retained. |

Both journals have eight CRC-valid records in the required order with consistent
allocation identities. `native-semantic-readback.json` and
`verify-native-results.py` bind the child witnesses, producer stdout, snapshots,
original observers, exact byte/entry truth and compiler/source manifests.

The original abort observer remains `accepted:false` with its precise RUNTIME
parser failure. No success label was substituted into that receipt. Readback-only
export (106frames/32files) has a distinct ID, `native_reexecution:false`, current
`driver_launched:false` and original launch preserved separately. Its independent
filesystem query confirms the exact runtime absent. The fresh environment export
(111frames/33files) has actual observer `accepted:true`. Original raw streams,
FILE/CHUNK/hash/terminal receipts and decoded files are retained. HOST_EXPORTED=False
in the native journal remains truthful; serial export/readback is separate proof.

## Source and build applicability

All13 C# source hashes declared in the native build manifest match the integrated
candidate. Eleven were actual compiler inputs: nine production files, Driver and
PayloadFixture. CustodyBackendFixture/NativeScopePolicyFixture were inventory-only
in this selection; no execution is claimed from those declarations. The separate
historical filesystem fixture is reused at its exact Backend/fixture hashes
(`fs-fixture-reuse/`), not treated as production Job proof.

Four compiler processes ran in one bounded BuildOnly allocation: three outputs
plus the intended missing-source compiler control. Their status/Job/watchdog
receipts pass. Exactly two public Drivers ran (abort and affected GREEN), with
no compiler rebuild and no repeated abort. The retained native binaries are
Runner72b02940…,Driver27b1e6f3…,Payload8564df0b…; complete pins are in the original
build manifest and observers. Retained-build ownership, input applicability,
unchanged expiry and immediate reuse purpose are in `execution-binding.json`.

Fourteen of15 frozen packet inputs are adopted byte-for-byte. The control differs
only by two CRLF-safe RUNTIME/JOURNAL regexes, exactly the in-memory text executed
by the successful GREEN. The alternate compiler wrapper changes three dependent
hash literals and remains uncompiled/unexecuted. Rust/product API files and Cargo
dependencies are unchanged; applicable Linux/macOS/Rust evidence is retained.

## Causes, limits and cleanup

The first Start completed BuildOnly but its multiline end-anchor did not accept
Windows CRLF. A ReadAllLines continuation reproduced the old parser failure and
verified exactly one pin/fresh binary hash. Script-file execution was disabled in
the parent console; the same pinned control entered through ScriptBlock, without
changing policy/configuration. The first real abort then completed successfully
but its observer had the analogous CRLF-sensitive RUNTIME expression. Saved
stdout confirms zero old matches and one corrected match; JOURNAL was corrected
in the same bounded patch. Recovery reads the completed run rather than launching
it again. Initial fast keyboard corruption/unmapped-key refusal happened before
Start execution. A media-assembly SyntaxError occurred before image generation;
its exact empty scope was retired. These are preparation/parser causes, not new
product assertion failures. Original failed observations and reviews are kept.

Original bounds remain BuildOnly930s plus30s termination reserve, compiler180s,
Driver180s, export180s/64files/4MiB each/16MiB total/3500encoded characters per frame.
Readiness/entry fixes consumed no additional native allocation. Two small input
media were assembled (the second corrects readback launch metadata); neither is
another C# build. Durations/tokens/cost not present in original receipts are unknown.

All original results were exported before cleanup. Both exact mutable control
scopes were checked for owner/terminal custody, unexpected/reparse entries,
size/runtime remnants, removed, and read back absent (`guest-control-cleanup.png`).
Original sdb/sdc media were restored; both exact owned images removed after hash
verification/export. The disposable assembly source copy and POSIX runtime/scopes
were retired. Only the exact source-bound C# build remains for immediately
compatible custody followups within its original finite expiry; it is not a
license to reuse historical expired builds. Foreign work/processes are preserved.

## Remaining criteria

Other supervision/fault controls require current-source applicability checks and
any genuinely missing native rows. Windows Rust/Cargo, script/Engine/sys/net OS
behavior, required platform/feature/MSRV matrix and full Ticket03/release/A–F
remain open. The next action uses the existing custody control route and retained
compatible build, not another success/abort build merely for the repaired parser.

The optional pure parser fixture now includes canonical NONE/0/0 work metadata.
Its one literal matches the2cd12d8… hash already pinned by the frozen harness;
the alternate wrapper/README pin is refreshed. It was not compiled/executed in
this native selection. Actual natively compiled inputs remain unchanged.
