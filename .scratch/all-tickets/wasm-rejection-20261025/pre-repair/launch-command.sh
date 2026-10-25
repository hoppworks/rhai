mkdir /var/roothome/.local/share/agent-builds/rhai/wasm-rejection-5015507b2728473597a1bbe53381b4dd
TMPDIR=/var/roothome/.local/share/agent-builds/rhai/wasm-rejection-5015507b2728473597a1bbe53381b4dd PYTHONDONTWRITEBYTECODE=1 python3 /var/home/workhorse/projects/agent-skills/tools/run_scoped.py --timeout 600 -- python3 -B /var/roothome/projects/rhai-wasm-rejection-20261025-5015507b/run.py > /var/roothome/projects/rhai-wasm-rejection-20261025-5015507b/run-scoped.stdout 2> /var/roothome/projects/rhai-wasm-rejection-20261025-5015507b/run-scoped.stderr
wasm_status=$?
printf "%s\n" "$wasm_status" > /var/roothome/projects/rhai-wasm-rejection-20261025-5015507b/run-scoped.status
rmdir /var/roothome/.local/share/agent-builds/rhai/wasm-rejection-5015507b2728473597a1bbe53381b4dd
exit "$wasm_status"
