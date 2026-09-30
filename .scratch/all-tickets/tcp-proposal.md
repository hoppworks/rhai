# TCP authority and lifecycle proposal

Status: approved by the owner on 2026-09-30; implementation and strict release proof remain open.

## Host authority

- NetPackage is optional, separate from sys and StandardPackage.
- NetConfig defaults to no connect/listen grants. Grant directions separately.
- Initial endpoints are numeric IPv4/IPv6 socket addresses. No implicit DNS.
- Connect grants match exact IP and port; listen grants match exact bind IP and
  port, with port 0 explicitly grantable for OS-selected ports. No name/wildcard
  policy framework in the first version.
- Script ports outside 0..=65535 fail before any socket operation. Connecting to
  port 0 fails validation; listen at port 0 is valid only with the explicit grant.
- Authorize before OS operations; denied binds create no listener and denied
  connects reach no independent peer.

## Blocking and resource limits

- Host config requires finite positive connect/read/write/accept deadlines, default
  five seconds. Scripts may shorten but cannot raise the configured ceiling.
- Validate negative, NaN, infinity, overflow and nonrepresentable durations first.
- Proposed maximum receive allocation is 1 MiB per call; host may lower it.
- Proposed package handle ceiling is 64 open stream/listener resources, shared
  across cloned handles and engines reusing the same package.
- Socket writes are bounded by host/engine input limits. The limits bound package
  storage and socket wait behavior; they do not provide an OS sandbox or a hard
  scheduler wall-clock guarantee.

## Public behavior

- Keep familiar address/connect/listen/read/write names where their contracts agree
  with the reference, without preserving zero padding or wrapping ports.
- Positive read N returns up to N actual received bytes; short reads are normal.
  EOF returns empty data. Negative lengths fail. Proposed read length zero returns
  empty immediately; require an explicitly named bounded read_to_end for EOF loops.
- Blob reads preserve bytes exactly; text reads decode the same captured bytes
  lossily, documented as unsuitable for preserving UTF-8 split across TCP reads.
- write returns actual count; write_all is an explicit full-transfer operation.
  Timeouts/errors after partial transfer expose progress and cannot claim no bytes
  reached the peer. TCP message boundaries are not promised.
- Separate read/write shutdown and full close. Repeated close is idempotent.
  Clones share logical close state; closing any clone closes the shared resource.
- Under sync, blocking I/O cannot hold a lock that prevents another clone closing
  or shutting down. Native behavior must prove cancellation/cleanup on all OSes.
- Accepted streams inherit host I/O limits and count against the same ceiling.
- Use NetError with kind, message, io_kind, op, target and partial-transfer detail;
  preserve SysError without pulling sys into net.
- Under no_index, omit Blob functions, retaining string I/O. Metadata and integer
  modes must preserve registration and validation. Unsupported gates fail explicitly.

## Real-peer acceptance scenarios

- Host binds port 0 before script connection; independent peer records script bytes.
- Script listener signals actual bound address; independent client exchanges bytes.
- EOF/short reads return exact prefixes without padding, including malformed UTF-8.
- Boundary ports and denied endpoints cause no peer connection/bind side effect.
- Finite no-data read and no-client accept fail with catchable timeout errors.
- Partial writes, half-close, repeated close, clone sharing and sync close unblock
  tests use explicit readiness and bounded peer completion, with owned cleanup.
- Handle ceiling includes clones correctly; rejected creation leaks no socket.
- Assertions must fail on a deliberately wrong payload/known-broken state before
  acceptance; changed harnesses invalidate prior controls.

## Owner decision

The owner accepted the recommended choices on 2026-09-30, prioritizing maximum
quality regardless of effort. This approves the concrete contract above, including
connect plus separately authorized listeners. It does not certify implementation,
relax verification, authorize remote publication or bypass native resource custody.
