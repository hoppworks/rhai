# Stable Cargo source-candidate preflight review

Reviewed immutable increment `adbb95e00253b480e1ebbb49cec92addc791e87e`
against its parent and the accepted source-candidate audit. OCR preview selected
two files; both were reviewed under the resolved Python rules. Coverage: 2/2,
no skips. This is a source prerequisite review, not native acceptance.

## Blocking finding

`cargo_source_graph_argv` requests `--edges all`, including feature edges, but
`validate_cargo_source_graph` accepts only package rows (`name vversion`).
Cargo's documented feature output includes rows such as `log feature "serde"`.
The preflight would reject legitimate Cargo output before any build. The mocked
tests use package-only output and therefore miss the producer/parser mismatch.
Use explicit normal/build/dev package edges or implement a complete documented
feature-output parser. Preserve all package dependency types and proc macros;
add a regression covering the actual selected output contract.

Source: https://doc.rust-lang.org/cargo/commands/cargo-tree.html (edge kinds,
feature output, prefix formatting and approximate compilation equivalence).
The installed Cargo command documentation independently describes these kinds.
No Cargo, compiler, native fixture or measurement was launched during review.

## Other reviewed conclusions

Both graph queries route through the existing sole-custodian RPC. Only returned
stdout bytes are validated and hashed, with separate stderr. The metadata
resolution is checked against the reviewed 26-package build/proc-macro candidate
superset; the reviewed workspace build script/codegen sources are unchanged
between the source-audit baseline and frozen measurement source. The result
explicitly records that exact compilation units are unproven. Those conclusions
do not close dynamic tool/linker resolution or native custody/ABI/capture gates.

The finding was sent to the existing responsible owner as one source-only fix
batch. The launch guard stays false, native invocation count remains 84, and
invocation 85 is not allocated. Acceptance awaits corrected immutable source and
affected-test evidence; unrelated accepted proof is retained.

## Corrected increment acceptance

Rechecked `52fe92bc9608ca996aef80d922e6f776f21c1609` against the reviewed
baseline. Explicit `normal,build,dev` edges remove feature-only display rows
without dropping package dependency kinds or proc macros. The regression retains
fail-closed handling for unexpected documented feature rows. The blocking
finding is closed. Original owner edge-kinds RED shows the intended argv
mismatch, targeted GREEN and the full 63-test GREEN are retained under
`macos-graph-preflight-source-evidence-20261002/`. Root independently ran all
63 tests successfully against the integrated files through the existing scoped
runner; original output is `macos-stable-graph-root-test.log`. The runner exited
0 and its own exact empty scope was removed. No Cargo query/build/native
measurement ran. This accepts source-candidate preflight implementation only;
tool/linker resolution and native custody/ABI/live-stream proof remain open.
