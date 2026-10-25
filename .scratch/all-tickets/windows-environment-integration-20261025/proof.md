# Integrate the accepted native Windows child-environment correction

Status: accepted for the private-child-environment prerequisite; combined
independent integration review PASS, including the alternate-wrapper pin correction. No new guest input, native run or compilation occurred.

## Actual correction

The old public Runner passed a null environment block to CreateProcessW. A child
received inherited temp/cache variables rather than paths under its own allocated
runtime. The accepted correction prepares a bounded Unicode child-only environment
and protected private work/temp, work/cargo-home and work/target directories before
payload creation, passes that block to CreateProcessW and frees it on every exit.
Parent variables and cwd are preserved. Directory handles remain pinned across
creation/validation and are disposed in reverse order; existing staged work paths
are rejected rather than reused or reset.

Four files are adopted byte-for-byte from the already natively tested frozen
source. All26 frozen inputs matched at adoption. A subsequent review corrected
three stale source-hash literals in the alternate CompileMonitorAcceptanceDriver.ps1
wrapper; 25 frozen inputs remain identical and that wrapper is the sole delta.
All13 compiled C# tool inputs remain exact matches to the native build. The alternate
wrapper has all9 source pins consistent but is still uncompiled and unexecuted. `adoption.json` records previous/accepted hashes and the exact source
manifest. Pending later work-retirement/backend changes in the dirty LLLM checkout
are not included. Neither that checkout nor its Rust/Windows implementation changes
were altered or staged here.

## Original native RED/GREEN retained

The existing Windows10.0.26300, non-admin RhaiTest/PowerShell5.1 native evidence
was accepted on2026-10-09. The same fixture records actual child cwd and five
variables through the public Driver/Runner/CreateProcessW path. Its pre-fix RED
reports all five mismatches and actual payload exit42 (0000002A). Its post-fix
GREEN reports payload0, contract PASS, exact private paths and zero mismatches.
Both public Drivers truthfully return0 because their specified payload exit is
observed. These are real child behavior assertions, not a mocked environment or
an assumption from directory creation. The child witness cwd is independently
bound to the actual Driver/journal allocation, rather than trusted by itself.

Original native fixture/compiler and public-tool builds are preserved. Their
source pins match all current compiled inputs; payload binarye663ad3f…, Driver
afd26a33… and Runnerb948dcba… match the exact GREEN observer. Compiler fingerprint
cf32cb7e… and the full manifests remain in the original exports. This is source
integration at that recorded native scope, not a new Windows/Rust/Cargo result.

The recorded combined review210343d6… exactly matches the first508424 bytes of
the preserved original report; appended report bytes are retained. Pre-launch
native_started=false markers remain historical; actual dispatch, raw serial
frames, child records and terminal results prove execution. Expired10-10 guest
build-retention paths are historical references, not authority to reuse them now.

## Fresh offline verification

Four original exports were replayed with the existing bounded project collector.
Only its optional console display was omitted for nested layouts; the complete
validation prefix is unchanged. All frame sequences, FILE lengths, CHUNK offsets,
SHA-256, FILE_END and terminal metadata equal the original readbacks; every saved
original also matches. Counts: fixture54frames/19files, RED35/9, tool build69/23,
GREEN36/9. Frozen source manifest1f554508… verifies all26 archived input files. Current
source differs only by the separately reviewed alternate-wrapper pin literals.

A separate semantic readback decodes the independently exported seven-line child
records. RED has five exact failing keys; GREEN has zero. Cwd equals the allocated
runtime, AGENT_RUNTIME_DIR equals cwd, TMP/TEMP equal work/temp, and Cargo home/
target equal their private work subdirectories. Selected parent preservation is
checked by the original actual observer. All16 journal records (eight per run)
pass independent CRC, byte length, grammar order and invocation checks, with the
correct payload exit, PayloadExited, confirmed cleanup and runtime removal.
HOST_EXPORTED=False is retained; host export is independently established by
original nonce-bound serial frames. `semantic-readback.json` records the scope.

The two fresh POSIX invocations were offline trace/semantic verification only
(120s and60s hard bounds), with owned runtimes, disabled Python bytecode caching
and exact empty-scope retirement. No build/cache is retained or foreign resource
changed. Existing native consumption/cause histories remain in originals; new
native compiler/control consumption is zero. Cost/token totals are unavailable.

## Remaining scope

This integrates the accepted native Windows private-child-environment prerequisite
only. Production Job-bound large work/cache retirement, remaining custody fault/
interruption controls, current guest ownership/artifact availability and Windows
Rust/Cargo/product acceptance remain open. The read-only current VM query confirms
only the intended UUID and running state. No current guest software state, retained
artifact validity, complete custody or release readiness is claimed. The old generic
payload-failure binding already accepts that narrow case; it is not scheduled again
solely because an older progress header still says it is next.

## Current execution route observation

On2026-10-25 the user directed continuation on workhorse. Its exact Rhai VM UUID
dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19 was shut off and was started normally after
read-only capacity/identity checks (81GiB available RAM,231GiB free /var; VM8GiB).
No other guest was started or changed. Existing mounted test media predate the
latest reviewed packet and are not authority to execute it. Lllm guest screenshot
was black and QEMU guest agent unconfigured; no input was sent to it. These are
readiness observations, not native acceptance or custody proof.
