"""Independent readback of saved native backend-failure originals."""
import hashlib
import json
import re
import sys
import zlib
from pathlib import Path, PureWindowsPath


def check(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


root = Path(sys.argv[1]).resolve()
binding = read(root / "binding.json")
medium = read(root / "media-readback.json")
check(digest(root / "Start.ps1") == binding["start_sha256"] == medium["files"]["Start.ps1"], "Start pin")
check(digest(root / "input-manifest.json") == binding["input_manifest_sha256"] == medium["files"]["input-manifest.json"], "manifest pin")
check(read(root / "input-manifest.json")["files"] == binding["source_files"], "source inventory")
for name, expected in binding["source_files"].items():
    check(digest(root / "input" / name) == expected == medium["files"]["input/" + name], "source pin: " + name)
check(len(medium["files"]) == 24, "media inventory")
dispatch = read(root / "dispatch.json")
mount = read(root / "host-mount-readback.json")
check(dispatch["enter_sent"] is True and dispatch["vm_uuid"] == mount["vm_uuid"] == binding["vm_uuid"], "host VM dispatch")
check(dispatch["media_sha256"] == mount["media_sha256"] == medium["sha256"], "host medium dispatch")
check(dispatch["start_sha256"] == binding["start_sha256"], "host Start dispatch")

cases = (
    ("hardlink", "backend-evidence-hardlink", "rhai-backend-evidence-0e6872acee8647af927c9023af25d331", "env-control-0e6872acee8647af927c9023af25d331", ["INTENT", "IDENTITY", "STAGED", "LIFECYCLE"], "evidence-hardlink", b"evidence must be withheld\r\n"),
    ("readonly", "backend-cleanup-readonly", "rhai-backend-cleanup-60e5e70f35564d85bf8f08f18e911f5d", "env-control-60e5e70f35564d85bf8f08f18e911f5d", ["INTENT", "IDENTITY", "STAGED", "LIFECYCLE", "EVIDENCE", "OUTCOME", "REMOVE_INTENT"], "cleanup-readonly", b"cleanup must remain incomplete\r\n"),
)
results = []
for tag, contract, identity, scope_leaf, grammar, mode, content in cases:
    export = root / (tag + "-export")
    receipt = read(root / (tag + "-export-readback.json"))
    observer = read(export / "observer.json")
    check(receipt["id"] == identity and observer["id"] == identity, tag + " identity")
    check(receipt["begin"]["accepted"] is True and receipt["end"]["accepted"] is True, tag + " serial acceptance")
    check(receipt["begin"]["exit"] == receipt["end"]["exit"] == observer["exit"] == 2, tag + " native negative exit")
    check(observer["contract"] == contract and observer["phase"] == "GREEN" and observer["accepted"] is True and not observer["failure"], tag + " contract")
    check(observer["backend_failure_accepted"] and observer["backend_failure_sensitivity"], tag + " wrong-expectation control")
    for key in ("fresh_host_record", "driver_launched", "exact_driver_exited", "pipes_drained", "process_disposed", "owned_executables_stopped"):
        check(observer[key] is True, tag + " " + key)
    for key in ("custody_pending", "observer_kill_used", "retained_driver_handles", "parent_environment_changed", "product_run"):
        check(observer[key] is False, tag + " " + key)
    check(observer["driver_elapsed_seconds"] < 30, tag + " Driver limit")
    check(PureWindowsPath(observer["scope"]).name == scope_leaf and PureWindowsPath(observer["run"]) == PureWindowsPath(observer["scope"]) / "run", tag + " scope")
    check(len(observer["channel_closure"]) == 2 and all(all(c[k] for k in ("reader_acquired", "writer_acquired", "reader_disposed", "writer_disposed", "eof")) and not c["error"] and not c["pending_task"] for c in observer["channel_closure"]), tag + " channels")
    check(len(receipt["files"]) <= 64 and sum(f["length"] for f in receipt["files"].values()) <= 16 * 1024 * 1024, tag + " export cap")
    for name, item in receipt["files"].items():
        path = export / name
        check(path.is_file() and path.stat().st_size == item["length"] and digest(path) == item["sha256"], tag + " file: " + name)
    check((export / "bootstrap.stderr").read_text().strip() == "driver failure: InvalidDataException: journal must contain the exact eight-record completion grammar", tag + " public Driver negative")
    check((export / "bootstrap.stdout").read_bytes() == b"", tag + " public Driver stdout")
    check(digest(export / "input/fixture.exe") == observer["fixture_sha256"], tag + " fixture binary")

    manifests = {}
    for component, binaries in (("build-readback", ("ScopedRunner.exe", "MonitorAcceptanceDriver.exe")), ("fixture-build-readback", ("PayloadFixture.exe",))):
        build = export / component
        build_observer = read(build / "build-observer.json")
        check(build_observer["accepted"] is True and build_observer["exit"] == 0 and build_observer["input_manifest_sha256"] == binding["input_manifest_sha256"], tag + " " + component + " build")
        check((build / "run-result.txt").read_text().startswith("BUILD_ONLY_PASS:"), tag + " " + component + " result")
        lines = (build / "build-manifest.txt").read_text().splitlines()
        check(lines[0] == "compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1", tag + " compiler")
        pins = {line[66:]: line[:64] for line in lines if re.fullmatch(r"[0-9a-f]{64}  .+", line)}
        for name in binaries:
            check("build/" + name in pins, tag + " missing binary pin " + name)
        manifests[component] = pins
    for name, expected in binding["source_files"].items():
        if name.endswith(".cs"):
            if "/fixtures/" not in name:
                check(manifests["build-readback"].get(name) == expected, tag + " public source: " + name)
            if name.endswith("PayloadFixture.cs") or name.endswith("NativeScopePolicyFixture.cs") or "/fixtures/" not in name:
                check(manifests["fixture-build-readback"].get(name) == expected, tag + " fixture source: " + name)
    for name in ("ScopedRunner.exe", "MonitorAcceptanceDriver.exe"):
        check(digest(export / "bin" / name) == observer["retained_binaries"][name] == manifests["build-readback"]["build/" + name], tag + " public binary")
    check(digest(export / "input/fixture.exe") == manifests["fixture-build-readback"]["build/PayloadFixture.exe"], tag + " fixture manifest")
    check(digest(export / "fixture-build-readback/build-manifest.txt") == observer["fixture_build_manifest_sha256"], tag + " fixture manifest hash")

    lines = (export / "payload-record.txt").read_text().splitlines()
    check(len(lines) == 7, tag + " payload record length")
    values = dict(line.split("=", 1) for line in lines)
    check(len(values) == 7 and values["mode"] == mode and values["job_member"] == "True", tag + " Job payload")
    check(re.fullmatch(r"[1-9][0-9]*", values["pid"]) and re.fullmatch(r"[1-9][0-9]*", values["creation_filetime_utc"]), tag + " actor generation")
    check(PureWindowsPath(values["runtime"]) == PureWindowsPath(observer["allocated_runtime"]), tag + " runtime identity")
    check(PureWindowsPath(values["runtime"]).parent == PureWindowsPath(observer["run"]), tag + " runtime parent")
    backend = observer["backend_failure_observed"]
    check(backend["mode"] == mode and PureWindowsPath(backend["runtime"]) == PureWindowsPath(values["runtime"]), tag + " backend observation")
    check(backend["payload_pid"] == int(values["pid"]) and backend["payload_creation"] == int(values["creation_filetime_utc"]) and backend["payload_actor_stopped"] and backend["runtime_retained"], tag + " actor/readback")
    run = export / "run"
    runtimes = list(run.glob("scoped-*"))
    journals = list(run.glob(".scoped-run-*.journal"))
    evidence = list(run.glob(".scoped-evidence-*"))
    check(len(runtimes) == len(journals) == len(evidence) == 1 and runtimes[0].is_dir(), tag + " exact retained roots")
    check(runtimes[0].name == PureWindowsPath(values["runtime"]).name, tag + " retained runtime")
    item_name = "evidence-hardlink-primary.txt" if tag == "hardlink" else "cleanup-readonly.txt"
    check(PureWindowsPath(values["file"]) == PureWindowsPath(values["runtime"]) / item_name, tag + " payload file path")
    check((runtimes[0] / item_name).read_bytes() == content, tag + " payload file contents")
    if tag == "hardlink":
        check(PureWindowsPath(values["link"]) == PureWindowsPath(values["runtime"]) / "evidence-hardlink-alias.txt", "hardlink path")
        check((runtimes[0] / "evidence-hardlink-alias.txt").read_bytes() == content, "hardlink readback")
    else:
        check(values["link"] == "", "readonly link field")

    data = journals[0].read_bytes()
    records = []
    while data:
        check(len(data) >= 15 and re.fullmatch(rb"[0-9A-F]{4}:[0-9A-F]{8}:", data[:14]), tag + " journal header")
        length = int(data[:4], 16)
        body = data[14:14 + length]
        check(len(body) == length and data[14 + length:15 + length] == b"\n" and zlib.crc32(body) == int(data[5:13], 16), tag + " journal CRC")
        records.append(body.decode("ascii").split("|"))
        data = data[15 + length:]
    check([row[0] for row in records] == grammar and len({row[1] for row in records}) == 1, tag + " negative journal grammar")
    check(records[0][1] == PureWindowsPath(values["runtime"]).name.removeprefix("scoped-"), tag + " invocation ID")
    check(PureWindowsPath(records[0][2]) == PureWindowsPath(values["runtime"]), tag + " journal runtime")
    check(records[3][2] == records[1][2] and "cleanup_confirmed=1" in records[3], tag + " Job closure")
    if tag == "hardlink":
        check(not list(evidence[0].glob("manifest.txt")), "hardlink incorrectly captured evidence")
    else:
        ev = dict(field.split("=", 1) for field in records[4][3:] if "=" in field)
        outcome = dict(field.split("=", 1) for field in records[5][3:] if "=" in field)
        check(ev["proof"] == "EXACT" and ev["exit"] == outcome["payload"] == "00000000", "readonly evidence exit")
        check(outcome["host_exported"] == outcome["runtime_removed"] == "0" and outcome["cleanup"] == "CONFIRMED", "readonly incomplete cleanup")
        for key in ("manifest", "stdout", "stderr"):
            check(digest(evidence[0] / {"manifest": "manifest.txt", "stdout": "stdout.log", "stderr": "stderr.log"}[key]).upper() == ev[key], "readonly evidence hash " + key)
        rows = (evidence[0] / "manifest.txt").read_text().splitlines()
        matches = [row.split("|") for row in rows if row.startswith("cleanup-readonly.txt|")]
        check(len(matches) == 1 and matches[0][1] == "F" and matches[0][5] == "1", "readonly attribute in native evidence")
        check(digest(evidence[0] / "runtime/cleanup-readonly.txt").upper() == matches[0][6], "readonly evidence file")
    results.append({"case": tag, "native_driver_exit": 2, "driver_seconds": observer["driver_elapsed_seconds"], "frames": receipt["frames"], "files": len(receipt["files"]), "journal_crc_records": len(records), "retained_runtime": values["runtime"], "payload_pid": int(values["pid"]), "payload_creation_filetime_utc": int(values["creation_filetime_utc"]), "wrong_expectation_rejected": True})

report = {"accepted_named_backend_failures": True, "source_base": binding["source_base"], "start_sha256": binding["start_sha256"], "medium_sha256": medium["sha256"], "results": results, "full_windows_gate": False, "native_rhai_cargo_started": False}
(root / "host-accepted-readback.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"accepted_named_backend_failures": True, "cases": [{k: item[k] for k in ("case", "frames", "files", "journal_crc_records", "driver_seconds")} for item in results]}))
