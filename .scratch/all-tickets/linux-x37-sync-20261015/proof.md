# Linux X37 final-clone drop proof: checked sync profile (2026-10-15)

## Scope and bound inputs

This proof covers only
managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not under
testing-environ,sys,sync with unchecked disabled. Host: lllm Linux x86_64,
Bazzite 44; Rust/Cargo 1.77.2; default profile; integrated fork-main revision
f6089906d586b038800e2649e01c88f7074986be.

The same X37 selector already has reviewed Linux rows under testing-environ,sys,
testing-environ,sys,unchecked, and testing-environ,sys,sync,unchecked. This adds
the missing checked sync row only. It does not close other X37 selectors,
platforms or Ticket03/A-F.

The private source copy came from git archive HEAD and the preserved X35 lock
fixture. Lock SHA-256:
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
Cargo.toml SHA-256:
cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
Unix process source SHA-256:
2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
Restored test source SHA-256:
9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.

## Results and lifecycle observations

One scoped runner invocation used an absent owned session scope, absolute
TMPDIR, private source/Cargo home/target below AGENT_RUNTIME_DIR, one Cargo
job and a 900-second bound. The assertion-sensitivity RED took 40.520 seconds
including compilation and exited Cargo 101 at the deliberately inverted
sentinel-live assertion. Before that assertion, output recorded nonfinal-drop
liveness for leader/worker/leaf, final-drop ESRCH for all three managed members,
and the unrelated sentinel still live. Restored GREEN took 2.132 seconds and
passed 1/1 with the same observations. The test also asserts exact sentinel
absence after its explicit fixture cleanup. Outer runner status was 0.

Preflight showed 95 GiB available RAM, 672 GiB free disk, 32 CPUs, and an
unrelated one-job Tauron build. This Rhai run used one job and left Tauron
untouched. The exact private runtime and owned session scope were removed; no
cache was retained. Full environment, capacity snapshots, commands, hashes,
and raw test outputs are in attempt-01/.

## Review and limits

Combined independent review: PASS; see attempt-01/combined-review.md. Acceptance remains limited to this
named Linux checked sync selector and revision.
