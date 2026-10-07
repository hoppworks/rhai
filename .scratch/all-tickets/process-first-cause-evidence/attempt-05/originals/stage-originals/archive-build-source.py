#!/usr/bin/env python3
"""Create a baseline Git archive with only the explicitly supplied test adapter."""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


SOURCE_PATH = "src/packages/sys/process/unix.rs"


def build_archive(repository: str, requested_revision: str, fixture_patch: Path) -> bytes:
    if fixture_patch.is_symlink() or not fixture_patch.is_file():
        raise SystemExit("fixture adapter patch must be a regular file")

    prefix = ["git", "-C", repository]
    revision = subprocess.check_output(
        prefix + ["rev-parse", "--verify", requested_revision + "^{commit}"], text=True
    ).strip()
    roots = subprocess.check_output(
        prefix + ["ls-tree", "-z", "--name-only", revision]
    ).split(b"\0")
    selected = [name.decode("utf-8") for name in roots if name and name != b".scratch"]
    if not {"Cargo.toml", "src", "tests"}.issubset(selected):
        raise SystemExit("missing required build source roots")

    original = subprocess.check_output(
        prefix + ["archive", "--format=tar", revision, "--", *selected]
    )
    source_member = None
    with tarfile.open(fileobj=io.BytesIO(original), mode="r:") as archive:
        matches = [member for member in archive.getmembers() if member.name == SOURCE_PATH]
        if len(matches) != 1 or not matches[0].isfile():
            raise SystemExit("baseline source archive does not contain one regular unix.rs")
        source_member = archive.extractfile(matches[0]).read()

    # Apply the frozen test-only adapter against the exact archive bytes. Production
    # behavior remains at the requested revision until the native baseline RED.
    with tempfile.TemporaryDirectory(prefix="rhai-first-cause-archive-") as temp_name:
        temp = Path(temp_name)
        source = temp / SOURCE_PATH
        source.parent.mkdir(parents=True)
        source.write_bytes(source_member)
        subprocess.run(
            ["git", "apply", "--check", str(fixture_patch.resolve())],
            cwd=temp,
            check=True,
        )
        subprocess.run(
            ["git", "apply", str(fixture_patch.resolve())], cwd=temp, check=True
        )
        adapted_source = source.read_bytes()

    output = io.BytesIO()
    found = 0
    with tarfile.open(fileobj=io.BytesIO(original), mode="r:") as archive:
        with tarfile.open(fileobj=output, mode="w:", format=tarfile.GNU_FORMAT) as result:
            for member in archive.getmembers():
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise SystemExit("unsafe path in Git archive: " + member.name)
                if member.name == SOURCE_PATH:
                    member.size = len(adapted_source)
                    result.addfile(member, io.BytesIO(adapted_source))
                    found += 1
                elif member.isfile():
                    result.addfile(member, archive.extractfile(member))
                else:
                    result.addfile(member)
    if found != 1:
        raise SystemExit("adapted source archive did not replace unix.rs exactly once")
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("revision")
    parser.add_argument("fixture_patch", type=Path)
    args = parser.parse_args()
    sys.stdout.buffer.write(build_archive(args.repository, args.revision, args.fixture_patch))


if __name__ == "__main__":
    main()
