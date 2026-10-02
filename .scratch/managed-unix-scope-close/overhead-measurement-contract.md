# POSIX process-scope overhead measurement contract

This package measures descriptive overhead for the accepted `DirectChild` and
`Managed` process scopes on native POSIX hosts only. It does not establish
Windows results, a pass/fail performance threshold, or a spawn-to-first-byte
latency. The current public API exposes completion reports, not a first-byte
timestamp.

The ignored `process_scope_overhead_measurement` integration test exercises the
public Rhai `run_raw` API with a compiled AST and reused Engine per scope. The
timer starts immediately before `eval_ast` and stops when the completed report
returns. Engine setup, script parsing and AST compilation are outside the timed
region. No warmups are performed. Each of 30 pairs per workload contains one
sample in each scope; scope order alternates by pair, and true/capture workload
order alternates by pair as well. The resulting fixed total is 120 measured
executions: 30 true calls and 30 capture calls per scope.

The latency workload executes the real platform `true` binary directly, with a
2-second API timeout. The capture workload reuses the existing independent
`process_fixture` and simultaneous-I/O path, with a 6-second API timeout and an
8 MiB per-stream cap. The fixture emits exactly 8 MiB on stdout and 8 MiB on
stderr, accounting for its known libtest banner in the stdout payload. Each
returned report must have exit code 0, complete streams, exact byte counts and
the expected payload bytes. Its fixture PID must already be absent at report
return. Raw sample records include pair, scope, workload, elapsed nanoseconds,
stream byte counts and the recorded fixture-child count. The measured resource
claim is limited to that one capture child being absent at each API return; it
is not a global process or descriptor census. The scoped runner independently
exports its package identity ledger and final process/group counts. The driver validates all
120 unique records, writes CSV raw values, and reports per-scope/workload
medians and capture-throughput medians. It reports results without a threshold.

There are no retries: the first timeout, incomplete report, wrong payload,
missing/duplicate record or failed cleanup aborts the package. The maximum API
timeouts sum to 480 seconds (60 true calls × 2 seconds plus 60 capture calls ×
6 seconds). The command budget is Cargo 540 seconds and measurement driver 580
seconds, under the existing `run_scoped` 585-second and outer 600-second bounds.
Use one private build and one scoped invocation per POSIX platform. Preserve the
existing jobs≤2, descendants≤16, 2 GiB memory policy, and 1,572,864 KiB sampled
storage stop at one-second sampling. The sample maximum is not a continuous
storage peak. The scoped runner must export its exact identity ledger and
confirm zero retained package processes/groups before cleanup completes.

Run the driver from `tools/run_scoped.py` with a private source copy, Cargo home
and target directory all inside `AGENT_RUNTIME_DIR`; export its evidence folder
outside that runtime. A representative invocation is:

```sh
tools/run_scoped.py -- python3 .scratch/managed-unix-scope-close/measure-process-overhead.py \
  --source-dir "$AGENT_RUNTIME_DIR/source" \
  --evidence-dir .scratch/managed-unix-scope-close/overhead-evidence/<platform>-<revision> \
  --source-revision <40-hex-immutable-commit> \
  --source-archive-sha256 <64-hex-reviewed-archive-hash>
```

The caller must create/extract the exact reviewed source copy into the runtime,
set `CARGO_HOME` and `CARGO_TARGET_DIR` under the runtime, and arrange the
existing process/resource monitor and package hard timeouts. The driver refuses
to use a non-private source/build path or a reused evidence directory. The
measurement is POSIX-only; accepted Linux/macOS behavior evidence applies, but
full Windows verification remains open.
