"""Freeze the tracked Rhai Cargo source closure for the Windows custody control."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "attempt01"
SELECTED = (
    "Cargo.toml", "Cargo.msrv.lock", "build.rs", "build.template", "README.md",
    "LICENSE-MIT.txt", "LICENSE-APACHE.txt", "src", "codegen", "tests",
    "examples", "benches",
)


def git(*args):
    return subprocess.check_output(("git", *args), cwd=ROOT)


head = git("rev-parse", "HEAD").decode().strip()
paths = [Path(raw.decode()) for raw in git("ls-files", "-z", "--", *SELECTED).split(b"\0") if raw]
assert paths and len(paths) < 2048
files = {}
for relative in paths:
    full = ROOT / relative
    assert full.is_file() and not full.is_symlink(), relative
    data = full.read_bytes()
    assert len(data) <= 64 * 1024 * 1024, relative
    files[relative.as_posix()] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
assert sum(item["bytes"] for item in files.values()) < 512 * 1024 * 1024

OUT.mkdir(exist_ok=True)
archive = OUT / "rhai-source.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zip_out:
    for relative in paths:
        info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 10, 25, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zip_out.writestr(info, (ROOT / relative).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)

with zipfile.ZipFile(archive) as zip_in:
    assert set(zip_in.namelist()) == set(files)
    for name, item in files.items():
        assert hashlib.sha256(zip_in.read(name)).hexdigest() == item["sha256"]

manifest = {
    "source_commit": head,
    "selected_paths": SELECTED,
    "file_count": len(files),
    "total_source_bytes": sum(item["bytes"] for item in files.values()),
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "archive_bytes": archive.stat().st_size,
    "files": files,
}
(OUT / "source-manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
print(json.dumps({k: manifest[k] for k in ("source_commit", "file_count", "total_source_bytes", "archive_sha256", "archive_bytes")}, indent=2))
