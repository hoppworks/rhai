"""Freeze the committed Rhai Cargo source and the accepted locked resolution."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

root = Path(__file__).resolve().parents[4]
output = Path(__file__).resolve().parent / "media-input"
selected = (
    "Cargo.toml", "Cargo.msrv.lock", "build.rs", "build.template", "README.md",
    "LICENSE-MIT.txt", "LICENSE-APACHE.txt", "src", "codegen", "tests",
    "examples", "benches",
)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
assert len(head) == 40
archive = subprocess.check_output(["git", "archive", "--format=tar", head,
                                   "--", *selected], cwd=root)
files = {}
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    for member in tar:
        if member.isdir():
            continue
        assert member.isfile() and not member.issym() and not member.islnk()
        assert not member.name.startswith("/") and ".." not in Path(member.name).parts
        assert member.size <= 64 * 1024 * 1024
        content = tar.extractfile(member).read()
        assert len(content) == member.size and member.name not in files
        files[member.name] = content
assert 400 <= len(files) < 2048
assert sum(len(content) for content in files.values()) < 512 * 1024 * 1024
lock_path = root / ".scratch/all-tickets/windows-rhai-native-20261028/attempt64/media-input/Cargo.lock"
lock = lock_path.read_bytes()
lock_hash = hashlib.sha256(lock).hexdigest()
assert lock_hash == "12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802"
assert not any(output.iterdir())
zip_path = output / "rhai-source.zip"
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                     compresslevel=6) as zipped:
    for name in sorted(files):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zipped.writestr(info, files[name], compress_type=zipfile.ZIP_DEFLATED,
                        compresslevel=6)
with zipfile.ZipFile(zip_path) as zipped:
    assert set(zipped.namelist()) == set(files)
    for name, content in files.items():
        assert zipped.read(name) == content
(output / "Cargo.lock").write_bytes(lock)
manifest = {
    "source_commit": head, "git_source_only": True,
    "selected_paths": selected, "file_count": len(files),
    "total_source_bytes": sum(len(content) for content in files.values()),
    "archive_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    "archive_bytes": zip_path.stat().st_size,
    "lock_sha256": lock_hash,
    "files": {name: {"bytes": len(content),
                     "sha256": hashlib.sha256(content).hexdigest()}
              for name, content in sorted(files.items())},
}
(output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({key: manifest[key] for key in (
    "source_commit", "file_count", "total_source_bytes", "archive_sha256",
    "archive_bytes", "lock_sha256")}, indent=2))
