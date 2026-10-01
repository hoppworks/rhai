# Question and deliverable

Prepare the missing real-client driver for the Windows monitor native acceptance route. Implement source and focused regression fixtures; do not execute native Windows operations or claim native proof. Read existing Expert02 and accepted monitor contracts rather than inventing a second architecture.

# Context by reference

- Goal/state: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md
- Sole design answer: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md
- Source plan: /Users/hoppworks/projects/rhai-windows-scoped-runner/.scratch/windows-monitor-job-owner/next-execution-plan.md
- Source files: tools/windows-scoped-runner/MonitorTransport.cs, MonitorLeaseProtocol.cs, Program.cs, MonitorLaunchSpecification.cs and README.md in accepted checkpoint d9480102a7f1d0cc87a7c294e2898995ed98dfd0. Locate exact names with rg --files.

# Ownership and constraints

Create your own exact Git worktree and task/windows-real-client branch from d9480102. Never edit another owner worktree. Read project AGENTS.md. English deliverables, author/committer hoppworks <daniel@hoppworks.de>, no coauthors. Only approved hoppworks/rhai fork writes; root owns integration. No credentials, install, home/config, services/admin, VM actions, process creation tests or native runtime deletion. Source preparation and ordinary syntax checks only. Preserve existing Expert02 and cause history. Use source-only 30-minute planning checkpoint; report concrete progress/remaining work, no arbitrary approval gate.

# Acceptance

Driver must exercise the real --lease-client protocol, immutable specification and fresh challenge responses, retain a real client lifetime, expose finite deterministic disconnect/client-death/replay modes for native controls, independently read bounded outcome/evidence, and produce exact identity/exit/cleanup diagnostics. It must not label EOF/disconnect as successful protocol coverage. Reconcile monitor CREATE_BREAKAWAY_FROM_JOB against driver containment explicitly; do not grant payload breakaway. Existing source-fixture harness remains narrow and unchanged; stage a separate reviewed native-driver route with finite caps from the plan. Start with meaningful failing contract fixtures/source assertions for new behavior; no mocked seam may be called native evidence.

Pass files by path. Return touched paths/hashes, source-check results, acceptance map and remaining native gates. Do not commit/push until root source review; do not merge.
