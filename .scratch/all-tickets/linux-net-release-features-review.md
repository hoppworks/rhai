# Native Linux TCP feature acceptance review

Accepted immutable957fc6a70dd53c38e33f42ba4a15b39254a5a1a0, base243404c9, within original16:02:41–16:32:41UTC package. Proof-only; no production/test changes. Native workhorse Bazzite44/Rust1.97.1, exact source/lock identities recorded in ../linux-net-release-features/proof.md.

OCR delegate preview accounts for36 added artifacts: all3 reviewable drivers reviewed with resolved Python/default rules;33 excluded proof/log artifacts checked through proof, full canonical output, exact26-row status inventory, command headers, test counts and cleanup identities. No silent code skips. Matrix23 invocations plus corrected test produce148 successful tests; deliberate peer-byte101 reports actual[0,255,65] versus wrong[0,254,65]. Native feature rows metadata+serde, only_i32+no_float, unchecked, no_index+sync+metadata, f32_float, dedicated no_object3 and no_object metadata1 accepted. Ordinary zero-count no_object legacy suites were not used as evidence. Existing native baseline/sync/no_index proof reused unchanged.

Independent root SSH readback confirmed all135 recorded PIDs absent and private runtime absent; a subsequent exact query confirmed staging directory and uniquely owned hash temporary file absent. Sampled whole-runtime allocated maximum862,019,584bytes and socket descriptors6 are observed maxima, not continuous peaks or memory proof. Statuses, logs and counts agree.

Review finding: executed verify.py starts Cargo children in separate sessions, so outer scoped runner alone cannot guarantee their interruption cleanup. Historical executed driver retained accurately; proof explicitly prohibits reuse before ownership correction. This completed normal run and independent cleanup readback support the listed tests; no interrupted-run supervision acceptance is claimed. No unexpected test failure or production finding.

Combined sys/net, optionalMSRV1.77.2, Windows and production process remain open. Native TCP evidence is unaffected by the proposed cap-std non-WASM target table because net alone does not enable cap-std; future relevant source changes still require affected verification.
