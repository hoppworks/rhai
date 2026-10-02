# Xcode PATH confinement source evidence

The source change adds a private runtime `tool-bin` with links only for pinned
Xcode `cc`, `clang`, `ld`, and `dsymutil`. Pure tests verify its contents and
PATH position, exact identity-probe argv, and adapter allowlist. No Cargo,
compiler, Xcode tool, native API, fixture, control, or measurement was run.

- `tool-path-red.log`: original failing check; PATH selected `/usr/bin` before
  the Xcode tool directory.
- `private-shim-red.log`: failing check after tightening the desired contract
  to a private shim directory.
- `private-shim-targeted-green2.log`: final focused source checks, 2/2 passed.
- `full-suite-private-shim.log`: final source suite, 64/64 passed.
- `full-suite.log` and `tool-path-targeted-green.log`: passing checks for the
  intermediate direct-Xcode-PATH version, retained as history. The private
  shim implementation supersedes that version.
- `private-shim-targeted-green.log`: test setup error because assertions ran
  after its temporary directory closed; corrected in `private-shim-targeted-green2.log`.

The launch guard remains false. Dynamic runtime selection is still unverified;
`ar` remains on the preexisting `/usr/bin` fallback and has no direct identity
probe. Managed live dual-stream readiness and native Darwin reader behavior also
remain unverified.
