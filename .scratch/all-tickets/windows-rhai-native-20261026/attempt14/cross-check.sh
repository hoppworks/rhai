#!/bin/bash
set -euo pipefail

packet="$(cd "$(dirname "$0")" && pwd)"
source_root="$AGENT_RUNTIME_DIR/source"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$source_root" "$CARGO_HOME"

python3 - "$packet/media-input" "$source_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

media, root = map(Path, sys.argv[1:])
manifest = json.loads((media / "source-manifest.json").read_text())
with ZipFile(media / "rhai-source.zip") as archive:
    names = sorted(name for name in archive.namelist() if not name.endswith("/"))
    assert names == sorted(manifest["files"]), "source inventory differs"
    for name in names:
        path = Path(name)
        assert not path.is_absolute() and ".." not in path.parts, name
        data = archive.read(name)
        pin = manifest["files"][name]
        assert hashlib.sha256(data).hexdigest() == pin["sha256"], name
        assert len(data) == pin["bytes"], name
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
assert hashlib.sha256((media / "Cargo.lock").read_bytes()).hexdigest() == "12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802"
(root / "Cargo.lock").write_bytes((media / "Cargo.lock").read_bytes())
PY

cd "$source_root"
rustc +1.77.2 --version
cargo +1.77.2 --version
cargo +1.77.2 check --locked --tests --target x86_64-pc-windows-msvc --features testing-environ,sys,metadata --lib --test sys_process_windows
