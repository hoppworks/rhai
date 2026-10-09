# Combined independent review — Ticket 03 stdin closure attempt

**Disposition: REJECTED on the Spec axis.** The temporary product change and run-path success test were removed. No product defect, GREEN acceptance, or Ticket 03 closure is claimed.

## Standards

**ACCEPT — no findings.** The change was localized and the test exercised the public Engine, real child processes, bounded readiness/release coordination, independent file readback, captured output, exit status, and direct-child reaping. The reviewer reloaded current project rules and memory before review. This axis does not determine whether the tested behavior matches the accepted contract.

## Spec

**REJECT — one blocking finding.** The accepted decision `.scratch/all-tickets/escalations/16-stdin-api-seam.answer.md` states that direct `run` and `run_raw` already retain pending-input `BrokenPipe` as `Io` with operation `write process stdin` (lines 17–24, 61–65). The genuinely missing behavior is in public `spawn`/shared `Child`, whose owner pump discards `BrokenPipe` (lines 19–21, 61–63). Ticket 03 requires input errors to be retained and owned cleanup to complete (`.scratch/stdlib-wayfinder/issues/03-process-contract.md`, lines 86–90 and acceptance table line 153). The patch instead converted direct-run `BrokenPipe` and `Ok(0)` into successful input closure, and the test asserted that success. Attempt02's observed `BrokenPipe` was therefore expected behavior; attempt05's RED/GREEN proves the inverted test oracle, not a product fix. `Ok(0)`/WriteZero is explicitly separate and remains open.

Evidence hashes and runtime binding were internally consistent: attempt05 used revision `ff3b25b0889c32e0e505517fc605d4b6cd2d5208`, lock SHA `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, Workhorse Linux x86_64, Rust/Cargo 1.77.2 and `testing-environ,sys`. Correct binding cannot repair the contract mismatch.

## Rule reload

Primary reviewer loaded project `AGENTS.md` SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`; global `~/.agents/AGENTS.md` was absent; memory index SHA-256 `6119ac79bb299052f8fc124465ab8a97da7e62c978f6c66dea5e3ba32aa53409`; `code-review` `09eb147f793e4647949edd32dbad278f0554dfb56e0d46b699cd4c2c55bf0357`; `build-efficiently` `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`; TDD `5505d25bbaa8fc14a79e4d20163936958992a2995b7f1dd1d6197edc9ed722e0`. Both reviewers performed read-only inspection; no build or test was run during review.
