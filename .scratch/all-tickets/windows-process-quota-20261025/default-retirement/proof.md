# Default Windows build retirement (2026-10-25)

The once-compatible default Runner/Driver build was retired before its original
workhorse UTC expiry of `2026-10-25T17:01:47.008186+00:00`. This is a resource
lifecycle result, not a new product assertion or a completed Windows gate.

## Preserved original build

- The unchanged original source/manifest/compiler/three-binary pins were checked
  before the read-only guest export. `binding.json` and `default-export-readback.json`
  bind 53 exported files and 1,640 sequential serial frames. The offline decoder
  passed; no compiler, Driver or project command was rerun.
- `default-export/` contains the exported originals. `serial-all-original.bin`
  preserves the collected original libvirt serial bytes, and
  `serial-collection.json` records their inode boundaries. The readback ISO and
  its source are preserved here, outside the guest scope.

## Exact guest and host closure

- The reviewed `retirement/cleanup.ps1` matched the sole owned
  `quota-build-e6ce6222dba147a8b43b2c79187d3184` scope and every one of its
  53 hash-bound files and 13 directories. It passed the native PowerShell parse
  gate before execution. `guest-cleanup-receipt.json` reports one stopped owner
  generation, the exact scope absent, original build retired, and no foreign
  resource touched. The original serial receipt and independent decoder remain
  under `retirement/`.
- A separate read-only PowerShell `Test-Path` returned
  `DEFAULT_BUILD_ABSENT=True`; `fresh-readback.png/json` record it. This does not
  substitute for the original one-scope census and receipt.
- The workhorse stage's exact 13 files and one directory were archived and
  independently hash-compared before removal (`host-stage-export.tar` and
  `retirement/host-staging-before.json`). Independent pre-execution review passed
  `retirement/retire-host-resources.py`: fixed VM UUID, two own ISO hashes,
  original `sdb/sdc`, active-process references, exact stage inventory, and
  fail-closed interpreter checks. It restored original `sdc`, then removed only
  those two own ISOs and the own staging directory. `host-retirement.json` and
  `host-final-readback.json` confirm their absence and original media presence.

The original expiry and historical build identity remain recorded in
`../retained-default-build.json`; its physical availability is now false. Accepted
quota and memory-denial proofs remain applicable at their stated bindings, while
failed backend export/cleanup, bounded real project commands, native Rhai and
release acceptance remain open.
