# Native2 collector-only custody correction

This correction repairs the consumer contract for the preserved Native2 stage. The frozen helper/proof input remains `61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53`; production sources, tests, observer, launcher, stage originals and Native2 proof were not changed.

`collect-originals.py` now reads periodic resource measurements from the exact `outer-evidence/outer.log` captured by the launcher. It binds the log bytes to the preserved stage inventory, requires one runtime banner matching the early runtime identity, and accepts only a nonempty, ordered stream of the helper's four fields before the successful outer status. It rejects malformed records and measurements at or above the existing storage/RSS/descendant/time limits. The custom proof exporter did not emit `resource-samples.jsonl`; no sidecar is fabricated or required.

Custody now accepts only the pinned logical and physical stage/scope paths. It checks the scoped supervisor and `run-scoped` command against `runner/tools/run_scoped.py`. Runtime identity must be one absent direct `agent-build-[a-z0-9]+` child of the exact scope after the explicit `/root`↔`/var/roothome` alias mapping. Green and RED fixture roots must match the exact Rust test directory name and observed host PID under that runtime's `tmp` directory, allowing only those same two root aliases. Existing ancestry, process identity, exact group census, package, source-pin, terminal absence, inventory and hash gates remain in place.

The complete `recipe-probes.py` run passed. Its full isolated CUSTODY interaction used the 53 exact sample lines from the preserved Native2 outer log after confirming its SHA-256 against the independent-readback manifest. The synthetic remainder used localized `/proc`, `ps`, stage and frozen-input boundaries. The whole CUSTODY program accepted the valid fixture and rejected empty, malformed, reversed and over-cap resource streams, the old scoped-supervisor relative path, a foreign fixture path, the empty managed group set and a foreign helper argv. It exercised canonical `/var/roothome` GREEN paths and lexical `/root` RED paths with the actual fixture naming scheme. The probe also independently checked the preserved Native2 runtime, runner argv and all four observed fixture-root aliases against the original manifest.

The preserved Native2 run remains RED `101/101` for direct and managed, GREEN `0/0` for direct and managed; its periodic sampled maxima are RSS `887404 KiB`, storage `732196 KiB`, and 7 descendants. Those are periodic sampled maxima, not continuous peaks. The Native2 observer/terminal evidence and original tree were not rerun or modified. No SSH, Cargo/compiler, native allocation, signal, remote mutation, or retirement was performed. The actual preserved tree still requires the affected independent whole-original CUSTODY review before any later retirement decision.

Validation: `python3 .scratch/all-tickets/linux-drop-false-523-evidence/recipe-probes.py` passed; `python3 -m py_compile` passed for both changed Python files; `git diff --check` passed. The patch-application and callback-coupling probes remained green.

Changed input hashes:

- `collect-originals.py`: `5b5ca03e58ca6e3749e4971d3f41e5fd2258913cd974e4544f1c2c835e8fa60e`
- `recipe-probes.py`: `8685c0bad43655cbd3f410c2d9a215810ace123f7d834e7c7816dbafa0759bfa`
- Frozen proof input: unchanged `61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53`

At freeze, this Native2 collector correction used approximately 14 minutes of active work (estimate; tool/token cost unavailable), within its 30-minute planning checkpoint. The earlier setup-repair estimate of 15/30 minutes and preceding package estimate of 56/60 minutes remain recorded; no estimate or history was reset. Native executions remain 2, with no new allocation.

## Post-retirement receipt correction

The observed Native2 cleanup completed its exact same-interpreter custody gate and retirement, but the separate post-retirement check failed because its embedded Python referenced `physical` without binding argument 3. Root independently confirmed fresh stage/scope/runtime absence, all 131 identities absent or reused, and all six groups empty; this correction did not repeat deletion and does not claim the lost Native2 removal receipt was saved.

The embedded check now binds the physical stage argument. Cleanup validates the retirement receipt against the exact preserved inventory and writes `remote-retirement.json` immediately before running that separate fresh check, so a later failure retains the receipt for future runs. `recipe-probes.py` executes the whole embedded postcheck with localized process-census boundaries, checks its valid absent-stage case, and rejects malformed identities, unknown process state, empty groups, a populated owned group, a surviving physical stage, and a runtime outside the exact scope. A local orchestration control injects postcheck failure after a valid deletion receipt and confirms that `remote-retirement.json` is durable while final `remote-cleanup.json` is not yet written.

The complete recipe probe, Python compilation and `git diff --check` passed. No SSH, Cargo, native run, signal, deletion, or production source change occurred. The preserved 69-file/7-directory original tree and tar were read-only inputs in earlier accepted checks and were untouched here. Frozen Native2 proof input and its pin remain unchanged.

Changed source hashes for this delta:

- `collect-originals.py`: `5e8775938865ba6c492035c4df2af693ead5256cb434de4e163991392637ec7c`
- `recipe-probes.py`: `c6ea62e1877b3c58427b4f95ac2797cf15391fe8a2a91f033f1a5c0afe7eee80`

This follow-up consumed approximately 14 minutes at the existing 30-minute consumer-correction checkpoint; the prior 14 minutes remain consumed, with no reset. Tool/token cost unavailable. Root owns independent state readback; this source-only package does not authorize or perform another retirement.
