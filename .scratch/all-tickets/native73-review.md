# macOS native73 diagnostic review

## Result and applicability

Rejected acceptance. Attached execution61601 terminated exit1. Source55e54ebd93a3dda931141d463c8cb12f5a2ea849/archivefb939f8b58ef5ec77c3b36cb3b5e1579f0e846869543dc3a89edfa8e2a746a5a adds typed error diagnostics and Linux-only fixtures; production b801 is unchanged. macOS27 arm64 Rust/Cargo1.93 development toolchain; no optional MSRV or release claim.

The selected public managed-run test failed at tests/sys_process.rs1668 before the intended exit0→42 assertion: ProcessCause::Io op="observe process group closure", PermissionDenied, EPERM. Its immutable report contains direct exit Code(0), both capture-complete flags true, timed_out false and no cleanup diagnostics. This identifies passive group observation as the failing operation. It does not reveal remaining group membership or establish quiescence. Cargo outer0 passed/1 failed/28 filtered; owner20/full public29 never executed. The control is not an informative wrong-expectation RED.

## Binding and restoration

Driver SHA2525b9255ef20b2bfb304276f1a322221ec7a2d8c3d44bad3167055e3ac8e9b4; wrapper46c4461dd9f539786e2afc14c409feca43b626550a9741376b9863da9edc6488; global runner9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d. Baseline8bd35d7d and edge2ba4b3a lock bindings checked by driver. Finally restoration emits six matching source path hashes, including production Unix11f3c2f23bc91535f6519a9dac94f7558970e6e4992a9b5286de3f350f7aaf67 and tests0d20b73d7823b21d9b9ce4ec6f0d53c13ae388275fb6650871517ff0fb6a58d7. Only the private overlay was changed.

Original wrapper/driver evidence macos-process-refresh-evidence/macos-process-refresh.B3sAtB SHAacba590a300494dc0e08ae789b39269e9705f6c8112d61eeaa059723ffb515b3; separate original Cargo log .B3sAtB.cargo.wrong-expectation.log SHA79ced691fb0d17dfde9f5f0de3971624fb97d258626464bb435f68a42511ed43. Root independently read the failure/restoration and recalculated these hashes.

## Cleanup and limits

Wrapper50849/PGID50849, supervisor50860/PGID50860, driver50861, Cargo50877, executable51262, sentinel51264, leader51265, worker51266, leaf51267. Root independent readback confirms all nine absent, both owned groups have no current members, exact /private/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-was5icho absent. Fixture receipts also show leader/worker/leaf/sentinel ESRCH. Receipt native73-root-cleanup-readback.json. These checks cover known identities and groups, not continuous descendant inventory. Wrapper runner/cleanup status1 reflects missing later intended logs, not a surviving runtime.

Original package caps scoped600s/Cargo540s/jobs2 and sampled stop1572864KiB remain unchanged. Actual monotonic Cargo16.640s; build15.55s/test0.13s are separate values. Sample maximum250668KiB is not continuous peak. Invocation73 consumed; known69–71+73 Cargo106.420s excludes unavailable72 wall. Preserve prior counts/history.

## Next action

Source-level Darwin diagnosis with exact native API error semantics before behavior changes. No generic EPERM-to-success rule, blind repeated build, new Expert chain or main merge. Linux held-zombie diagnostic74 follows independent frozen/staged review; it is not general normal-completion acceptance. All final process/platform/MSRV/feature/performance/release gates remain open.
