# Native Windows process attempt12: apparent RED, later invalidated

The targeted public test failed with `timeout_range_child_record=Some("pid=6096\n")`
and Cargo exit 101 after the baseline 7+3 GREEN tests. The Driver exited 0 in
123.141 seconds, removed its runtime and exported 211 ordered frames and 14
hash-verified original files. The serial log rotated during export; the exact
old-inode tail and new-inode prefix are joined and documented in
`serial-rotation-readback.json`. The source manifest is
`a7b6c7c9c6a7243aff406bfdb6f62dbb8006ad70e9e86a283a59dc0d02d2d251`;
the lock is `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.

Attempt13 proved the `1.0e19` timeout in this public test was representable
by the Windows `Instant`, so this intended RED was based on a false premise.
It is preserved as original evidence and consumed attempt history, not as a
valid product-defect reproduction or acceptance control. Attempt14 uses a
public value outside `Duration` and a separate synthetic overflow unit test.
