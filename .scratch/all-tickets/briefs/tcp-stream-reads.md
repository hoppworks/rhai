# TCP receive and cancellable stream lifecycle

## Requirement

Implement bounded stream read_blob/read_string and explicitly bounded read_to_end
variants from tcp-proposal.md. Positive length returns actual bytes, short reads
normal, EOF empty, negative rejected, zero immediate empty. Text is lossy UTF-8
from the actual bytes with split-character caveat. Receive storage maximum1MiB,
host may lower; positive finite host read deadline default5s and optional script
millisecond deadline may lower, never raise. Accepted streams inherit read policy.
Structured NetError retains op/target/io_kind and partial captured progress when a
bounded EOF loop fails. no_index omits blob functions, string remains usable.

A blocking read must release state lock so another clone closes/shuts down. Full
close is idempotent shared state, cancels active read and frees quota once. Avoid
racing global socket timeout options across concurrent operations. Use an owned
Arc socket with brief state access, or a justified equivalent; no descriptor leaks.
Preserve listener/connect acceptance and host quota. This slice excludes writes,
write_all and complete half-close API, which are next bounded requirements.

## Context and first action

Read AGENTS.md, approved tcp-proposal.md and release-proposal.md, listener acceptance
review and actual stream/listener/config/error code. Role Standard, fresh feature
slice with own task/tcp-stream-reads worktree on coordinator ref assigned at launch.
Send concrete API/concurrency/timeout/partial-error design before implementation.
Use tdd: actual Engine and independently controlled real OS peer meaningful RED.
Use e2e-proof; only real byte observations count, no mocks or fixed readiness sleeps.

## Proof

Outgoing and accepted stream receive paths: independent peer bytes, exact short
prefix/no zero padding, EOF, malformed/split UTF-8, length validation, host cap,
no-data timeout, explicitly bounded EOF loop, clone shared state and close while a
read is observably waiting. Explicit readiness and finite channels/deadlines; own
thread guards close sockets and join on every error/panic path. A wrong independent
payload assertion must fail; restore and pass. Existing connect/listen suites plus
new reads run default net and sync; no_index applicable string proof. Run related
builds/checks/control within one invocation when reusing the cache, serial tests.

## Bounds

60 active minutes including coordinator review from actual launch clock; scoped
invocations <=900s; private build storage <=2GiB; <=16 simultaneous fixture sockets
and handles, CARGO_BUILD_JOBS=2. Python3 unchanged agent-skills/tools/run_scoped.py;
private source copy, Cargo home/target/TMP under AGENT_RUNTIME_DIR. Export necessary
logs before cleanup. Record launches, diagnosis, active time and scope in
.scratch/tcp-stream-reads/coordinator-state.md. Sampled/end storage is not continuous
peak. No shared service, credentials, installs, home configuration, remote writes
or merges. Stop on hard limits, contradictions, uncovered decisions or two launches
without diagnosis/closed check. One Expert/cause chain only if triggered, no reset.

## Deliverable

Report early design/RED, source/tests committed atomically as configured human,
exact ref and changes, proof/log/control paths, cleanup, remaining unverified gates.
Do not claim full net/release acceptance or introduce incomplete write behavior.
