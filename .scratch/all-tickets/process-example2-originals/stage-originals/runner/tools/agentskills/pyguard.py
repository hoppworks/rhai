"""The 3.11 re-exec guard (docs/agents/tooling-contract.md "Python").

Every tool under tools/ is Python stdlib only and needs Python 3.11+ for
tomllib. The MacBook's /usr/bin/python3 is 3.9, so every entry script calls
ensure() before importing anything that needs 3.11.
"""

from __future__ import annotations

import os
import shutil
import sys

CANDIDATES = ("python3.14", "python3.13", "python3.12", "python3.11")
FALLBACK_DIRS = ("/opt/homebrew/bin", os.path.expanduser("~/.local/bin"))


def _find_on_path() -> str | None:
    for name in CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _find_in_dir(directory: str) -> str | None:
    for name in CANDIDATES:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def ensure() -> None:
    """Re-exec argv[0] under a Python >= 3.11 interpreter if the current one is older.

    Search order: the current interpreter (no-op if already >= 3.11), then
    python3.14, python3.13, python3.12, python3.11 on PATH, then the same
    names under /opt/homebrew/bin, then under ~/.local/bin. Exits with a
    clear message if none is found.
    """
    if sys.version_info >= (3, 11):
        return

    interpreter = _find_on_path()
    if interpreter is None:
        for directory in FALLBACK_DIRS:
            interpreter = _find_in_dir(directory)
            if interpreter:
                break

    if interpreter is None:
        sys.stderr.write(
            "agentskills: this tool needs Python 3.11+ (tomllib); "
            "none of "
            + ", ".join(CANDIDATES)
            + " was found on PATH, in /opt/homebrew/bin, or in ~/.local/bin.\n"
        )
        sys.exit(1)

    os.execv(interpreter, [interpreter] + sys.argv)
