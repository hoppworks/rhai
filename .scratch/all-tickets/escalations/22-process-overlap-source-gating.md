# Question

Determine the minimal safe final source correction for the process overlap
regression after two completed source corrections failed independent review.

# Why escalated

Initial457 observation gate rejected correct1111 and immediateexpect_err stopped
Timeout-first control before intendedcause assertion. cc329 corrected both but
added Linux/proc fixture without Linux test gates (failedcorrection1). b83 added
Linux gates but also gated shared record_field_pid, used by existing non-Linux
Unix tests (failedcorrection2). Global rules require fresh non-fork Expert and
one bounded follow-up. This is source-readiness cause history, no native launch.

# Context by reference

Root /Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery.
Writer /Users/hoppworks/projects/rhai/.worktrees/process-overlap-acceptance.
Read current global ~/.agents/AGENTS.md, root AGENTS.md, Expert template and
campaign escalation reference; confirm6830c49. Read root
.scratch/all-tickets/process-overlap-review.md, process-overlap-acceptance-brief.md
and immutable Git diff8c0ee4634355aee4e841b455461a7dd5aac2aa18..b83ffe431f76bd051312179e297e1dcc14a79ae4 for unix.rs, affected helper callers.
Relevant current shared helperrecord_field_pid at4185 and inherited pipe tests
at5267/5387; newly addedrecord_field_ticks and overlaptests near4405.
Do not read entire coordinatorhistory or unrelated stoppedpackages.

# Constraints and decisions

PublicEngine/realOS proof, bothDirect/Managed, sameactualexpired/readablepollstep,
OutputLimitwins, independentactualchildPID/start/PGID/readiness, cleanupbeforecause.
cfg(test) only instrumentation; no production behavior change or publicAPI.
NoDarwinclaim: LinuxgateonlyLinuxspecificnewwork, preserveexistingsharedhelper.
Do notbuild/SSH/launch/signals/cleanup/install/Gitmutation. Existing stdin/API21/
Darwin09/12/Windows02/13 paths remainstopped. Solefollowup cannotrenewhistory.

# Tried so far

Initial457, correctedcc329 (failed1), b83 (failed2), no nativeallocation.
Root froze/replaced own unacceptedsourcearchive:31bc26c8b79317800a458045bed8ff0d6712f1225267266937eb48fa1d4a15dd,
sourceSHA d4e09a1ccde117e0d7d81ba9cfa252984316f891851d2664c3bdb09994341c8b.
CombinedreviewExpert foundsharedhelpergatingdependency, sourceblocked, writer
notifiedstopRust. Independent concretehelper work maycontinue; its newinitial
shorttestnames --exact defect is harnesspreparation, no nativefailures.

# Deliverable

Write answer besidebrief22-process-overlap-source-gating.answer.md. Exactminimal
allowedsourcefix, affecteddependencycheck, whether oneboundedfollowup can close
source-readiness and explicit stopcriteria. Include findings beyond obviousgate
only when material. Return <=15lines pluspath. Do notapplyfixes.

# Budget

20minute active-work planningcheckpoint, finite one analysis, actualcostunknown.
One subsequent bounded sourcefollowup perhistory (30minplanningcheckpoint);
no source correction renewal if itfails independentreview. Nativehardbounds
600/585/540secs andresourcecaps preserved forlaterunallocated acceptance.
