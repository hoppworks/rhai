"""Light real observer signal/reap proof; not Engine feature acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("darwin_sampler", HERE / "check-current-darwin-sys-net-behavior.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.capture_runtime_proof()
actual_popen = subprocess.Popen
rows = []
for signum in (signal.SIGINT, signal.SIGTERM):
    owned = []
    prior_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    module.INTERRUPTED = None
    signal.signal(signal.SIGINT, module.on_signal)
    signal.signal(signal.SIGTERM, module.on_signal)
    def launch_observer(args, *positional, **keywords):
        child = actual_popen(args, *positional, **keywords)
        if args == ['/bin/ps', '-axo', 'pid=,ppid=,rss=']:
            owned.append(child)
            communicate = child.communicate
            injected = False
            def interrupted_communicate(*a, **kw):
                nonlocal injected
                if not injected:
                    injected = True
                    os.kill(os.getpid(), signum)
                    raise AssertionError('real signal handler did not interrupt')
                return communicate(*a, **kw)
            child.communicate = interrupted_communicate
        return child
    began = time.monotonic()
    try:
        subprocess.Popen = launch_observer
        try:
            module.sample_resources()
        except InterruptedError as error:
            assert module.INTERRUPTED == signum, module.INTERRUPTED
            assert len(owned) == 1, len(owned)
            child = owned[0]
            assert child.returncode is not None, 'observer not reaped before propagation'
            try:
                os.waitpid(child.pid, os.WNOHANG)
            except ChildProcessError:
                waitpid_no_child = True
            else:
                raise AssertionError('child wait ownership still present after cleanup')
            rows.append({'signal': signal.Signals(signum).name, 'observer_pid': child.pid,
                         'returncode_before_propagation': child.returncode,
                         'waitpid_no_child': waitpid_no_child,
                         'elapsed_seconds': round(time.monotonic() - began, 6),
                         'error': str(error)})
        else:
            raise AssertionError('expected InterruptedError did not propagate')
    finally:
        subprocess.Popen = actual_popen
        for sig, handler in prior_handlers.items():
            signal.signal(sig, handler)
        for child in owned:
            if child.returncode is None:
                child.kill()
                child.communicate(timeout=2)
receipt = {'scope': 'Actual Darwin ps observer, real SIGINT/SIGTERM, local termination/reap only; no Rustup/Cargo/Engine acceptance',
           'rows': rows, 'runtime': str(module.RUNTIME),
           'process_identities': (module.EVIDENCE / 'process-identities.tsv').read_text()}
target = HERE / 'darwin-sampler-native-interrupt-readback.json'
with target.open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print(json.dumps(receipt, indent=2), flush=True)
print('real_sigint_sigterm_observer_reap=PASS', flush=True)
