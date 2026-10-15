# Attempt history

- Preflight invocation 1: direct execution of the existing central
  tools/run_scoped.py was denied because the file is not executable. No Cargo
  process or test started. Read the runner entry and invoked it through
  python3, which is its supported interface.
- Attempt 01: one bounded Python-invoked scoped run at integrated revision
  197bd802d8ca4f91c47b577d2a70700b62908e61, with one Cargo job. Deadline
  and OutputLimit deliberate assertion REDs were 101; restored tests were 1/1
  each; scoped runner was 0. The run compiled once and reused its private target
  for three subsequent selectors. See evidence/.
- Cleanup: runner removed its private runtime; the exact owned session scope
  was empty and then retired. No build cache retained.
