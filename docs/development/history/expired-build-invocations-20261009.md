# Historical build invocation limits

Archived on 2026-10-09 from AGENTS.md. These completed invocation records preserve
evidence and consumed limits; they are not launch rules for new work. Consult current
project instructions and the actual run contract before launching.

## Workhorse finite build concurrency exception

For the single reviewed Linux OutputLimit invocation106 only, permit at most two
heavy runs on workhorse: the already active foreign Tauron G47 run_scoped group
1329949 (launcher1329948/start4447594, supervisor1329949/start4447596) and this
Session's one bounded Rhai run. Read-only capacity measurement on 2026-10-03
reported32 CPUs, MemAvailable79,580,232 KiB and
727,025,782,784 bytes free on the source/runtime filesystem. The observed foreign
Cargo/rustc RSS totaled about2,044,696 KiB; these are samples, not peaks.

Rhai retains600/585/540-second outer/runner/helper limits, two Cargo jobs,
16 descendants,1,572,864 KiB storage preemptive stop and2,097,152 KiB
storage/RSS hard caps. Before launch require no third heavy runner/compiler
group, at least16 GiB MemAvailable and16 GiB disk free. Preserve all foreign
processes, limits and resources. This finite exception expires when invocation106
is terminal; later work uses the global one-heavy-run default unless a new
measured exception is recorded. This is a workflow convention, not a lock.

Invocation 106 finished successfully on 2026-10-03. Independent read-back and
exact export retirement completed; its finite concurrency exception has expired.
New heavy runs use the global default unless separately justified by current
measurements. No foreign process was stopped or modified.

## Workhorse finite concurrency exception for escaped-pipe proof

For the single reviewed escaped-pipe invocation107, permit at most two heavy
runs: the existing foreign Tauron runner (launcher1408079/start4603295,
supervisor1408080/start4603297, compiler group1408080) and one bounded Rhai run.
Current read-only measurements report32 CPUs, load3.86/4.27/4.15,
MemAvailable78,299,404 KiB,717,200,211,968 bytes free, and sampled foreign
compiler RSS3,794,880 KiB. These are samples, not peak or reservation claims.

Rhai retains600/585/540-second outer/runner/helper bounds including30 seconds
for export, two Cargo jobs,16 descendants,1,572,864 KiB preemptive storage stop
and2,097,152 KiB hard RSS/storage limits. Require immediate no-third-heavy
runner/compiler group, exact current foreign identities and at least16 GiB
available RAM/disk before launch. If the foreign run exits, recheck the global
slot; a changed runner needs a fresh measured identity assessment. Never stop
or modify foreign processes. This project workflow exception expires at107
terminal completion; subsequent runs use the global default.

Invocation107 is terminal. Its finite concurrency exception has expired; no
foreign process was modified. A later invocation needs fresh slot/capacity checks.

## Workhorse finite concurrency exception for invocation108

For this single reviewed escaped-pipe invocation108 only permit at most two
heavy runs: foreign launcher1532705/start4776357 and supervisor1532709/start4776360
with compiler group1532709, plus this owned bounded Rhai run. Fresh measurement
reports 32 CPUs, MemAvailable78030992KiB, free725398978560bytes
and foreign compiler RSS sample3807908KiB (not peak).
Require immediately matching foreign identities, no third heavy group, at least
16GiB available RAM/disk and all13 frozen stage hashes. Retain600/585/540second
bounds including30second export reserve, two Cargo jobs,16descendants,
1572864KiB preemptive storage and2097152KiB hard RSS/storage limits. Never modify
foreign processes/resources. Exception expires at108 terminal; future default
is one heavy run. Workflow convention, not a lock or capacity reservation.

Invocation108 is terminal (infrastructure parser failure after control and base
regressions). Its finite exception has expired. Runtime and scope cleanup passed;
only the exact immutable diagnostic input/export stage remains until export
and retirement. No foreign process was modified. Future launches require fresh
measured slot/capacity checks; no exception transfers to109.

## Workhorse finite concurrency exception for invocation109

Permit only this one reviewed bounded109 run plus foreign launcher1683061/start4944420
and supervisor1683065/start4944422, compiler group1683065. Fresh measurement:
32CPU, MemAvailable79586836KiB, free728046215168bytes,
foreign compiler RSS sample1085476KiB (not peak).
Require immediate matching foreign identities/no thirdheavy,16GiB availableRAM
and disk,all13frozeninputhashes,scope/terminalabsent. Rhai600/585/540secondbounds
including30secondexportreserve,2jobs,16descendants,1572864KiB preemptstorage and
2097152KiB hardRSS/storage remain unchanged. No foreign process modified.
Exception expires109terminal; later runs defaultoneheavy with fresh checks.

Invocation109 is terminal0. Its finite exception has expired. All71 original
files and seven closure artifacts were exported and independently hash checked.
Exact owned stage/scope retirement and fresh group absence passed; no retained
109 resources and no foreign process modified. Future runs require fresh checks.

## Single corrected60048 example capacity exception

For only the prepared corrected60048 example invocation, allow two heavy runs:
foreign launcher3276320/start6852456 (PGID3276313), supervisor3276321/start6852459
(PGID3276321), and this bounded Rhai run. Fresh read-only workhorse measurement
on 2026-10-04 reports32 CPUs, MemAvailable78177216KiB, free519143673856bytes,
load4.58/6.87/7.71 and sampled foreign heavy RSS7293216KiB. Samples are neither
peaks nor reservations. No foreign process/resource may be changed.

Require immediate ten frozen input hashes, absent own prospective scope/terminal,
either a completely free slot or both exact foreign identities/argv and no third
runner/compiler group. All foreign Cargo/rustc entries must belong to3276321;
other heavy tools block launch. Require16GiB available RAM and disk and one-minute
load below16 on32 CPUs. Rhai retains2 Cargo jobs,600/585/540second outer/runner/
helper limits (including30second export reserve),16 descendants,1572864KiB
preemptive storage and2097152KiB hard RSS/storage caps. Use the independently
reviewed fixed finite-slot guard with explicit Python check=True before launcher.
This workflow exception expires at this invocation's terminal outcome; it does
not renew stopped stdin/native110, Darwin/Windows or any earlier exception.

The corrected60048 invocation is terminal1 on 2026-10-04 after about40seconds:
Cargo example compilation E0369 before behavior controls. Its single capacity
exception has expired. All49 original files are preserved; exact stage retirement
and independent102 PID/start, two-group and four-path absence checks passed.
No foreign process/resource changed; future heavy runs require fresh checks.
