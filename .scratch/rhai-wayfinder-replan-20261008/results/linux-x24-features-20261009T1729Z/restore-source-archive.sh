#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out="$here/attempt02/source.tar.gz"
tmp="$out.restore-$$"
test ! -e "$out"
trap 'rm -f "$tmp"' EXIT HUP INT TERM
cat "$here"/attempt02/source.tar.gz.part-* > "$tmp"
expected=ae84afaefe73f411d10b10d627f8d6dd9d0ceceeff8cc462c7031505105d8a80
if command -v sha256sum >/dev/null 2>&1; then
  printf '%s  %s\n' "$expected" "$tmp" | sha256sum -c -
else
  printf '%s  %s\n' "$expected" "$tmp" | shasum -a 256 -c -
fi
mv "$tmp" "$out"
trap - EXIT HUP INT TERM
