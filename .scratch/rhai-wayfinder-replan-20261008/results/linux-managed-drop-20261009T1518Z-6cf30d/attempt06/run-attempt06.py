#!/usr/bin/env python3
import hashlib
import json
import os
import signal
import subprocess
import sys
import traceback
from pathlib import Path

ATTEMPT = Path(__file__).resolve().parent
BASE = ATTEMPT.parent
SESSION_ID = "linux-x35-20261009T1620Z-cd51a2"
SCOPE = Path.home() / ".local/share/agent-builds/rhai" / SESSION_ID
RUNNER = Path("/var/home/workhorse/projects/agent-skills/tools/run_scoped.py")
PAYLOAD = ATTEMPT / "payload.sh"
CLEANUP = ATTEMPT / "cleanup-after-run.py"
TIMEOUT = 1200
RUNNER_WAIT_SECONDS = TIMEOUT + 60
TERM_GRACE_SECONDS = 35
KILL_WAIT_SECONDS = 15
interrupted = []
runner = None
runner_pidfd = None


def record_signal(signum, _frame):
    interrupted.append(signum)
    if runner_pidfd is not None:
        try:
            signal.pidfd_send_signal(runner_pidfd, signal.SIGTERM)
        except ProcessLookupError:
            # The pidfd stays bound to this process identity after exit/reap.
            pass


for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, record_signal)


def write_text(name, value):
    (ATTEMPT / name).write_text(value)


def write_json(name, value):
    write_text(name, json.dumps(value, indent=2, sort_keys=True) + "\n")


def retire_scope(identity):
    try:
        current = SCOPE.lstat()
    except FileNotFoundError:
        write_text("build-scope-retirement.txt", "retired=false\nreason=scope disappeared\n")
        return False
    matches = (not SCOPE.is_symlink() and
               (current.st_dev, current.st_ino, current.st_uid, current.st_gid) == identity)
    entries = list(SCOPE.iterdir()) if matches else []
    if matches and not entries:
        SCOPE.rmdir()
        write_text("build-scope-retirement.txt",
                   f"device={identity[0]} inode={identity[1]} uid={identity[2]} gid={identity[3]} retired=true\n")
        return True
    write_text("build-scope-retirement.txt",
               f"device={identity[0]} inode={identity[1]} uid={identity[2]} gid={identity[3]} "
               f"retired=false identity_matches={matches} entries={[str(x) for x in entries]}\n")
    return False


def signal_owned_runner(signum):
    if runner is None or runner.returncode is not None:
        return
    if runner_pidfd is not None:
        signal.pidfd_send_signal(runner_pidfd, signum)
    else:
        # An unreaped child retains its PID, so this fallback cannot target a reused PID.
        os.kill(runner.pid, signum)


def stop_and_reap_runner():
    if runner is None or runner.returncode is not None:
        return
    try:
        signal_owned_runner(signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        runner.wait(timeout=TERM_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            signal_owned_runner(signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            runner.wait(timeout=KILL_WAIT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("runner remains unreaped after bounded SIGTERM/SIGKILL waits; retaining scope and skipping observer") from exc


def run_cleanup():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        with open(ATTEMPT / "post-run-cleanup.stdout", "wb") as stdout, open(ATTEMPT / "post-run-cleanup.stderr", "wb") as stderr:
            result = subprocess.run([sys.executable, str(CLEANUP)], cwd=ATTEMPT, env=env,
                                    stdout=stdout, stderr=stderr, check=False)
        status = result.returncode
    except BaseException:
        write_text("post-run-cleanup-launch-error.txt", traceback.format_exc())
        status = 125
    try:
        write_text("post-run-cleanup.status", str(status) + "\n")
    except BaseException:
        pass
    return status


# Cheap immutable preconditions happen before creating our unique build scope.
if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
    raise SystemExit("Linux pidfd support is required for safe signal forwarding")
if not RUNNER.is_file():
    raise SystemExit(f"scoped runner missing: {RUNNER}")
EXPECTED_RUNNER_SHA = json.loads((ATTEMPT / "inputs.json").read_text())["scoped_runner_sha256"]
INITIAL_RUNNER_SHA = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
if INITIAL_RUNNER_SHA != EXPECTED_RUNNER_SHA:
    raise SystemExit(f"scoped runner SHA mismatch before scope creation: expected {EXPECTED_RUNNER_SHA}, got {INITIAL_RUNNER_SHA}")
if SCOPE.exists() or SCOPE.is_symlink():
    raise SystemExit(f"refusing existing session scope: {SCOPE}")

scope_created = False
scope_identity = None
launcher_error = None
runner_status = None
cleanup_status = None
scope_retired = False
observer_ran = False
stdout = None
stderr = None

try:
    SCOPE.parent.mkdir(parents=True, exist_ok=True)
    SCOPE.mkdir(mode=0o700)
    scope_created = True
    scope_stat = SCOPE.lstat()
    scope_identity = (scope_stat.st_dev, scope_stat.st_ino, scope_stat.st_uid, scope_stat.st_gid)
    write_text("build-scope.identity",
               f"device={scope_stat.st_dev} inode={scope_stat.st_ino} uid={scope_stat.st_uid} gid={scope_stat.st_gid}\n")
    runner_sha = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    if runner_sha != EXPECTED_RUNNER_SHA:
        raise RuntimeError(f"scoped runner changed after preflight: expected {EXPECTED_RUNNER_SHA}, got {runner_sha}")
    envelope = {
        "session_id": SESSION_ID,
        "scope": str(SCOPE),
        "scope_identity": list(scope_identity),
        "runner": str(RUNNER),
        "runner_sha256": runner_sha,
        "timeout_seconds": TIMEOUT,
        "working_directory": str(BASE),
        "payload": str(PAYLOAD),
        "payload_sha256": hashlib.sha256(PAYLOAD.read_bytes()).hexdigest(),
        "cleanup_helper": str(CLEANUP),
        "cleanup_helper_sha256": hashlib.sha256(CLEANUP.read_bytes()).hexdigest(),
        "signal_forwarding": "HUP/INT/TERM to SIGTERM via retained pidfd; fallback signals only an unreaped direct child",
        "exception_cleanup": "all post-scope setup/launch/wait errors enter observer and exact-scope retirement after runner reap",
        "stuck_runner": "bounded TERM then KILL waits; retain custody and skip observer/retirement if still unreaped",
    }
    write_json("invocation-envelope.json", envelope)

    if interrupted:
        runner_status = 128 + interrupted[0]
        write_json("launch-decision.json", {"runner_started": False, "signals": interrupted})
        write_text("scoped-runner.status", str(runner_status) + "\n")
    else:
        env = dict(os.environ, TMPDIR=str(SCOPE), PYTHONDONTWRITEBYTECODE="1")
        stdout = open(ATTEMPT / "scoped-runner.stdout", "wb")
        stderr = open(ATTEMPT / "scoped-runner.stderr", "wb")
        command = [sys.executable, str(RUNNER), "--timeout", str(TIMEOUT), "--", "bash", str(PAYLOAD), str(BASE)]
        write_json("runner-command.json", {"argv": command, "cwd": str(BASE), "TMPDIR": str(SCOPE)})
        runner = subprocess.Popen(command, cwd=BASE, env=env, stdout=stdout, stderr=stderr,
                                  start_new_session=True)
        write_text("scoped-runner.pid", str(runner.pid) + "\n")
        runner_pidfd = os.pidfd_open(runner.pid)
        if interrupted:
            signal.pidfd_send_signal(runner_pidfd, signal.SIGTERM)
        runner_status = runner.wait(timeout=RUNNER_WAIT_SECONDS)
        write_text("scoped-runner.status", str(runner_status) + "\n")
except BaseException:
    launcher_error = traceback.format_exc()
finally:
    for stream in (stdout, stderr):
        if stream is not None:
            try:
                stream.close()
            except BaseException:
                if launcher_error is None:
                    launcher_error = traceback.format_exc()

    if runner is not None and runner.returncode is None:
        try:
            stop_and_reap_runner()
        except BaseException:
            failure = traceback.format_exc()
            launcher_error = (launcher_error + "\n" if launcher_error else "") + "Runner stop/reap failed:\n" + failure
    if runner is not None and runner.returncode is not None:
        runner_status = runner.returncode
        try:
            write_text("scoped-runner.status", str(runner_status) + "\n")
        except BaseException:
            launcher_error = (launcher_error + "\n" if launcher_error else "") + traceback.format_exc()
    try:
        write_text("launcher-interrupted.flag", json.dumps(interrupted) + "\n")
    except BaseException:
        launcher_error = (launcher_error + "\n" if launcher_error else "") + traceback.format_exc()

    runner_reaped = runner is None or runner.returncode is not None
    if scope_created and runner_reaped:
        cleanup_status = run_cleanup()
        observer_ran = True
        if cleanup_status != 0:
            try:
                write_text("build-scope-retirement.txt",
                           f"retired=false\nreason=cleanup observer failed with status {cleanup_status}; retained fail-closed\n")
            except BaseException:
                pass
        elif scope_identity is not None:
            try:
                scope_retired = retire_scope(scope_identity)
            except BaseException:
                launcher_error = (launcher_error + "\n" if launcher_error else "") + "Scope retirement failed:\n" + traceback.format_exc()
                scope_retired = False
        else:
            try:
                write_text("build-scope-retirement.txt", "retired=false\nreason=scope identity was not captured; retained fail-closed\n")
            except BaseException:
                pass
    elif scope_created:
        # Do not inspect or remove a scope while its runner could still be writing into it.
        cleanup_status = 125
        try:
            write_text("post-run-cleanup.status", "125\n")
            write_text("post-run-cleanup-skipped.txt", "runner was not reaped; retained scope for safe custody\n")
            write_text("build-scope-retirement.txt", "retired=false\nreason=runner was not reaped; retained fail-closed\n")
        except BaseException:
            pass

    if runner_pidfd is not None:
        try:
            os.close(runner_pidfd)
        except OSError:
            pass
        runner_pidfd = None

    if launcher_error:
        try:
            write_text("launcher-error.txt", launcher_error)
        except BaseException:
            pass
    try:
        write_json("launcher-result.json", {
            "runner_status": runner_status,
            "cleanup_status": cleanup_status,
            "observer_ran": observer_ran,
            "scope_retired": scope_retired,
            "runner_reaped": runner_reaped,
            "signals": interrupted,
            "launcher_error": launcher_error,
        })
    except BaseException:
        pass

if runner_status is None or runner_status != 0 or cleanup_status != 0 or interrupted or not scope_retired or launcher_error:
    raise SystemExit(1)
raise SystemExit(0)
