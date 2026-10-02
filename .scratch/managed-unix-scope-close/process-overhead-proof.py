#!/usr/bin/env python3
"""Prepare the private Linux source/build runtime and run the frozen measurement."""

from __future__ import annotations

import hashlib
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time


REVISION = "00bed4a0dfeb103ff209ba4c76dac7ae797b7c56"
ARCHIVE_SHA = "5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98"
BASELINE_SHA = "8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa"
EDGE_LOCK_SHA = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
RUST = pathlib.Path("/root/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin")
SOURCE_PATHS = (
    "Cargo.toml",
    "src/packages/sys/config.rs",
    "src/packages/sys/mod.rs",
    "src/packages/sys/process.rs",
    "src/packages/sys/process/unix.rs",
    "tests/sys_process.rs",
)
MAX_DRIVER_SECONDS = 580
MAX_CARGO_SECONDS = 540
SAMPLED_STORAGE_STOP_KIB = 1_572_864


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proc_start_ticks(pid: int) -> tuple[str, int, int, str]:
    proc = pathlib.Path("/proc", str(pid))
    raw = (proc / "stat").read_text()
    fields = raw[raw.rfind(")") + 2 :].split()
    cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    return fields[19], int(fields[1]), int(fields[2]), cmdline


def monitor_health() -> tuple[bool, str]:
    ready = pathlib.Path(os.environ["PROOF_CUSTODY_READY"])
    heartbeat = pathlib.Path(os.environ["PROOF_CUSTODY_HEARTBEAT"])
    if ready.is_symlink() or heartbeat.is_symlink() or not ready.is_file() or not heartbeat.is_file():
        return False, "custody ready/heartbeat file missing or symlinked"
    try:
        match = re.fullmatch(r"pid=(\d+) start_ticks=(\d+)\n?", ready.read_text())
        age = time.time() - float(heartbeat.read_text().strip())
    except (OSError, ValueError):
        return False, "custody identity/heartbeat is unreadable"
    if not match or age > 3.0:
        return False, f"custody identity malformed or heartbeat stale ({age:.3f}s)"
    expected_pid, expected_start = int(match.group(1)), match.group(2)
    current = os.getpid()
    try:
        for _ in range(12):
            start, parent, _, _ = proc_start_ticks(current)
            if current == expected_pid:
                return (start == expected_start, "ready" if start == expected_start else "runner start identity changed")
            if parent <= 1:
                break
            current = parent
    except (OSError, ValueError, IndexError) as error:
        return False, f"runner ancestry unreadable: {type(error).__name__}"
    return False, "run_scoped identity is not in this process ancestry"


def wait_for_monitor_ready() -> None:
    deadline = time.monotonic() + 2.0
    last_reason = "custody monitor has not published readiness"
    while time.monotonic() < deadline:
        healthy, reason = monitor_health()
        if healthy:
            return
        last_reason = reason
        # The monitor is launched alongside run_scoped, so allow only a short
        # startup handshake window. Once ready, every later check is immediate
        # and fail-closed; the monitor's 3-second stale-heartbeat bound remains.
        if "missing or symlinked" not in reason and "unreadable" not in reason:
            break
        time.sleep(0.05)
    raise RuntimeError(f"process custody monitor did not become ready: {last_reason}")


def source_manifest(evidence: pathlib.Path, source: pathlib.Path, phase: str) -> None:
    with (evidence / "source-restoration-manifests.tsv").open("a", encoding="utf-8") as output:
        for relative in SOURCE_PATHS:
            output.write(f"{phase}\t{relative}\t{digest(source / relative)}\n")
        output.flush()
        os.fsync(output.fileno())


def sampled_runtime_storage(runtime: pathlib.Path, evidence: pathlib.Path, stop: threading.Event,
                            failures: list[BaseException], samples: list[int]) -> None:
    output_path = evidence / "resource-samples.tsv"
    try:
        with output_path.open("w", buffering=1, encoding="utf-8") as output:
            output.write("utc_epoch\tsampled_runtime_kib\n")
            next_sample = time.monotonic()
            while not stop.is_set():
                result = subprocess.run(
                    ["du", "-sk", str(runtime)], capture_output=True, text=True,
                    timeout=4, check=True,
                )
                fields = result.stdout.strip().split(maxsplit=1)
                if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(runtime):
                    raise RuntimeError(f"malformed private runtime storage sample: {result.stdout!r}")
                size = int(fields[0])
                samples.append(size)
                output.write(f"{time.time():.3f}\t{size}\n")
                if size >= SAMPLED_STORAGE_STOP_KIB:
                    raise RuntimeError(
                        f"sampled private runtime storage reached {size} KiB "
                        f"(stop {SAMPLED_STORAGE_STOP_KIB})"
                    )
                next_sample += 1.0
                if stop.wait(max(0.0, next_sample - time.monotonic())):
                    break
    except BaseException as error:
        failures.append(error)
        print(f"STORAGE_SAMPLER_FAILURE {type(error).__name__}: {error}", file=sys.stderr, flush=True)


def stop_storage_sampler(stop: threading.Event, thread: threading.Thread) -> None:
    stop.set()
    thread.join(timeout=5)
    if thread.is_alive():
        raise TimeoutError("bounded storage sampler did not stop within 5 seconds")


def main() -> int:
    stage = pathlib.Path(os.environ["PROOF_STAGE"]).resolve(strict=True)
    evidence = stage / "evidence"
    runtime = pathlib.Path(os.environ["AGENT_RUNTIME_DIR"]).resolve(strict=True)
    if stage.is_symlink() or evidence.is_symlink() or runtime.is_symlink() or not evidence.is_dir():
        raise RuntimeError("stage, evidence, and private runtime must be real directories")
    if not (runtime / "tmp").is_dir() or (runtime / "tmp").is_symlink():
        raise RuntimeError("run_scoped did not create its private tmp directory")

    archive = stage / "source.tar"
    baseline = stage / "Cargo.lock.baseline"
    if digest(archive) != ARCHIVE_SHA or digest(baseline) != BASELINE_SHA:
        raise RuntimeError("frozen source archive or accepted baseline lock hash mismatch")
    for name in ("cargo", "rustc", "rustdoc"):
        tool = RUST / name
        if not tool.is_file() or tool.is_symlink():
            raise RuntimeError(f"required preinstalled direct tool is unavailable: {tool}")
    for name, binary in (("rustc", RUST / "rustc"), ("cargo", RUST / "cargo")):
        version = subprocess.run(
            [str(binary), "--version", "--verbose"], capture_output=True, text=True, timeout=5, check=True
        ).stdout
        if "1.93.0" not in version:
            raise RuntimeError(f"unexpected direct {name} toolchain: {version!r}")
        (evidence / f"{name}-version.txt").write_text(version, encoding="utf-8")

    source = runtime / "source"
    target = runtime / "target"
    cargo_home = runtime / "cargo-home"
    rustup_home = runtime / "rustup-home"
    for path in (source, cargo_home, rustup_home):
        path.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(source, filter="data")
    shutil.copy2(baseline, source / "Cargo.lock")
    initial = {relative: digest(source / relative) for relative in SOURCE_PATHS}
    source_manifest(evidence, source, "before-measurement")

    manifest = source / "Cargo.toml"
    if 'libc = { version = "=0.2.189", optional = true }' not in manifest.read_text(encoding="utf-8"):
        raise RuntimeError("source does not contain the reviewed exact optional libc edge")
    lock_path = source / "Cargo.lock"
    lock = lock_path.read_text(encoding="utf-8")
    start = lock.index('name = "rhai"\n')
    end = lock.index("[[package]]", start)
    package = lock[start:end]
    if ' "libc",\n' not in package:
        if ' "libm",\n' not in package:
            raise RuntimeError("baseline lock lacks the exact reviewed insertion anchor")
        lock_path.write_text(
            lock[:start] + package.replace(' "libm",\n', ' "libc",\n "libm",\n', 1) + lock[end:],
            encoding="utf-8",
        )
    if digest(lock_path) != EDGE_LOCK_SHA:
        raise RuntimeError("private libc-edge-only lock hash differs from the accepted resolution")
    shutil.copy2(lock_path, evidence / "Cargo.lock.private-final")

    env = dict(os.environ)
    env.update(
        {
            "CARGO_HOME": str(cargo_home),
            "CARGO_TARGET_DIR": str(target),
            "RUSTUP_HOME": str(rustup_home),
            "TMPDIR": str(runtime / "tmp"),
            "TMP": str(runtime / "tmp"),
            "TEMP": str(runtime / "tmp"),
            "CARGO_BUILD_JOBS": "2",
            "CARGO_INCREMENTAL": "0",
            "CARGO_PROFILE_DEV_DEBUG": "0",
            "CARGO_PROFILE_TEST_DEBUG": "0",
            "RUSTFLAGS": "-C debuginfo=0",
            "RUSTC": str(RUST / "rustc"),
            "RUSTDOC": str(RUST / "rustdoc"),
            "PATH": str(RUST) + os.pathsep + env.get("PATH", ""),
        }
    )
    for key in ("RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN", "CARGO_HOME_CONFIG"):
        env.pop(key, None)
    measurement_evidence = evidence / "measurements"
    measurement_evidence.mkdir()
    command = [
        sys.executable,
        str(stage / "measure-process-overhead.py"),
        "--source-dir",
        str(source),
        "--evidence-dir",
        str(measurement_evidence),
        "--source-revision",
        REVISION,
        "--source-archive-sha256",
        ARCHIVE_SHA,
    ]
    print(
        f"PRIVATE_RUNTIME {runtime}\nSOURCE_ARCHIVE revision={REVISION} sha256={ARCHIVE_SHA}"
        f"\nLOCK baseline_sha256={BASELINE_SHA} private_edge_sha256={EDGE_LOCK_SHA}"
        f"\nLIMITS outer_seconds=600 run_scoped_seconds=585 driver_seconds=580 cargo_seconds={MAX_CARGO_SECONDS}"
        " cargo_jobs=2 descendants=16 memory_policy_bytes=2147483648 sampled_storage_stop_kib=1572864"
        " storage_sampling_seconds=1 measurements=120 warmups=0 retries=0",
        flush=True,
    )
    wait_for_monitor_ready()
    started = time.monotonic()
    storage_stop = threading.Event()
    storage_failures: list[BaseException] = []
    storage_samples: list[int] = []
    storage_thread = threading.Thread(
        target=sampled_runtime_storage,
        args=(runtime, evidence, storage_stop, storage_failures, storage_samples),
        name="private-runtime-storage-sampler",
        daemon=True,
    )
    storage_thread.start()
    log_path = evidence / "measurement-launch.log"
    identities_path = evidence / "measurement-command-identities.tsv"
    with log_path.open("w", encoding="utf-8") as output, identities_path.open("w", encoding="utf-8") as identities:
        identities.write("label\tpid\tstart_ticks\tppid\tpgid\tcmdline\n")
        process = subprocess.Popen(
            command,
            cwd=stage,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=False,
        )
        try:
            try:
                start_ticks, ppid, pgid, cmdline = proc_start_ticks(process.pid)
            except (OSError, ValueError, IndexError) as error:
                raise RuntimeError("measurement driver identity disappeared before it could be recorded") from error
            identities.write(f"measurement-driver\t{process.pid}\t{start_ticks}\t{ppid}\t{pgid}\t{cmdline}\n")
            identities.flush()
            os.fsync(identities.fileno())
            while process.poll() is None:
                healthy, reason = monitor_health()
                if not healthy:
                    raise RuntimeError(f"process custody monitor failed during measurement: {reason}")
                if storage_failures:
                    raise RuntimeError("private runtime storage sampler failed") from storage_failures[0]
                if time.monotonic() - started > MAX_DRIVER_SECONDS:
                    raise TimeoutError("measurement driver exceeded its 580-second package limit")
                time.sleep(0.2)
            status = process.wait()
        except BaseException:
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            raise
        finally:
            stop_storage_sampler(storage_stop, storage_thread)

    if storage_failures:
        raise RuntimeError("private runtime storage sampler failed") from storage_failures[0]
    print(
        f"SAMPLED_PRIVATE_RUNTIME_STORAGE_MAX_KIB={max(storage_samples, default=0)}; "
        "du -sk approximately once per second; sampled maximum, not continuous peak",
        flush=True,
    )
    print(log_path.read_text(encoding="utf-8", errors="replace"), flush=True)
    if status != 0:
        raise RuntimeError(f"measurement driver exited with status {status}; no retry")
    if time.monotonic() - started > MAX_DRIVER_SECONDS:
        raise TimeoutError("measurement package exceeded its 580-second limit")
    source_manifest(evidence, source, "after-measurement")
    for relative, expected in initial.items():
        if digest(source / relative) != expected:
            raise RuntimeError(f"source path changed during measurement: {relative}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException as error:
        print(f"MEASUREMENT_PACKAGE_FAILURE {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise
