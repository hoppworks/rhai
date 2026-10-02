# macOS tool-path and graph-boundary correction review

Frozen owner93ea424457b0a6045e1702df6fdf7b3a223cadef; integrated only its three
changed files, preserving unrelated owner work. OCR preview/rules retained beside
this review: two selected Python files reviewed2/2 (100%, skipped0); excluded
original pure-suite log manually inspected1/1. One combined affected review covers
build_environment, tool identity callers, graph preflight and existing source
confinement/locked graph evidence. No material source finding remains.

The private PATH now exposes six exact entrypoints only, while Cargo/Rust
executables remain absolute. Missing or divergent pinned links fail closed.
Existing private output/home/cache settings remain. This closes arbitrary PATH
fallback for ar/emcc at the source boundary; it does not prove dynamic helper
resolution or native descendant confinement. The retained Rust1.93 source audit
shows LlvmArchiveBuilderBuilder selects ArArchiveBuilder, whose Darwin archive
kind uses write_archive_to_stream; no external ar is required by that route.

The graph validator now requires every one of the26 reviewed candidate keys
in the metadata resolution, rejects additions and retains exact_compilation_units
false. Prior locked graph/source evidence remains the applicability baseline;
metadata is a conservative superset, not native unit selection.

Independent root pure replay passes68/68 in
macos-source-readiness-correction-root-pure.log. Independent baseline replay
loads only the frozen c3ac graph-validator function into the current test context:
the missing-candidate expectation fails exactly with RuntimeError not raised,
then the restored on-disk candidate passes in the full suite. Replay script and
original output are retained. Both scoped runners return0 and their exact owned
empty scopes are removed; no Cargo/native fixture/control/measurement runs.

Native ABI, actual tool/helper resolution, interruption controls, escaped-leaf
closure and live dual-stream capture remain open. Launch guardfalse, readiness
not-ready and process allocation84 are unchanged. This accepts source correction
only; it does not authorize measurement or claim ticket03/release completion.
