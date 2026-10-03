#!/usr/bin/env python3
"""Apply the one reviewed process-feature unified diff with strict byte pins."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

PATCH_SHA256 = "5cf5d4533ca3adb99a9313e710b91f184bf5f2ee90ce2e215644fddf71b17693"
BASELINE_SHA256 = "379db748d4b84a60538d172059df1feafaa62b337eaf49c1178d3e6467d40c74"
PATCHED_SHA256 = "8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b"
TARGET = "tests/sys_process.rs"
HUNK = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:[^\n]*)\n?$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(patch: bytes, original: bytes) -> bytes:
    if sha(patch) != PATCH_SHA256:
        raise ValueError("reviewed process-feature patch SHA-256 mismatch")
    if sha(original) != BASELINE_SHA256:
        raise ValueError("baseline integration-test source SHA-256 mismatch")
    lines = patch.splitlines(keepends=True)
    if lines[:4] != [
        b"diff --git a/tests/sys_process.rs b/tests/sys_process.rs\n",
        b"index 96cdd0fb..6355c6b9 100644\n",
        b"--- a/tests/sys_process.rs\n",
        b"+++ b/tests/sys_process.rs\n",
    ]:
        raise ValueError("unexpected patch header or target")

    source = original.splitlines(keepends=True)
    out: list[bytes] = []
    src_pos = 0
    patch_pos = 4
    hunk_count = 0
    while patch_pos < len(lines):
        match = HUNK.match(lines[patch_pos])
        if not match:
            raise ValueError(f"unexpected patch record at line {patch_pos + 1}")
        old_start = int(match.group(1))
        old_count = int(match.group(2) or b"1")
        new_count = int(match.group(4) or b"1")
        hunk_start = max(0, old_start - 1)
        if hunk_start < src_pos or hunk_start > len(source):
            raise ValueError("patch hunk position is invalid or overlaps")
        out.extend(source[src_pos:hunk_start])
        src_pos = hunk_start
        old_seen = new_seen = 0
        patch_pos += 1
        while patch_pos < len(lines) and not lines[patch_pos].startswith(b"@@ "):
            record = lines[patch_pos]
            if record.startswith(b"\\ No newline at end of file"):
                raise ValueError("unexpected no-newline patch marker")
            if not record or record[:1] not in (b" ", b"+", b"-"):
                raise ValueError(f"invalid hunk record at patch line {patch_pos + 1}")
            kind, payload = record[:1], record[1:]
            if kind in (b" ", b"-"):
                if src_pos >= len(source) or source[src_pos] != payload:
                    raise ValueError(f"patch context mismatch in {TARGET} at source line {src_pos + 1}")
                src_pos += 1
                old_seen += 1
            if kind in (b" ", b"+"):
                out.append(payload)
                new_seen += 1
            patch_pos += 1
        if old_seen != old_count or new_seen != new_count:
            raise ValueError(f"hunk line counts differ: expected {old_count}/{new_count}, got {old_seen}/{new_seen}")
        hunk_count += 1
    if hunk_count == 0:
        raise ValueError("patch contains no hunks")
    out.extend(source[src_pos:])
    result = b"".join(out)
    if sha(result) != PATCHED_SHA256:
        raise ValueError(f"patched source SHA-256 mismatch: {sha(result)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--patch-file", required=True, type=Path)
    args = parser.parse_args()
    source_root = args.source_root.resolve(strict=True)
    target = source_root / TARGET
    if target.is_symlink() or not target.is_file() or target.resolve(strict=True).parent != (source_root / "tests").resolve(strict=True):
        raise ValueError("private source target is missing, symlinked, or outside source root")
    patched = apply(args.patch_file.read_bytes(), target.read_bytes())
    target.write_bytes(patched)
    print(f"strict_patch_applied=true target={TARGET} sha256={sha(patched)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"strict patch refused: {exc}", file=sys.stderr)
        raise SystemExit(1)
