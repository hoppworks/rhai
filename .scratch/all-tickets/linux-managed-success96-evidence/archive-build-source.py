#!/usr/bin/env python3
"""Stream an immutable Git source archive without recursively embedding proof archives."""
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("revision")
    args = parser.parse_args()
    prefix = ["git", "-C", args.repository]
    revision = subprocess.check_output(prefix + ["rev-parse", "--verify", args.revision + "^{commit}"], text=True).strip()
    roots = subprocess.check_output(prefix + ["ls-tree", "-z", "--name-only", revision]).split(b"\0")
    # Proof and campaign state are supplied separately; every other tracked root stays.
    selected = [name.decode("utf-8") for name in roots if name and name != b".scratch"]
    if "Cargo.toml" not in selected or "src" not in selected or "tests" not in selected:
        raise SystemExit("missing required build source roots")
    subprocess.run(prefix + ["archive", "--format=tar", revision, "--", *selected], stdout=sys.stdout.buffer, check=True)


if __name__ == "__main__":
    main()
