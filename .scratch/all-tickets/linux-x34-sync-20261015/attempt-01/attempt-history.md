# Attempt history

- Attempt 01: one scoped Python runner invocation at integrated revision
  aedf7857e3aca48797b6f3ee178c4209aad90ea1. Features were
  testing-environ,sys,sync, with one Cargo job and 900-second bound. Both
  assertion REDs exited 101; both restored GREEN tests passed 1/1; outer runner
  exited 0. The first selector compiled the target; remaining selectors reused
  it. See evidence/.
- Post-run hash-check command initially used the project cwd instead of the
  deleted private source copy and could not find Cargo.lock. A direct hash
  comparison against the preserved lock fixture, current production source and
  restored test source then passed. A second cosmetic output command had a
  shell formatting typo; it did not invoke tests or modify data.
- The Tauron gateway Cargo build was active in parallel at preflight and
  postflight; it was not changed or stopped. Exact runtime and scope were
  removed; no cache was retained.
