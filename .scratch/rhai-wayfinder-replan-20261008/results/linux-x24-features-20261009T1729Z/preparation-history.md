# X24 feature package preparation notes

The first attempt to create Workhorse's remote staging leaf failed because its parent evidence directory did not exist. The failure occurred in the `mkdir` staging command before `run_scoped.py`, session-scope creation, Cargo or tests. The parent and exact attempt01 leaf were then created with owner-only permissions; the same prepared package launched successfully. This is staging history, not a product or test result.
