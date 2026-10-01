# Native72 macOS process refresh — rejected acceptance

## Scope and immutable inputs

Actual invocation72 ran the immutable b801968d221a9f7baac592770d3ac7e2b315e8fd source archive ba60259b46c686db02d7f77d52674b34688189924ab7f2237dfecbfeaf9a812a on macOS27.0 arm64 with Rust/Cargo1.93.0. This is development-platform verification, not MSRV or release acceptance. Driver f716d6320ac7a13bc06e93a7e56cd5940f89f6917ef9973c9519148744986154 and wrapper46c4461dd9f539786e2afc14c409feca43b626550a9741376b9863da9edc6488 were prepared at c8e29b45.

## Observed result and classification

Attached execution44705 is terminal exit1. The first public test managed_run_closes_worker_after_leader_exit_and_preserves_sentinel returned a typed runtime SysError before reaching the intended false expected exit42 assertion. At tests/sys_process.rs:1043 the test prints only ErrorRuntime(type, position), hiding the ProcessCause/report. Cargo reported0 passed/1 failed/28 filtered; compilation17.41s and test0.13s. These reported durations do not establish total Cargo wall time. Owner20/public29 suites were not executed. This is an actual macOS acceptance failure of the candidate; the intentional wrong-expectation control was not established. Exact underlying cause remains unknown. No behavioral retry is justified without better diagnostic evidence.

Source restoration ran in finally: all six-path hashes match the original immutable inputs; Unix11f3c2f23bc91535f6519a9dac94f7558970e6e4992a9b5286de3f350f7aaf67 and tests08092b4a2d990b02d53a9d5d46818c10ca3a12138b9846cceeba653bb2310c8f. Missing subsequent suite logs caused wrapper cleanup_status1; this does not mean the private runtime remained.

## Originals and independent cleanup

Original evidence is in macos-process-refresh-evidence/: macos-process-refresh.qOlwz9 SHA2565f14f1697b039e594e3c659731c652aa4ceb0fe8170d5100a96b2ef91458ada2; its .cargo.wrong-expectation.log SHA2568bcba2acd9b6b23d4346eea3fcf5e5da1f0c46452622b953d860994ab5637f2a. Root independently queried all nine emitted/known PIDs43693,43702,43703,43721,44015,44017,44018,44019,44020: absent. Owned PGIDs43693/43702 have no current members. Exact private runtime /private/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-z9gj9kfp is absent. Original fixture cleanup also reports exact leader/worker/leaf/sentinel ESRCH. Readback is root-cleanup-readback.json. This verifies known identities/groups and runtime, not continuous inventory of every descendant. Maximum du sample250596KiB; sampling is not a continuous peak.

## Next action and retained history

Same responsible source context adds diagnostic-only typed SysError printing and freezes source before further bounded diagnosis. No new Expert chain or automatic unchanged native retry. Existing cause08 history and safety limits persist. Count72 is consumed; Linux next actual invocation73 only after final frozen and staged review. Accepted71 ordinary Linux/shared-safety scope remains reusable for unchanged production sources. Full process ticket/platform/MSRV/features/performance and main integration remain open.
