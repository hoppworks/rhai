# Compatibility and release proposal

Status: approved by the owner on 2026-09-30; implementation and strict release proof remain open.

## Platforms and Rust versions

- Core Rhai remains at Rust 1.66.0 and gains no mandatory OS dependency.
- Optional sys/net packages target Rust 1.77.2 and native Linux, macOS and Windows.
- sys/net require std; reject no_std and wasm explicitly.
- sys retains its accepted no_object incompatibility. Proposed net uses structured
  errors and ordinary handle methods and can support no_object if registration allows
  it; do not assume support without compile and script proof.
- Do not enable Actions or publish anything. Obtain native checks locally and on
  the already authorized workhorse/Windows environment.

## Bounded feature gates

Each package alone and combined, plus sync, no_index, metadata+serde,
only_i32+no_float, and unchecked. Check no_index+sync+metadata together because
type registration and handle sharing interact. Check f32_float duration bounds.
Check core minimum without either package and package minimum with both.
Negative checks must explain unsupported combinations rather than fail incidentally.
Resolve optional dependencies at their supported MSRV; record the exact lock used.

## Process API compatibility

Propose an additive ProcessScope enum (DirectChild default, Managed) and a
SysConfig::process_scope builder; scripts cannot downgrade host selection.
The existing SysError enum is non_exhaustive, but changing the payload of
OutputLimit(String), Timeout(String) or Io breaks Rust callers constructing them.
Retain those existing variants. Review a new Process error variant containing a
primary cause and immutable ProcessReport, with kind/io_kind preserving script
classification and an additive process getter. The proposal explicitly changes
which Rust variant future process failures use; no existing process API exists.
Captured bytes, completeness, exit and cleanup diagnostics belong to that report.

## Release acceptance

- All accepted behavior rows exercised through Engine and real OS fixtures.
- Independent host readback/peer observation and demonstrated assertion controls.
- Native POSIX and Windows cancellation/reaping scope prototypes before production
  mechanisms are accepted; cleanup failures and inherited pipes cannot be hidden.
- Windows scoped runner first proves interruption cleanup and owned resource isolation.
- Metadata/documentation and examples execute; streaming handle divergences explicit.
- No completion claim while promised native platforms or feature/MSRV gates lack proof.

## Owner decision

The owner accepted the recommended choices on 2026-09-30, prioritizing maximum
quality regardless of effort. This approves the concrete contract above, including
connect plus separately authorized listeners. It does not certify implementation,
relax verification, authorize remote publication or bypass native resource custody.

Negative file-read lengths must fail; resource limits remain enforced under unchecked.
