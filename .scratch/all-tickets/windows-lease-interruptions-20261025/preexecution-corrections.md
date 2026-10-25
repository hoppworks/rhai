# Affected preexecution corrections

No native case/build has run. Existing source bodies are retained except the
following explicit strengthened checks and result fields.

- Runtime and snapshot are distinct: Backend1339 allocates scoped-GUID; Backend690
  creates .scoped-evidence-GUID as the retained snapshot. The old scoped-* filter
  was not a snapshot-name typo. Controls now bind a unique CRLF-safe RUNTIME path
  to the exact case run/root GUID, use literal Test-Path and Force enumeration. A
  negative assertion checks the existing snapshot is rejected as an absent path,
  then the real absent runtime passes. Original marker/identity controls remain.
- Cleanup requires a hash-pinned host-accepted-readback.json, emitted only after
  all frame and semantic assertions pass. It matches every exported original
  file/hash plus the pinned disposable input fixture, rejects unexported entries,
  requires original observer booleans and rechecks exact payload PID/start liveness
  and actual runtime absence. All three scopes are checked before any deletion.
  This is export/data binding, not another human approval or independent service.
- The initial immutable input medium89b877… was never attached or executed; it is
  replaced after the source corrections. No native allocation is consumed.
