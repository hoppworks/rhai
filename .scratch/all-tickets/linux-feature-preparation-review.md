# Linux current-feature compilation preparation review

The reviewed package prepares eleven positive compiler rows and one intentional
sys/no_object rejection against frozen source 1ca21e32 and compatible lock2ba4.
This is preparation acceptance only; no compiler, public Engine, or native
platform behavior has been accepted from this package yet.

OCR workspace preview selected four files: compiler helper, launcher, staging
script and interruption regression. All four were reviewed (100%, none skipped).
The contract was excluded by OCR's unsupported-extension rule and read directly.
Review includes the frozen source/lock/runner inputs, private environment, row
statuses and intentional diagnostic, deadlines/resources, export and cleanup.

One correction batch addressed interrupted export, a missing heredoc terminator,
the exported-evidence path, uncertain/malformed identity handling, waiting after
an interrupted Bash wait and unsafe numeric signaling of a nonchild helper.
The final launcher records a private interruption request, waits on its exact
runner child, and permits scope retirement only after successful process/runtime
readback. Passive process readback uses a five-second ps query limit.

Independent scoped replay is retained in linux-feature-source-evidence:
interruption stops work, export remains possible before the original deadline,
expired export is rejected, shell syntax and all three Python heredocs pass.
Removing the interrupted-export exception produced the intended InterruptedError
and status1; restoring it passed. Frozen input hashes stayed unchanged throughout.
The proof runtime and exact empty scope were independently confirmed removed.
This replay covers pure source boundaries, not actual remote interruption.

The authorized remote stage was created and independently read back: all eight
archive/lock/helper/contract/launcher/runner-package hashes match the local frozen
inputs. Compiler scope and outer evidence were absent. The compiler package has
not launched because the last live workhorse inventory still showed foreign
G41/r3 cargo-nextest work. Revalidate that slot before launching. Original caps
and native invocation count84 remain unchanged. No material source finding is
left open in this preparation batch; native and release acceptance remain open.
