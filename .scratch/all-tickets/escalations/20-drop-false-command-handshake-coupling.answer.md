# Live Cargo command / observer handshake coupling

**Verdict: a narrow callback-ordering correction can close the remaining recipe interaction in one bounded follow-up. Frozen772 is NOT READY. Publish the recorded Cargo identity during its command-start callback and start the GREEN observer only after that publication. Prove actual coupled direct and managed ACK timing before any native preparation is declared ready. This does not close native acceptance.**

Current instruction repository revision is independently confirmed as `6830c49ed962a3dc1937d72d0d182150bb4c935c`. Global and root project instructions, campaign/repair/escalation guidance, OCR review guidance, TDD and strict E2E guidance, roles.toml and the current Expert template were loaded. Writer HEAD independently equals `7721356ac8c2eaf5adff502b3a27cd7131c87509`. This analysis used local source reads, byte rehashes and read-only Python AST checks. No Cargo, SSH, native fixture, signals, staging, deletion, Git mutation or production edit occurred. The requested answer is the sole file written. No independent execution of the reviewer's coupled reproduction is claimed.

## Diagnosis and smallest safe correction

The pinned c542 helper's `run_command` creates Cargo with `Popen`, calls `record_process_identity('command:<label>', pid, process_identity(pid))`, then polls/waits for command completion. Its recorder preserves the identity row and flushes/fsyncs the TSV. The proof's interception currently calls that recorder and updates only a private `command_identity` dictionary. It assigns `observer_result['cargo_process_identity']` in `finally`, after the command returns. The live observer requires that identity before comparing the test host's PPID to the live Cargo PID/start and before writing ACK. A fixture held for ACK cannot make this completion-time publication satisfy its live prerequisite.

The772 affected review's actual coupled GREEN reproduction demonstrates the failure, including no ACK during the command and the specific incomplete-Cargo-identity error. Source/AST inspection independently confirms that the callback contains no publication to `observer_result`. Existing RED-only `run_case` evidence and standalone preseeded observer positives cannot establish the missing order.

Simply moving the dictionary assignment into the callback while leaving the observer running from before `Popen` would fix the reproduced schedule, but leaves an avoidable race: Cargo can create its request while the parent is still reading identity or fsyncing the original custody row. The observer currently treats absent Cargo identity as a terminal error. Resolve ordering at the driver rather than adding a retry policy to the observer:

1. Keep creation and fresh-empty checking of the per-case observer directory before command launch, and retain the environment variable pointing to it. Keep `thread = None` initially; do not start an observer at this point.
2. In `record_and_publish`, call the original recorder first. On the exact current `command:<label>` callback with a non-None identity, retain the separate command identity. For `handshake=True`, publish a complete copied identity to `observer_result['cargo_process_identity']`, then create/start the actual observer thread with the existing arguments. Use the outer `thread` via `nonlocal`. The pinned helper has one target callback per command; resource-sampler/other labels must not start or overwrite this observer.
3. Keep RED's command recording independent: `handshake=False` never starts an observer or publishes an observer handshake identity. Identity availability alone is neither ACK nor success.
4. Remove completion-time publication as the mechanism needed for GREEN. Keep existing `done.set()`, bounded join for a thread that actually started, copied handshake originals, partial JSON, exact Cargo result checks, ACK check, host-parent binding and actual terminal readback. Missing identity or original-record failure must remain a failing GREEN result with preserved available command/error evidence; never invent Cargo identity from the request or host.

This changes the proof driver and its regression probes, with transitive pin/report updates. The observer need not change. Do not relax its request grammar, exact request-byte echo, request re-read, PID/start/parent/group checks, challenge state, incomplete/error preservation or terminal closure. Starting after publication also supports a request already present when the callback finishes: it is still checked by the same actual observer while the command is active. No extra sleep, acceptance timeout or observer deadline extension is needed.

## Meaningful coupled regression

First add a failing regression against unchanged772 at the already authorized command-boundary seam. For each of direct and managed, invoke actual `run_case(handshake=True)` with actual `OBS.observe`. Substitute only the Cargo command boundary and OS process-table/census boundaries. Keep actual request parser, atomic ACK writer, filesystem challenge records, result persistence and actual terminal observer. Use emitter-shaped requests from the retained patch/schema evidence; do not preseed `cargo_process_identity`, replace `observe`, or fabricate `ack_written`/successful live receipts.

Within the command substitute, invoke the actual intercepted recorder for the exact target label with a complete Cargo identity. Create the valid request/challenge files while the substitute is still active. Wait with a finite deadline/event for the actual ACK and require its bytes equal the complete request plus `observer_ack=true\n`. Record/assert that ACK was present before the substitute returned and that the callback-supplied PID/start bound the independently modeled live Cargo and host parent. Only then write the exact successful named-test Cargo log and return. Switch modeled terminal state after ACK to absent identities/empty groups and remove only probe-owned fixture data, allowing actual terminal validation to run. Use synchronization or bounded polling; a fixed100ms sleep alone is not the assertion.

Add the adverse schedule too: arrange the valid request before invoking the identity callback, then call it while the command is active. Require the same exact ACK-before-return. This catches the spawn-to-recording race without an observer grace period. Validate record-before-publication ordering through the original recording hook, and confirm the hook is restored after success and failure. Keep probe runtime finite, use unique local fixtures and ensure observer threads terminate on every probe outcome.

| Regression/control | Required result |
|---|---|
| Unchanged772 actual coupled direct/managed GREEN | Intended failure: no live ACK, incomplete identity error; not a harness crash or accepted successful log alone |
| Corrected coupled direct/managed, request after callback and request before callback | Exact ACK while command remains active; successful actual run_case and terminal checks |
| Target identity None/missing; unrelated command label | No accepted handshake/ACK; GREEN rejected; ordinary available custody retained |
| Wrong recorded Cargo start or mismatched host PPID | Actual observer rejects; no ACK; partial/error evidence retained |
| Request bytes changed during validation | Existing exact-byte control still rejects without ACK |
| Actual RED run_case with ordinary command identity | Intended named101 assertion and RED marker/terminal checks succeed; no observer thread, live receipt, ACK or request |
| Existing later-member/terminal permission failures and isolated CUSTODY corruptions | Existing incomplete/error and fail-preserve behavior remains; no success receipt |

Preserve the finite existing producer, RED emitter, source/manifest/status corruption, whole isolated CUSTODY, exact groups/provenance and partial-evidence probes. Localized census/proc substitutions must be reported explicitly as synthetic wiring evidence. A sandbox failure before a check is infrastructure, not a meaningful RED or a completed product correction.

## Frozen dependencies and one follow-up

The immutable production revision remains `523608648dcae99bc0f6b46eaf2bb91fa4ecc752`. Independently rehashed current inputs match the review:

| Input | SHA256 at772 |
|---|---|
| Exact accepted base helper | `c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9` |
| Proof driver to correct | `27358b72926faeecab68c76294d0b715d247ac17755919a14f460817561dcb26` |
| Observer to preserve | `07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2` |
| Tests-only handshake patch to preserve | `78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd` |

Retain archive `998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b`, compatible lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, baseline test `5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb` and contract `5f26d4fd99bddda2fcd5f3a0ee863b361c930a69f915be4c9f8389bfadb072f5` as prescribed. Repin the corrected proof everywhere it is checked: stage, collector/consumer, configured root preflight and proposal/report. Regenerate/check the exact12-input manifest relationship, including unchanged launcher/scoped-runner dependencies. Record the probe's frozen hash/revision. Do not change a correct dependency merely to refresh a pin. Actual filenames are `drop-false-observer.py` and `recipe-probes.py` in the evidence directory; the brief's longer names refer to these inputs.

The existing Standard owns one consolidated follow-up on the same writer branch/worktree. Record cause `drop-false-command-handshake-coupling`, ad512 failed correction1,772 failed correction2, this first escalation20 and the answer path. Apply only the ordering/probe/pin batch above. Use the existing remaining approximately10 minutes to the60-minute TOTAL active-work planning checkpoint, retaining estimated50 consumed and earlier cumulative unknown. This is a checkpoint estimate, not60 new minutes or a hard cap. If useful progress reaches that checkpoint, the Coordinator may revise the estimate under the existing autonomous policy with the specific new evidence and cumulative use recorded; no history reset or new Expert chain. No new heavy/native allocation is granted.

Freeze one atomic scoped correction with the required configured human attribution; report hashes, actual elapsed use, failing regression and corrected/control outcomes, and gaps. Return it to the same combined reviewer for one affected delta recheck of area2, pins and potentially affected preservation. Retain the five closed areas and unchanged evidence; no additional broad review chain. Stop this path on contradictory evidence, repeated no-progress, a completed failed follow-up or actual hard limits. Preserve the cause history and report the remaining requirement once; changing the label or Session does not renew it.

## Remaining native acceptance

Recipe readiness after that focused recheck only permits the Coordinator to prepare the existing bounded native route. Strict acceptance still needs real Linux Rust1.77.2 Cargo direct and managed named RED/101 failures at the intended expectation with pre-assertion custody markers, restored GREEN/0 behavior with live exact ACK and independent Cargo/host/member binding, actual terminal fixture/PID/start/group absence, baseline test/manifests/lock restoration, original export/hash equality, fresh exact custody and conservative immediate/post-retirement checks plus independent readback of logical and physical stage, runtime and scope absence. Fresh slot/capacity and every final frozen pin must be checked before allocation. Unknown reads retain custody and block closure.

Native consumption remains0 here. Existing600/585/540-second limits, two jobs,16 descendants,1572864KiB preemptive and2097152KiB hard RSS/storage bounds are unchanged. Collector19/EA7 is not renewed. Stopped stdin/native110/Darwin/Windows histories remain stopped. Original523 production and previously valid proof remain applicable narrowly; no new native, release or overall-goal acceptance is claimed. Token/cost and earlier cumulative work remain unknown.
