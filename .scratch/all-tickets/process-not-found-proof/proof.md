## E2E proof: X2/X8 missing-program and missing-cwd process failures

**Entry point**: A Rhai script calls the registered public Engine function
run(program, args, options). The real integration-test entry point is the
focused Cargo command recorded in attempt-01/command.txt.

**Stack exercised**: Public Rhai Engine evaluation → registered sys process
function → Unix process implementation → Linux process creation / cwd setup →
real test-binary child and filesystem record.

**Steps performed**:
1. Staged base revision 4ec8fb1094885223d4e1923ee70825214512a5be with the
   focused regression test and the previously accepted pinned Cargo.lock.
2. Started a valid test-binary child through the same Engine API. It wrote a
   PID and exit record into the test's unique TempDir.
3. Invoked a nonexistent executable, then a valid executable with a nonexistent
   cwd. Both used the same Engine entry point and independent fixture records.
4. Changed the X2 expected ErrorKind to PermissionDenied and reran the focused
   test; restored it, changed the X8 expected ErrorKind and reran; restored the
   original source and reran GREEN.
5. Saved raw outputs before the scoped runner removed its private build runtime.

**Evidence**:
- Test source: SHA-256 f3c3d3055a50a538d06ea20ae575f66ffa7d76550099225cf21fa036a79f0450;
  restored source has the same hash.
- Raw results: byte-preserving gzip captures in attempt-01/x2-red.stdout.gz,
  x8-red.stdout.gz and restored-green.stdout.gz; exact uncompressed and
  compressed SHA-256 values are in attempt-01/raw-stdout.sha256. Matching
  stderr and exit-status files remain uncompressed alongside them.
- Test command and runner recipe: attempt-01/command.txt and run.sh.
- Locked metadata and input hashes: attempt-01/cargo-metadata.json and
  input-identities.sha256. Workhorse admission and tool identity:
  attempt-01/remote-preflight.json. Run and cleanup details:
  attempt-01/runner-summary.txt.
- X2 mutant exited 101 with the targeted assertion showing actual NotFound and
  expected PermissionDenied. X8 mutant exited 101 at its cwd assertion after
  the X2 case passed. Restored GREEN exited 0 and reported one passing test.
- The valid-child output was child-pid=1695506 child-exit=0 and reap=ESRCH.
  X2 output recorded io_kind=NotFound and child_record_absent=true. X8 output
  recorded io_kind=NotFound and child_record_absent=true.

**Reused proof (if any)**: No behavior or assertion proof was reused. The pinned
Cargo.lock is a previously accepted build input from
.scratch/all-tickets/process-policy-proof/attempt-02/Cargo.lock.accepted;
its provenance and hash are recorded in the input manifest.

**Independent read-back**: The valid child wrote its PID/exit record to the
unique TempDir. The test separately read the file and checked kill(pid, 0)
returned -1 with errno ESRCH. For each negative case it independently checked
that the corresponding fixture record did not exist. The valid control produced
a record before the two absence checks.

**Assertion sensitivity**: For X2, replacing expected NotFound with
PermissionDenied failed at the X2 kind assertion. For X8, the same mutation
failed at the X8 kind assertion after X2 passed. Both showed actual NotFound;
restoring both expected values yielded a passing test.

**Setup and reset**: Workhorse Linux x86_64, Cargo 1.93.0 and rustc 1.93.0.
Before launch, no candidate heavy process was present; /var had 609381453824
free bytes and MemAvailable was 91926008 KiB. The central run_scoped.py at
Agent Skills revision 14617043b70d1ba2d40b720832cbad294fa8c008 ran once with a
600-second timeout and two Cargo jobs. TMPDIR was the exact owned session
scope; CARGO_TARGET_DIR and CARGO_HOME were inside AGENT_RUNTIME_DIR. The
runner removed its private runtime and this was confirmed by readback. The test
used TempDir, so mutable fixture files were scoped and removed. After exporting
the source identity, launcher and raw outputs, the exact owned session scope was
removed as its owner and Workhorse readback confirmed it absent. No shared test
data or other Session resource was touched.

**Verified**: On Workhorse Linux x86_64 with Rust 1.93.0 and
testing-environ,sys, public Engine run returns the expected Io/NotFound result
for a missing program and a nonexistent cwd; both fixture records remain absent.
The valid control verifies the fixture marker and independent child reaping.

**Unverified**: Native macOS and Windows; other Rust versions and feature
combinations; every other criterion in X2 and X8 outside this named Linux row;
all remaining tickets and release gates. This partial acceptance does not close
either full ticket.
