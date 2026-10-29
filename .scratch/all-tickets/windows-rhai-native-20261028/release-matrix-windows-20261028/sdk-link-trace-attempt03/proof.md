# Native Windows SDK linker microprobe, attempt 03

Outcome: **infrastructure RED before the compiler**. This attempt makes no Rhai
product or SDK-link acceptance claim. It preserves the accepted release profiles
and attempts 01–02 without rerunning them.

## Binding and execution

- The pinned integrated head before preparation was `9439f27b4896ae7a5833d9840735c3f07a760420`.
  The frozen Rust source inventory matches that head (448 archived files, source
  commit `7019821fc9d7814d0632fea06de50933aa9e35ee` plus the recorded test
  overlay), with Cargo.lock SHA-256
  `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
  This control ran no Cargo target or Rhai product test.
- VM `rhai-win11-quality`, UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`,
  reported Windows NT 10.0.26300.0. The controlled CL, LINK and SDK
  `kernel32.lib` hashes and paths are in `binding.json`; the live guest queried
  them in `guest-sdk-kernel32-query-result.png`. The owned ISO SHA-256 was
  `b3ac50e6b9409e390d4f57271d0980b92733cea7817f72af4db004a37755bb0f`.
  `iso-build-readback.json` verifies all nine media inputs. The original sdb
  remained attached; only the owned sdc media changed.
- An independent source review approved the explicit absolute SDK library path
  before the ISO build. `scope-absence-result.png` shows the own guest scope
  absent; `parser-result.png` shows zero errors for all three PowerShell files.
  `host-dispatch-preflight-final.json` binds the media, source, VM, expiry,
  capacity, original COM1 inode and offset immediately before dispatch.
  `dispatch-typed.png` records the exact hash-guarded command. Driver deadline
  was 180 seconds, observer 185 seconds, export 180 seconds.

## Original result and cause

- `observer.json` reports Driver PID 5800, 5.58 seconds, exit 2, no observer
  kill, drained pipes, disposed process, no custody pending and stopped owned
  executables. The original Driver stderr states that success did not match
  the exact payload/client exit contract.
- The original journal passed length/CRC checks and has all eight states through
  `REMOVED`. Its `EVIDENCE` and `OUTCOME` records show payload exit `00000055`
  (decimal 85) and cleanup confirmed. `RunRhaiContract.cmd` line 5 is the sole
  `exit /b 85` in this payload. It follows `cd /d "%~dp0"`, which changes
  into the staged source directory, then compares `%CD%` with
  `%AGENT_RUNTIME_DIR%\work`. The script therefore rejected its own directory
  switch. No compile, link, response-file check or executable run occurred.
  This is a payload preparation error, not a newly demonstrated product defect.
- The original COM1 log rotated during export. The preflight inode
  `126867980` became `.0` at exactly 2 MiB; current inode `126869568` held
  the remainder. `capture-rotated-serial.py` verifies both inodes, the original
  offset and a unique BEGIN/END before writing the contiguous suffix.
  `serial-capture-binding.json` records SHA-256
  `d5a07a0a8f428e6b05a65e66724ba415d65fdad2e568b74e50ccf5e50080cf4c`.
  `decode-native-export.py` recovered 181 ordered frames and 10 hash-checked
  original files. `journal-readback.json` records the failed exit without
  treating it as PASS. The guest original files were exported before deletion.

## Custody and next step

- `guest-closure-result.png` shows the exact scoped runtime absent and no
  `MonitorAcceptanceDriver`/`ScopedRunner` process. The guarded retirement
  command removed only guest `n-32483e88`; `guest-retirement-confirm-result.png`
  independently shows that outer scope absent and no named process.
- `cleanup-host.py` restored the original live sdc media and verified the
  inactive media, unchanged foreign sdb, exact ISO hash, single link, no ISO
  holder, then retired only this attempt's ISO and host stage (51 files).
  Final `virsh domblklist` readback showed original sdc in both live and inactive
  definitions and the foreign sdb unchanged; exact owned stage and ISO were
  absent. `host-cleanup-readback.json` preserves that receipt. The temporary
  POSIX ISO-build scope was also retired after its own run.
- Correct the payload's directory assumption after inspecting the complete
  source-to-runtime command path. A bounded native rerun is justified only
  after that correction and review. It should capture the response file before
  cleanup and establish a fresh executable run marker. Even a passing explicit
  SDK path probe would not identify which SDK path Cargo chose in attempt 02.
  `combined-review.md` records the independent source and result review.
