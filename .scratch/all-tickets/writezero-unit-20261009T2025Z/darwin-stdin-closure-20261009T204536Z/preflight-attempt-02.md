# Darwin stdin run: evidence-copy preflight attempt 02

The second invocation staged the owned source copy and pinned lock, then stopped before the baseline source mutation and before Cargo because `cp` tried to overwrite the already archived read-only `sys-pipe.h` evidence file. No test ran. Runner exit was 1 and the exact private session scope was empty and retired.

Recovery: compare the resolved active SDK header byte-for-byte with the existing read-only evidence copy and reuse it only when identical. Preserve the original file mode and bytes.
