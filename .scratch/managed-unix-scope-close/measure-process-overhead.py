#!/usr/bin/env python3
"""Run and summarize the bounded POSIX process-scope measurement test."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path


PAIRS = 30
STREAM_BYTES = 8 * 1024 * 1024
TOTAL_SAMPLES = PAIRS * 2 * 2
RUN_LIMIT_SECONDS = 580
CARGO_LIMIT_SECONDS = 540
SAMPLE_RE = re.compile(
    r"PROCESS_SCOPE_SAMPLE,(\d+),(DirectChild|Managed),(true|capture),(\d+),(\d+),(\d+),(\d+)"
)


def parse_samples(output: str) -> list[dict[str, int | str]]:
    samples = []
    for match in SAMPLE_RE.finditer(output):
        pair, scope, workload, latency_ns, stdout_bytes, stderr_bytes, retained = match.groups()
        samples.append(
            {
                "pair": int(pair),
                "scope": scope,
                "workload": workload,
                "latency_ns": int(latency_ns),
                "stdout_bytes": int(stdout_bytes),
                "stderr_bytes": int(stderr_bytes),
                "retained_fixture_children": int(retained),
            }
        )
    return samples


def validate_samples(samples: list[dict[str, int | str]]) -> None:
    expected = []
    for pair in range(PAIRS):
        scopes = ("DirectChild", "Managed") if pair % 2 == 0 else ("Managed", "DirectChild")
        workloads = ("true", "capture") if pair % 2 == 0 else ("capture", "true")
        expected.extend((pair, scope, workload) for scope in scopes for workload in workloads)
    observed = [
        (sample["pair"], sample["scope"], sample["workload"])
        for sample in samples
    ]
    if len(samples) != TOTAL_SAMPLES or observed != expected or len(set(observed)) != TOTAL_SAMPLES:
        raise ValueError(
            f"expected exactly {TOTAL_SAMPLES} unique pair/scope/workload records in alternating order; got {len(samples)}"
        )
    for sample in samples:
        if sample["latency_ns"] <= 0 or sample["retained_fixture_children"] != 0:
            raise ValueError(f"invalid timing or retained-child count: {sample}")
        expected_bytes = STREAM_BYTES if sample["workload"] == "capture" else 0
        if sample["stdout_bytes"] != expected_bytes or sample["stderr_bytes"] != expected_bytes:
            raise ValueError(f"unexpected stream byte count: {sample}")


def summarize(samples: list[dict[str, int | str]]) -> dict[str, object]:
    validate_samples(samples)
    groups: dict[str, dict[str, object]] = {}
    for scope in ("DirectChild", "Managed"):
        groups[scope] = {}
        for workload in ("true", "capture"):
            selected = [
                sample
                for sample in samples
                if sample["scope"] == scope and sample["workload"] == workload
            ]
            latencies = [int(sample["latency_ns"]) for sample in selected]
            entry: dict[str, object] = {
                "samples": len(selected),
                "latency_ns_raw": latencies,
                "latency_ns_median": statistics.median(latencies),
            }
            if workload == "capture":
                rates = [
                    (int(sample["stdout_bytes"]) + int(sample["stderr_bytes"]))
                    * 1_000_000_000
                    / int(sample["latency_ns"])
                    for sample in selected
                ]
                entry["captured_bytes_per_second_raw"] = rates
                entry["captured_bytes_per_second_median"] = statistics.median(rates)
                entry["captured_bytes_per_sample"] = 2 * STREAM_BYTES
            groups[scope][workload] = entry
    return {
        "profile": "POSIX descriptive process-scope overhead; no pass/fail threshold",
        "pairs_per_workload": PAIRS,
        "samples_total": TOTAL_SAMPLES,
        "warmups": 0,
        "stream_bytes_per_stream": STREAM_BYTES,
        "samples": groups,
        "retained_fixture_children_after_capture_calls": 0,
        "resource_count_scope": "The test proves its one recorded capture fixture PID is absent at each API return; package-wide process/group cleanup is measured independently by run_scoped.",
    }


def within(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath([str(path.resolve()), str(parent.resolve())]) == str(parent.resolve())
    except ValueError:
        return False


def write_samples(path: Path, samples: list[dict[str, int | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "pair",
                "scope",
                "workload",
                "latency_ns",
                "stdout_bytes",
                "stderr_bytes",
                "retained_fixture_children",
            ],
        )
        writer.writeheader()
        writer.writerows(samples)


def self_test() -> None:
    generated = []
    for pair in range(PAIRS):
        scopes = ("DirectChild", "Managed") if pair % 2 == 0 else ("Managed", "DirectChild")
        workloads = ("true", "capture") if pair % 2 == 0 else ("capture", "true")
        for scope in scopes:
            for workload in workloads:
                payload = STREAM_BYTES if workload == "capture" else 0
                generated.append(
                    f"PROCESS_SCOPE_SAMPLE,{pair},{scope},{workload},1000,{payload},{payload},0"
                )
    parsed = parse_samples("test output prefix\n" + "\n".join(generated))
    summary = summarize(parsed)
    assert summary["samples_total"] == 120
    assert summary["samples"]["Managed"]["capture"]["captured_bytes_per_sample"] == 16 * 1024 * 1024
    try:
        summarize(parsed[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError("missing sample must fail closed")
    reordered = list(parsed)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    try:
        summarize(reordered)
    except ValueError:
        return
    raise AssertionError("non-alternating sample order must fail closed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--source-revision")
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("measurement parser self-test passed")
        return 0

    if os.name != "posix":
        parser.error("this package measures POSIX process scopes only")
    runtime_value = os.environ.get("AGENT_RUNTIME_DIR")
    if (
        not runtime_value
        or args.source_dir is None
        or args.evidence_dir is None
        or not args.source_revision
        or not re.fullmatch(r"[0-9a-f]{40}", args.source_revision)
        or not args.source_archive_sha256
        or not re.fullmatch(r"[0-9a-f]{64}", args.source_archive_sha256)
    ):
        parser.error("requires AGENT_RUNTIME_DIR, private paths, a 40-hex source revision, and 64-hex source archive SHA-256")
    runtime = Path(runtime_value).resolve()
    source = args.source_dir.resolve()
    evidence = args.evidence_dir.resolve()
    if not within(source, runtime):
        parser.error("source copy must be inside AGENT_RUNTIME_DIR")
    if within(evidence, runtime):
        parser.error("evidence directory must survive outside AGENT_RUNTIME_DIR")
    for variable in ("CARGO_HOME", "CARGO_TARGET_DIR"):
        value = os.environ.get(variable)
        if not value or not within(Path(value), runtime):
            parser.error(f"{variable} must be inside AGENT_RUNTIME_DIR")
    if not (source / "Cargo.toml").is_file():
        parser.error("source copy has no Cargo.toml")
    evidence.mkdir(parents=True, exist_ok=True)
    if any(evidence.iterdir()):
        parser.error("evidence directory must be fresh and empty")

    started = time.monotonic()
    command = [
        "cargo",
        "test",
        "--features",
        "testing-environ,sys",
        "--test",
        "sys_process",
        "process_scope_overhead_measurement",
        "--",
        "--exact",
        "--ignored",
        "--nocapture",
        "--test-threads=1",
    ]
    command_env = dict(os.environ)
    command_env["CARGO_BUILD_JOBS"] = "2"
    try:
        result = subprocess.run(
            command,
            cwd=source,
            env=command_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=CARGO_LIMIT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode(errors="replace")
        (evidence / "cargo-output.log").write_text(partial, encoding="utf-8")
        (evidence / "cargo.status").write_text("timeout\n", encoding="ascii")
        raise SystemExit(f"cargo measurement exceeded {CARGO_LIMIT_SECONDS}s; no retry")

    output = result.stdout or ""
    (evidence / "cargo-output.log").write_text(output, encoding="utf-8")
    (evidence / "cargo.status").write_text(f"{result.returncode}\n", encoding="ascii")
    if result.returncode != 0:
        raise SystemExit(f"measurement command failed ({result.returncode}); no retry")
    if time.monotonic() - started > RUN_LIMIT_SECONDS:
        raise SystemExit(f"measurement package exceeded {RUN_LIMIT_SECONDS}s total")

    samples = parse_samples(output)
    summary = summarize(samples)
    write_samples(evidence / "raw-samples.csv", samples)
    try:
        rustc = subprocess.run(
            ["rustc", "--version", "--verbose"],
            check=True,
            text=True,
            capture_output=True,
            timeout=5,
        ).stdout
        cargo = subprocess.run(
            ["cargo", "--version"],
            check=True,
            text=True,
            capture_output=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError) as error:
        (evidence / "metadata-error.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        raise SystemExit("toolchain metadata collection failed; raw samples were preserved")
    metadata = {
        **summary,
        "os": platform.platform(),
        "machine": platform.machine(),
        "cargo": cargo,
        "rustc": rustc,
        "source_revision": args.source_revision,
        "source_archive_sha256": args.source_archive_sha256,
        "command": command,
        "elapsed_package_seconds": time.monotonic() - started,
        "resource_policy": {
            "outer_seconds": 600,
            "run_scoped_seconds": 585,
            "driver_seconds": RUN_LIMIT_SECONDS,
            "cargo_seconds": CARGO_LIMIT_SECONDS,
            "jobs": 2,
            "descendants": 16,
            "memory_policy_bytes": 2 * 1024 * 1024 * 1024,
            "sampled_storage_stop_kib": 1_572_864,
            "storage_sampling_seconds": 1,
        },
        "interpretation": "API-evaluation entry to completed Rhai report; excludes Engine construction and AST parsing. Spawn-to-first-byte is not exposed by this API.",
    }
    if time.monotonic() - started > RUN_LIMIT_SECONDS:
        raise SystemExit(f"measurement package exceeded {RUN_LIMIT_SECONDS}s total")
    (evidence / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
