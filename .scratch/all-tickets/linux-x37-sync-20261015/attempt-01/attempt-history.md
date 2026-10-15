# Attempt history

- Attempt 01: one scoped runner on integrated revision
  f6089906d586b038800e2649e01c88f7074986be with
  testing-environ,sys,sync, one Cargo job and a 900-second bound. The intended
  sentinel-live assertion RED exited 101; restored GREEN passed 1/1 and the
  runner exited 0. The first invocation compiled once; both cases used the
  same bounded session scope. See evidence/.
- One-job Tauron Cargo compilation was observed at preflight/postflight and left
  untouched. Exact runtime and scope were removed; no cache retained.
