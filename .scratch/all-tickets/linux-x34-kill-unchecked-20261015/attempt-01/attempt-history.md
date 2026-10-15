# Attempt history

- Attempt 01: one scoped Python runner invocation at integrated revision
  29d3a44096fb35c315931926af142b2af00300bf. Features
  testing-environ,sys,unchecked; one Cargo job; 900-second bound. The deliberate
  public kill-report assertion RED exited 101 after exact lifecycle and cleanup
  observations. Restored GREEN passed 1/1; runner status 0. One cold compile,
  then incremental GREEN; no cache retained.
- Preflight showed one Tauron build, which was preserved. The exact owned
  session scope/runtime were removed. Evidence and timings are in evidence/.
