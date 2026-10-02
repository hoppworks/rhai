# Source preparation receipts

## Frozen inputs and retained evidence

- Prescribed stage/private-runtime identifier: `current-darwin-sys-net-behavior-2f795ece-sampler2-20261002`; the helper rejects mismatched stage basenames or runtime scope.

- Test/source revision: `2f795ecee8edd6ddf348f382e5397cc6e348ad37`.
- Frozen source archive SHA-256: `43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b`.
- Compatible lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Original combined review and its seven receipts are retained at `/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/current-darwin-sys-net-source-review/`.
- The diagnostic association TDD RED is recorded in `current-darwin-sys-net-diagnostic-red.md`; it shows the old helper accepting a status-zero stderr-only EILSEQ case.
- Follow-up pure GREEN: `python3 .scratch/all-tickets/test-current-darwin-sys-net-behavior.py` passed all ten categories; complete captured output is `current-darwin-sys-net-diagnostic-green.stdout` (SHA-256 `c903ed462358f52217654aed54cf6a7aab76a18e5fe22e38c9ef4241e7f94684`). It covers stderr-only producer association with overlapping names, warning/test/result-shaped stderr isolation, partial observations and status-zero continuation/aggregate behavior, no-index unresolved coverage, conflicting inline producer, original stream-order malformed cases, and strict SESSION_ID/stage/scope positives and negatives.
- One test-fixture correction was made after an initial pure run showed that the inline-conflict synthetic transcript omitted its required Cargo target header; the transcript was corrected and the complete suite then passed. No native/build/Cargo/toolchain invocation occurred.
- The same combined affected recheck is retained at `/tmp/current-darwin-sys-net-affected-recheck.vmrgou7y/`; its `review.md`, `affected-regressions.py`, and `affected-receipts.json` document that the first F3/F4 repair in `8b9740de8e4493c78320293d3a07599672f22484` did not configure a root matching the system-prefix reads and concatenated stdout before stderr, making target association fail. This correction batch preserves that failed-correction history; no native allocation was made.
- Existing compiler/example readbacks apply only to those requirements. Existing Linux behavior proof remains Linux-only and unaffected.

## Consolidated affected correction

- F1/F2 are retained from `8b9740de8e4493c78320293d3a07599672f22484`: exact named outcomes/EILSEQ uncovered aggregation and fail-closed stable process/path cleanup remain unchanged.
- F3: the frozen cfg(macos) test now obtains the two system-prefix spellings from the exact owned `real` directory, configures `fs_root` with the `/var` spelling, and reads through both configured and prefix-alias forms. The fixture independently requires distinct strings, canonical equality to the exact real directory, denied write, and host byte readback. Native execution remains unverified.
- F4: raw stdout and stderr stay separate. The helper validates the exact stderr target header sequence, parses successive complete stdout libtest blocks, pairs each block with its corresponding header and exact selected named inventory, and labels the generated parser input `derived target order ... not captured cross-stream chronology`. Missing, duplicate, extra, incomplete or inventory-mismatched headers/blocks fail closed. Original stdout/stderr logs remain raw receipts. The EILSEQ diagnostic is separately consumed and associated only with the frozen producer `sys_fs/test_non_utf8_file_name`; stderr structure is never reparsed as libtest output. Unknown or conflicting association preserves observed outcomes but leaves completion uncertified and fails the row closed.

## RED/GREEN receipts

- F3 RED: the affected recheck’s `F3_configured_root_policy_mismatch` demonstrates that the previous configured ordinary `.../link` root did not lexically match either `/var/../../.../real/a.txt` or `/private/var/../../.../real/a.txt`. Its scope is explicitly a lexical policy model, not an Engine or OS run. F3 GREEN is the test-source correction in frozen revision `2f795ecee8edd6ddf348f382e5397cc6e348ad37`; the cfg(macos) assertions will verify the actual host canonicalization, Engine access, denied write, and readback only at future Darwin dispatch.
- F4 RED: the affected recheck’s `behavior-model.stdout`, `behavior-model.stderr`, and `behavior-model.parser-input.txt` use realistic separate Cargo streams and reproduce `test result appeared without a selected integration target` for stdout-then-stderr concatenation. A direct run of the baseline helper at `8b9740de8e4493c78320293d3a07599672f22484` against two complete blocks and two stderr headers reproduced the same error; ordered clean named output passed while EILSEQ and missing-name cases stayed uncovered. These results are saved in `current-darwin-sys-net-behavior-repair-red.json`. The new focused regression initially failed because `derive_target_order_parser_input` did not exist. F4 GREEN: `python3 .scratch/all-tickets/test-current-darwin-sys-net-behavior.py` now passes the separate-stream multi-target regression, with reversed selected-target order, missing/duplicate headers, extra/missing/inventory-mismatched blocks, clean ordered output, named-test negatives, and the EILSEQ uncovered case. Exact output is saved in `current-darwin-sys-net-behavior-repair-green.stdout`.
- Python syntax compilation and `git diff --check` pass. No Cargo, toolchain, native Engine/API/fixture, process query, control, or measurement85 was launched.

## Remaining acceptance

The nine Darwin behavior rows and five assertion controls remain pending actual Darwin source-run acceptance. `test_non_utf8_file_name` remains uncovered if its actual body returns early for EILSEQ. The source-only diagnostic association follow-up updates the helper, its regression suite, contract, and this preparation record atomically; it retains the original F1/F2/F3/F4 receipts and requires the same independent reviewer’s affected recheck. No native acceptance is claimed, and no push or merge was performed.
