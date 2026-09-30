# Bounded launch specification transfer source

Continue the same owned Windows custody context after the immutable model's
related review corrections. Read the retained Expert answer and existing
MonitorTransport/LeaseMonitor bounds. Implement a pure managed transfer model
and source fixtures first; no workload/native execution or launch integration.

## Contract

Carry the complete accepted 8192-byte specification through the existing
512-byte maximum frame and 32-frame/8192-byte queue without raising limits.
Use explicit versioned BEGIN/DATA/END and bounded acknowledgements. Choose fixed
chunk size and header bounds whose worst case fits 512 bytes including delimiter.
A sender has at most one outstanding data frame, awaiting an acknowledgement
for that exact transfer/index before emitting the next. The whole base64 wire
will exceed queue capacity at maximum input; never queue it all at once. Queue
pressure is a failure or bounded retry by control polling, never a blocking wait
on the watchdog. Specify exact byte accounting and maximum frame count.

Bind transfer correlation to a monitor-issued token supplied by its owner, not
a host authorization claim. Validate total size/count before allocating a fixed
bounded assembly buffer. Require canonical strict UTF8/decimal/base64, contiguous
indexes, exact nonfinal/final chunk lengths and exact accumulated length. Reject
unknown versions, replay, wrong token, out-of-order/duplicate chunks, malformed
frames, overflow and trailing data. No replacement/restart after failed or
completed transfer. END may complete only an immutable successfully parsed
LaunchSpecification. Defensively copy model inputs/outputs.

The transfer uses a supplied fixed setup deadline/current monotonic time; check
expiry before each acceptance, including END/acknowledgement. It cannot extend
setup, lease or absolute lifetime. Stopping/cancellation/EOF/error invalidates
partial data. Transfer acknowledgements mean receipt only; they cannot authorize
create/resume or renew a lease. No shell, caller runtime/evidence paths, PID or
job handle fields. Keep pure transfer logic independent of filesystem/native I/O.

## Delivery and limitations

Author fixture source first for exact maximum-size valid transfer, per-frame
bounds, one-frame sender pacing, queue byte pressure, canonical/malformed inputs,
truncation, duplicate/index/token replay, expiry at the exact boundary, cancellation,
failed/completed terminality, immutable result and acknowledgement nonauthority.
Use intended diagnostics. Include exact quoting and model corrections retained
from the previous review; do not duplicate old tests without a new requirement.

Document model/protocol and the future MonitorTransport dispatch boundary. Do
not connect allocation, staging, job creation/resume or exact-job proof issuance.
Do not change existing watchdog/queue limits. Source-only model assertions do not
prove a working connection or end-to-end lease.

No compiler/build/fixture/native/guest commands, installs, remote writes, runtime
resources or workload launches. Preserve disabled public entry. Commit atomically
as the configured human author, report exact static checks and unexecuted paths.
Related source corrections remain in this context, not a new Expert chain or
completed failed full-custody attempt.
