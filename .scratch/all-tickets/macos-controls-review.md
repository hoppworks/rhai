# macOS finite controls combined review

Baseline: 89bd29d4457720107efc5c38791745565f3eebd5.
Reviewed increment: 01a14793cf28c666bce033335daad773c3d0f605.
Preparation is not accepted yet. Native invocation count remains84 and the
measurement guard remains false.

OCR selected five source files; all five were reviewed, none skipped (100%).
The sixth file, the Markdown contract, was excluded as unsupported and read
directly. Review covers control selection, exact-child signal ownership,
readiness, workload separation, deadlines and final cleanup/readback.

Normal measurement mode is preserved. Setup uses frozen Git/tar commands;
build uses Cargo --no-run and returns before the measurement path. Managed is
explicitly unavailable. The controller cannot request a census-derived PID
signal or signal the custodian.

The finalizer still requires the measurement identity ledger for every case.
Setup exits before creating it; deadline explicitly disables monitoring; build
does not request monitoring. Each reaches read_live_identities, which rejects a
missing owned-process-ledger.json. These control paths therefore cannot close
their required runtime/receipt contract. Correct this in the responsible context
using explicit control evidence from registered records and complete native
readback, retaining every conservative closure condition.

Control success also needs the published matching readiness event and actual
consumed action, or the actual deadline reason. A negative child status alone
does not prove the declared intervention. The controller currently reports
deadline-stop-observed on EOF after readiness, without a final closure message;
early custodian failure must not produce that claim.

One correction batch was returned to the existing owner. Test the finalization
logic and readiness/closure rejection paths, with meaningful RED/restored proof.
The owner reported47 source and20 reader passes, but the original scoped output
was not located; that report is not independent acceptance. Root will replay the
frozen corrected package. No build or native control was launched by this review.
