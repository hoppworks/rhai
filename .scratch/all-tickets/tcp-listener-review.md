# Listener acceptance review

Accepted candidate eda030a1ded6d102a2f2ea5128fcd0378818e839 on task/tcp-listener.
Production source review covered six Rust files; the final correction reviewed
one test file, with zero skips. All excluded proof files were assessed separately.
Numeric direction grants precede bind, RAII quota reservations release on failure,
listener and accepted streams share quota, and close releases state without holding
its lock across blocking accept. Deadline polling is finite and returns typed errors.

Native macOS proof: net connect4/listener6 and net,sync connect4/listener7 pass;
independent OS peer, denial preservation, timeout quota release, clone close,
final drop and shared accepted-stream quota are covered. Wrong peer assertion
fails for actual peer versus false port1. Expert03 required bounded worker retries;
the sole followup adds real saturated-quota expiry and bounded sync close, both
pass. No further Expert chain. Unchanged baseline/control evidence applies because
only that fixture and new expiry test changed. Followup native accept5s, retry6s,
channel12s and close-before-join preserve finite cleanup and op=accept assertion.

Final runtime agent-build-qml7nk5w and prior agent-build-hph67qpq were independently
confirmed absent at their exact recorded paths. End storage493888KiB and861980KiB
are not peak measurements. Evidence retained in ../tcp-listener/proof.md and logs.
This accepts connect/listen on native macOS; read/write, release feature/MSRV and
other native platforms remain open. Original12:34–13:34UTC allowance preserved.
