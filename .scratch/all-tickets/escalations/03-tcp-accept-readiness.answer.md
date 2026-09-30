# TCP accept readiness assessment

Candidate: `8b8255774a2685c2116383520853f9e667f3a79b` in
`/Users/hoppworks/projects/rhai-tcp-listener`.

Do not accept the fixture's finite-worker claim yet. One small fixture correction
is needed: give the ResourceLimit retry loop its own monotonic deadline. No
production listener rewrite is justified by this review.

## Readiness conclusion

`tests/net_listen.rs:153–169` is a valid observation of an outstanding worker
accept reservation. The only persistent resource is the original listener, quota
is two, and a failed probe reservation does not increment the counter
(`src/packages/net/mod.rs:188–196`). Consequently a probe's ResourceLimit means
the worker owns the second slot inside `accept`, rather than merely having sent
the early ready message at test line 142. Probe reservations that succeed are
released by RAII at `mod.rs:164–169` when their one-millisecond accept times out.
Retrying ResourceLimit fixes the identified race in which the probe temporarily
owns that second slot before the worker enters accept.

This proves an in-progress no-peer accept, which is sufficient readiness for
concurrent clone close. It does not prove that the OS has already returned
WouldBlock: reservation precedes the first OS accept at
`src/packages/net/listener.rs:84–110`. Do not describe the observation as an
instrumented OS wait. Requiring an additional test seam merely to observe the
first WouldBlock is unnecessary for this slice's outstanding-call contract.

The observed error after close is consistent with the actual source: clone close
takes the shared listener and releases its slot (`listener.rs:25–33`); the
worker examines that shared state on each nonblocking iteration, with the mutex
released before the at-most-five-millisecond sleep (`listener.rs:96–126`). An
accept cannot hold that mutex across a socket wait in this implementation.

## Concrete bound gap and minimal correction

`tests/net_listen.rs:145` retries ResourceLimit without a deadline or retry limit.
Its five-second native timeout begins only after quota reservation succeeds;
ResourceLimit returns before the native wait loop. A permanently rejected
reservation therefore never reaches that timeout. The controller's two-second
probe and one-second result-channel timeout do not stop the worker; line 180
then joins unconditionally. A reservation regression can turn a diagnostic test
failure into a stuck join until the outer runner kills the process.

Under the candidate's correct quota and close implementation, stopping the probe
and closing the listener makes a slot available, and the worker exits. That
conditional reasoning explains the green run but does not supply the explicit
fixture bound required by the brief. The result-channel timeout is an observation
bound, not a join bound.

Minimal correction, confined to this test:

1. Before spawning, register a host test function on the worker Engine that reports
   expiry of a captured `std::time::Instant` deadline. Choose a documented finite
   worker budget longer than the controller's one-second readiness plus two-second
   probe budget, for example six seconds.
2. Check that function at the top of every retry iteration, outside the catch
   block. On expiry, leave the script with a distinct failure result; do not treat
   expiry as a successful close observation. Continue retrying only ResourceLimit.
   A host function works with unchecked as well; `on_progress` and
   `set_max_operations` are unavailable there.
3. Retain close-before-join and all assertions after join. Align the completion
   receive timeout with the documented worker deadline plus at most one five-second
   native accept and a small diagnostic margin. This makes the bound independent
   of the controller's successful close and of quota becoming available. It does
   not promise a hard OS scheduling deadline.

The current test captures readiness, probe, close and channel errors before its
assertions (`tests/net_listen.rs:149–190`), and joins even when any of those captured
operations fails. Keep that ownership structure. No source error return or
assertion between spawn and join currently bypasses cleanup. The needed change
is a worker termination bound, not moving assertions or detaching the thread on
channel timeout. The outer 900-second runner remains containment for process
failure or broken native blocking behavior; it cannot substitute for this bound.

## Evidence disposition

Read `proof.md`, `coordinator-state.md` and the final `accept-net.log`,
`accept-net-sync.log`, and `accept-wrong-peer-control.log` under
`.scratch/tcp-listener/`. Final logs record net connect 4/listener 6 and sync
connect 4/listener 7 passing, plus the intended independent-peer mismatch failure.
The two quota-limited timeout calls in `tests/net_listen.rs:111–125` genuinely
exercise release: a leaked first reservation would prevent the second Timeout.
Those separate assertions and their evidence remain applicable when unchanged.

The readiness result is accepted as an outstanding accept observation. The
finite-worker/finite-join claim in proof.md is not accepted until the deadline
correction receives source review and targeted real-OS verification in the one
remaining responsible-context followup, within the original allowance. Exercise
the expiry outcome as well as the successful close outcome so the new control is
known to terminate. Do not repeat unrelated peer controls or whole feature rounds
solely because this assessment was written. If the original allowance is exhausted,
stop with finite worker termination explicitly open.

Review coverage: three relevant source files reviewed, zero skipped; the specified
final proof/state/log records reviewed. No builds, tests, fixtures, installations,
remote operations, or production/test source edits were performed. OCR selection
commands were not run because this brief fixes the scope and permits source-only
inspection; the review was performed directly against the named source.
