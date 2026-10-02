# Root alias correction and integrated behavior package

Reviewed frozen source a2d7a8c2ace21e63c18b2e64cdce74e5e10afc94.
OCR selected two files; both reviewed, no exclusions. Preview/rules retained.

The original two native policy failures are the pre-correction RED. On workhorse
`/root` is a symlink to `var/roothome`, confirmed by fresh readlink. Existing
matching recognized configured and canonical root names but missed intermediate
spellings through the ancestor alias. The correction admits only candidates
whose full OS canonicalization equals the configured canonical root. It retains
capability-relative I/O, relative traversal checks, access levels and longest
root selection. No ambient target-file I/O or unrestricted fallback is added.
The regression checks alternate and canonical reads, denied write and independent
unchanged host bytes, plus traversal denial. No blocking source finding remains.
The existing root canonicalization/open race is unchanged by this correction;
the alias match does not bypass the retained directory authority.

The helper, staging, launcher, contract and pure pins were rechecked together:
only immutable source/archive identities, fresh owned scope names and five
additional required feature rows change. Existing custody, classifiers, target
summary verification and caps remain. Nine finite positive rows use one target
directory: the prior four plus sync, i32/no_float, unchecked,
no_index/sync/metadata and f32. Every row has real integration targets; no process
fixture/control is introduced. Archive551c03/v3lock2ba4 are pinned consistently.

Independent scoped pure replay passed all eight requirements; its exact empty
scope was retired. This is source readiness, not native acceptance. The intended
native run must prove the original policy failures restored, new public alias
regression and existing confinement, with original controls and all target
results. Preserve earlier unrelated net proof; do not claim a complete row if
any target fails or subsequent row remains unexecuted.

## Finite package and history

One new 600-second outer envelope, helper540/work510/export30, jobs2,
descendants16 and sampled RSS/storage2GiB with storage preemption1.5GiB.
Earlier launches retain 23.547s and35.655s (59.202s observed export elapsed;
1200s prior outer envelopes). With this envelope total allocation1800s; no
history reset. The first cause was classifier infrastructure; the second is
newly diagnosed policy behavior, zero failed corrections so far for that cause.
The expanded row plan is agent-selected: compiler matrix took64.206s and the
first baseline/control package35.655s, with measured sampled RSS below1GiB.
These justify one shared finite run rather than separate disposable builds.
The unchanged hard limits stop work if the larger feature matrix cannot fit.
No continuous peak or guaranteed completion within this envelope is inferred.
Native process count84 and Mac measurement guardfalse remain unchanged.
