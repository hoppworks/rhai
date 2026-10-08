# Native Windows compiler prerequisite

Accepted by one combined independent review on 2026-10-08. This closes only the
narrow BuildOnly compiler/control slice. Public lease-client custody, complete
interruption/work/export gate, Windows process implementation and release matrix
remain open.

Native guest: rhai-win11-quality, UUID dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19,
RhaiTest non-admin, Windows NT10.0.26300, installed MSVC14.44/SDK10.0.26100.
Readonly ISO input and all twelve frozen source pins were checked before launch.
The original entry, manifest, media record, observer and serial export are retained
under bootstrap03-input, bootstrap03-media.json, bootstrap03-export and
bootstrap03-serial-original.txt. Exact native invocation:

```powershell
Get-Content -Raw E:\start.ps1 | Invoke-Expression
```

The reviewed new PowerShell child obtains its no-breakaway kill-on-close job and
finite watchdog before any compiler. BuildOnly compiles only ScopedRunner,
MonitorAcceptanceDriver and PayloadFixture serially. It has a 900-second overall
limit, 180 seconds per compiler, 4MiB per log, 1GiB per-process/2GiB aggregate
memory and 16 processes. The independent observer retains the exact child handle
and 930-second deadline; no persistent policy or parent environment is modified.

Allocation01 preserved the injected setup exception but returned zero when its
self-inclusive kill-on-close job was closed. The outer observer correctly rejected
it; no compiler was launched. Allocation02 proves the explicit E0000003 failure
status, real setup child cleanup/owner-only accounting and exit0/17/mismatch checks.
It reached a successful production compile, then failed driver compile with CS0103
for an existing TerminateJobObject call lacking its DllImport. Allocation03 adds
that exact declaration and updates the pin maps. All original attempts remain.

Allocation03 actual observer exit0 and accepted=true are independently bound to:
setup failure with child PID2404 plus primary marker and outer owner-only return;
actual exit17 rejected when expected0; exit0 and expected17 accepted; unavailable
status refused; all three native compiler exits0; missing-source control exit1
with CS2001; successful final job accounting/disposition and watchdog drain before
build-manifest.txt and the exact BUILD_ONLY_PASS result. The 24-file ordered serial
export has complete BEGIN/END, contiguous sequence/offsets and independently
recomputed file lengths/SHA-256. No public driver or payload was executed.

Retained reusable artifacts are below the exact guest run recorded in observer.json:
ScopedRunner.exe SHA33ea1e97546ac5797f576dc9e0388281432edac46db623c8d8583b70d9761812,
MonitorAcceptanceDriver.exe SHA026f12ef1ca17cec95aa1994591e1d59656f0279acca5f5ba53c9c798f0457c0,
PayloadFixture.exe SHAb571f5b91d632feac3a7770f5a116d3e0947bdf73fe388213fc11ffb72f7da6d.
Compiler SHAcf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1.
The manifest records all source pins. Reuse requires current source/compiler/argv
binding and fresh native file hash readback; changed runner sources invalidate
those binaries but not the unchanged standalone payload. These small private
artifacts remain for the next gate; targets/caches are absent. Retire only exact
owned roots after accepted replacement/export, by this execution's end. Failed
roots remain pending identity/ownership readback; never stop a guessed PID.

Combined review: bootstrap-review.md; SHAe5ca199beae0a4b0cc522e8969d21cbeea3b14c6ad57f4e53908b4f44d98b1af.
