# Suspended-child cwd-handle probe — inconclusive for product behavior

On 2026-10-29 a single bounded native Windows Driver attempted the x64-only
test `suspended_cwd_candidate_identity_and_reparse` under Rust/Cargo 1.77.2,
`testing-environ,sys,net`, base `b2608fc7c` plus only the test overlay pinned
in `binding.json`. The frozen source and media passed independent preflight
review. Driver elapsed 80.621 seconds of 180; observer reports exit 2,
`accepted=false`, stopped owned executables, no pending custody, and
`product_acceptance=false`.

Compilation succeeded. The first test created a suspended child and queried
its process parameters through the intentionally undocumented x64 PEB layout.
The candidate current-directory handle at the hypothesized offset was zero;
the assertion failed before any junction mutation or intended inverse control.
The test result was 0 passed, 1 failed, 2 filtered. No GREEN test ran. This is
an informative rejection of this *specific handle-location hypothesis* on
this machine, not evidence that the child lacks a current directory, that a
different API cannot verify one, or that the Rhai cwd contract passed/failed.
The earlier reparse-before-start finding remains applicable and the public
Rhai cwd RED remains open.

The serial capture crossed one log rotation; `serial-capture-binding.json`
ties both inodes and byte ranges to the preflight cursor. Its 204 frames
decoded 15 originals. All 15 saved files matched their recorded lengths and
SHA-256. The one native journal had eight independently checked length/CRC
records through `REMOVED`; the payload exit was nonzero. `wrong-result.png`
and the original wrong log independently show the zero-handle assertion.
After export, the exact guest scope was checked for reparse entries and
removed with absent readback (`retired.png`). The exact owned host ISO/stage
were removed, original sdc restored and foreign sdb left intact
(`host-cleanup.json`).

No implementation or acceptance claim is based on this prototype. A later
attempt needs a new documented way to bind process cwd identity, or a
different solution to the same accepted filesystem-authority contract.
