# macOS overhead custody prerequisites

Status: **not launch-ready**. No native, Cargo, fixture, control, or measurement
command was launched for this source repair. Invocation count remains 82.

The harness now checks a source constant that is deliberately `False` before it
reads `macos-overhead-custody-readiness.json`, creates a runtime, or starts any
child. The current record is also deliberately incomplete. Setting the source
constant to `True` and changing the record to `reviewed-ready` is valid only after
every item below is proven from the frozen implementation and independently
reviewed; the record itself does not prove custody.

| Prerequisite | Current evidence | Status |
| --- | --- | --- |
| One sole spawner/reaper; per-command gate and live anchor; interruption registration; exact reaping | Current adapter starts a Python driver with `Popen`; that driver also uses `subprocess` for setup and Cargo. No sole custodian or anchored command gate exists. | Open |
| Direct Cargo execution and frozen parser reuse | Frozen driver invokes Cargo through `subprocess.run` and then separately invokes toolchain metadata commands. The macOS harness currently supervises that driver, not Cargo. | Open |
| Complete conservative escaped-leaf observation | Current `ps` ledger is sampled ancestry and `lstart` readback; it is not a complete Darwin process census and cannot authorize signaling by numeric PID. | Open |
| Darwin process-list ABI and installed-kernel semantics | SDK declarations were located for `proc_listallpids`, `proc_pidinfo`, and `proc_pidpath`; the interface is private and versioned. No matching installed-kernel semantic review or complete reader exists. | Open |
| Exact locked build-script/toolchain confinement | The locked set has 131 registry packages. A read-only audit found 46 package source directories missing from the existing shared cache. The available subset is not a complete audit; no source was fetched or installed. | Open |
| Pure interruption/registration/readback controls and independent frozen-source review | No such controls or review receipt exist for the proposed custodian. | Open |

Until these gates are closed, the inherited scripts must not be used for a
native launch. In particular, sampled resource values are not continuous
enforcement, direct Python-child reaping is not Cargo-tree custody, and
runtime retention after uncertain cleanup is not successful cleanup acceptance.

The remaining exact decision is whether to obtain and review every unavailable
locked build-script source and matching toolchain source under a separately
bounded source-only package, or to stop this launch path because confinement
cannot be established. This repair did not fetch dependencies or change shared
caches. Root must resolve that prerequisite before any launch authorization.
