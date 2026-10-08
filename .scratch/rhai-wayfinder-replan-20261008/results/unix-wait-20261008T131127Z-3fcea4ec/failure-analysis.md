# Attempt01: fixture preparation error, not expected assertion RED

The build succeeded (37.94s). The selected test exited101 while public spawn
refused an explicitly supplied timeout option, before any child was launched or
intended exit assertion was reached. Current unix.rs spawn_child explicitly
rejects opts.contains_key("timeout"). This is the documented spawn contract;
Child.wait chooses its own bounded wait. Removed that option only in the new test.
No product defect or valid oracle RED is claimed. Original logs remain intact.
The runner restored the staged source and removed its private runtime; the
verified empty owned outer scope was retired. Attempt02 retains the same
archive, lock, compiler, profiles and function-specific control.
