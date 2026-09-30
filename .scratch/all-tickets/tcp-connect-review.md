# TCP connect foundation review

Reviewed candidate d03049bf with final-drop correction e139ecf4 and proof
qualification a89cb9b3. The deterministic OCR preview identified seven Rust/Cargo
files; all were reviewed against the resolved rules. Logs, state, proof and the
correction script were examined separately for acceptance and applicability.

Real Engine tests and independent loopback peer observations pass for `net` and
`net,sync` (four tests each). The wrong-EOF control fails at the intended peer
assertion. The final-drop test actually drops a Scope holding an unclosed stream,
then connects through another Engine sharing the package quota; both peers see EOF.
Default denial, endpoint mismatch, invalid ports, shared close, quota exhaustion
and failed-connect reservation release are covered. Earlier compilation and test
harness diagnostics are retained and are not accepted functional proof.

Independently checked Rust source whitespace, configured human commit authorship,
clean candidate tree, rustc 1.93.0/aarch64-apple-darwin and Darwin 27.0.0. Exact
accepted runtimes agent-build-r7cfllns and agent-build-6dmn3c22 are absent. Raw log
trailing blank lines are preserved; range-wide whitespace checking is not clean.
No retained peak-storage measurement exists, and the correction script omitted
an explicit runner timeout. These procedural gaps are disclosed; future launches
must enforce timeout and record storage. No resource-limit compliance claim is
inferred from the functional tests.

Accept this outgoing-connect foundation only. It does not close the entire net
ticket, listener/transfer contracts, combined sys regression gate, MSRV or native
Linux/Windows matrix. Unchanged sys production paths retain their existing proof.
Local integration is authorized by recorded workflow choices; no remote writes.
