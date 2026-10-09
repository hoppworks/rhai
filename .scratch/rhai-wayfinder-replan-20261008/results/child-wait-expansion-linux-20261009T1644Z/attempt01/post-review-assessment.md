# Independent-review classification

The attempt01 GREEN is valid for the baseline source: source SHA, accepted lock, features, Rust/Cargo 1.77.2, Linux target and exact selector are recorded. It covers both decoded-expansion cases, cloned/repeated waits, exact raw capture, independent child record and ESRCH.

The attempt01 RED is **not** an acceptance control. Its injected unconditional `assert!(false)` only showed the selector reached the inserted panic; it did not establish sensitivity to a wrong behavioral expectation. This finding came from the combined independent review. The failure remains preserved as review history, not a product defect or accepted RED.

Attempt02 supplies the corrected RED by flipping only the expected first raw byte in the no-primary case. It failed at the real `wait must retain exact raw bytes` assertion with status 101. The source was restored and its SHA matches the baseline. That corrected RED shares all relevant inputs with the valid attempt01 GREEN, which is reused without another GREEN build or test.
