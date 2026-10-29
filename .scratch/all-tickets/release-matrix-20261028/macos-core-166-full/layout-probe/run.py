"""Compare the minimal enum shape on the MSRV and current compiler."""
import json
import os
from pathlib import Path
import subprocess

root = Path('/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai/.scratch/all-tickets/release-matrix-20261028/macos-core-166-full/layout-probe')
runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
source = root / 'main.rs'
results = []
for toolchain in ('1.66.0-aarch64-apple-darwin', 'stable-aarch64-apple-darwin'):
    env = dict(os.environ, RUSTUP_TOOLCHAIN=toolchain)
    binary = runtime / ('probe-' + toolchain.split('-')[0])
    compiled = subprocess.run(['rustc', '--edition=2021', str(source), '-o', str(binary)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
    output = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=5) if compiled.returncode == 0 else None
    results.append({'toolchain':toolchain, 'compile_exit':compiled.returncode,
                    'compile_output':compiled.stdout.decode(errors='replace'),
                    'run_exit':None if output is None else output.returncode,
                    'size':None if output is None else output.stdout.decode().strip()})
(root/'result.json').write_text(json.dumps(results,indent=2)+'\n')
assert [item['size'] for item in results] == ['56','48']
