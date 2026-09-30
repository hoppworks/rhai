# File documentation and example acceptance

Accepted b9225862e05244acd1d42de9060ee2d785d04524 on task/file-handle-docs.
OCR preview selected Cargo.toml and examples/sys.rs; both reviewed with respective
rules, zero skips. README and CHANGELOG excluded by extension, manually reviewed.
One gated Cargo example adds no dependencies/default features/library changes.
Default-core library graph is unchanged, so prior core-lib proof still applies;
final release matrix remains open. Documentation follows accepted nine modes,
shared cursor/drop lifetime, actual-byte/EOF/UTF-8 behavior, host and Engine caps,
no_index omission, and separates whole-file reads. Local source link avoids
claiming an unpublished upstream API is documented on latest docs.rs.

Real macOS example runs under sys and sys,no_index return Rhai and independently
read Rhaiting data from the full host file. Deliberate wrong host expectation fails
at examples/sys.rs75 with actual Rhaiting data versus wrong payload, exit101;
restored source passes. Temporary directory uniquely created and owned by guard,
error paths release it, scoped source/build/cache/fixtures isolated. Coordinator
independently confirmed exact runtime agent-build-6o4bxcjz absent. Target end size
723268KiB is not total runtime or peak; missing storage measurement is disclosed.
Original13:21:01–13:51:01UTC window retained; no redundant builds for docs-only fixes.
Proof moved without duplication to ../file-handle-docs/ after verified merge/push.
Author and committer both verified lowercase hoppworks with configured email.
Native/MSRV/release matrix gates remain open; this closes phase4 docs/example only.
