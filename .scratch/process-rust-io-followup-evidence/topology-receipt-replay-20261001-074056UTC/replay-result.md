# Attempt3 topology receipt replay

This was a pure-Python replay of private copies. No native process, fixture, build, or install ran. The retained attempt3 raw receipt was only copied into the scoped runtime; its source SHA-256 is `e545dafd06694258e3342a7d9cb9a96e29097341330b6a21ef2df93d6479351e` and it remains under the original attempt3 evidence directory.

Command: `.scratch/process-rust-io/evidence/topology-receipt-replay-20261001-074056UTC/run.sh`

The wrapper invoked `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 90 -- python3 <evidence-dir>/replay.py`. The replay copied `test_workload_topology_receipt.py`, `process_identity.py`, `test_process_identity.py`, and the raw receipt into `$AGENT_RUNTIME_DIR/topology-replay`.

Results: pre-fix duplicate-field assertion failed with the expected `KeyError('worker_joins')`; current assertion accepted the raw receipt; actual-copy controls for `workers_joined=2`, `wake_to_join_ms=1001`, and wrong pre-escape session ID each failed with `AssertionError`; focused `unittest` ran 11 tests and passed. No assertion was weakened.

SHA-256 of current `test_workload_topology_receipt.py`: `113a7d85333045d89f905df31b594e0d12b7781da24e72b9b521d3239bf545e6`. SHA-256 of raw attempt3 receipt: `e545dafd06694258e3342a7d9cb9a96e29097341330b6a21ef2df93d6479351e`.

Terminal cleanup readback: PASS; scoped runtime `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-4bjlvyla` was absent immediately after the wrapper returned. Full stdout is in `replay.log`; `run.sh`, `replay.py`, `runtime-path.txt`, and `cleanup-readback.txt` preserve the command and cleanup proof.
