# Question

How can the frozen Darwin acceptance helper associate separate Cargo stdout/stderr with exact test targets and fail closed on actual stderr-only EILSEQ early-return diagnostics, without inventing cross-stream chronology or discarding valid partial evidence?

# Why escalated

Two implemented F4 corrections failed independent affected review: 8b9740de concatenated stdout before stderr headers and failed normal parsing; 4c4a81e associates headers and blocks but computes coverage from parser_core excluding stderr diagnostics. The same reviewer reports an actual-stream EILSEQ false pass, contradicting previously accepted diagnostic rejection. No third direct patch is authorized on this unexamined route. This is the first cause-specific Expert escalation.

# Context by reference

- Root: /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai; AGENTS.md and .scratch/all-tickets/coordinator-state.md.
- Frozen source: /Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai at 4c4a81e0551f6e6d5c56112de7febda0101ce27f.
- Helper: .scratch/all-tickets/check-current-darwin-sys-net-behavior.py, positive_test_coverage and derive_target_order_parser_input, especially coverage computed from parser_core.
- Tests: .scratch/all-tickets/test-current-darwin-sys-net-behavior.py; actual macOS EILSEQ emission in tests/sys_fs.rs; named inventories and contract/source-prep in the same directory.
- Root initial and affected originals: .scratch/all-tickets/current-darwin-sys-net-source-review/ and affected-8b974/.
- Latest same-reviewer original report/reproduction: obtain its terminal path from the root before analysis if not available. Do not infer acceptance from owner GREEN categories.

# Constraints and decisions

Source-only independent Expert analysis. Read current global/project rules, relevant campaign repair guidance and current Expert role definition; report revision. No source edits, native process query, Cargo, toolchain/API/control/build launch, push or merge. Retain separate original streams and label derived association honestly. Fail closed on ambiguous or incomplete evidence. Do not weaken nine-row named acceptance, wrong controls, cleanup, F19 uncovered behavior or strict native requirements. Preserve production and unaffected Linux proof; F3 now independently reports matching configured root, awaiting terminal report. No new review pipeline or budget reset.

# Tried so far

Initial review: missing named inventory/EILSEQ early-return rejection and merged stream mismatch. First correction improved positive_test_coverage but stdout-then-stderr concat failed normal target association. Second correction validates stderr header sequence and pairs successive complete stdout libtest blocks; exact inventory checks pass, but diagnostics are appended only to parser_input and omitted from coverage. Eight pure categories GREEN miss realistic stderr-only diagnostic acceptance. No native launch occurred in either correction.

# Deliverable

Write 11-darwin-split-stream-coverage.answer.md beside this brief. Diagnose the exact evidence boundary; propose the smallest sound source correction and meaningful realistic multi-target stdout/stderr RED/GREEN cases, including unknown diagnostic association, multiple targets, clean output and stderr-only EILSEQ. Specify previously accepted conclusions invalidated and unchanged evidence reusable. Provide a bounded follow-up repair contract and stop criteria. Return at most 15 lines plus path.

# Budget

One fresh Expert analysis and one bounded follow-up repair for this cause; 30-minute active-work planning checkpoint, no native allocation or safety-cap revision. Preserve two failed implementation corrections and all prior source/native history. Stop this path on repeated failure without progress, contradictory remaining evidence or an uncovered decision; do not start a second Expert chain.
