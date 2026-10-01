# Question
How can the current production process verification harness run one coherent scoped native proof without another avoidable setup failure or escaping runner custody?

# Why escalated
At least two harness-level infrastructure failures: nested wrapper quoting SyntaxError, then sample_storage called before definition (NameError), with zsh readonly status preventing marker. Responsible context has been stopped from new launches. These are independent of production behavior; raw run3 succeeded. One fresh Expert review for this cause, no second chain.

# Context by reference
Read /Users/hoppworks/projects/rhai-all-tickets/AGENTS.md and .scratch/all-tickets/coordinator-state.md. Current harness: /Users/hoppworks/projects/rhai-process-unix-run/.scratch/process-unix-run/verify-harness.py. Responsible state and evidence beside it; current tests: /Users/hoppworks/projects/rhai-process-unix-run/tests/sys_process.rs. Runner: /Users/hoppworks/projects/agent-skills/tools/run_scoped.py. Inspect current source read-only; responsible agent can continue source fixes but launches paused.

# Constraints and decisions
Use your own /Users/hoppworks/projects/rhai-process-harness-review task/process-harness-review worktree for answer. Do not modify responsible files, launch builds/install/run native fixtures, mutate agent homes or inspect unrelated runtimes. Inherit runner process group; saved Python script instead of fragile shell quoting; private source/cache/target/tmp/lock;600s/jobs2/2GiB hard caps unchanged. Exact accepted lock and only direct rhai/libc edge. Full public sys_process cases plus report target, wrong expected byte control then restored pass. Literal argv/tool/source identity and exact owned runtime cleanup; sampled storage only, not peak. No public upstream writes.

# Tried so far
Expected initial public RED. Resolver setup errors corrected by accepted lock8bd35... with direct libc edge. Compiler E0061/E0505 corrected. Run3 raw real Engine/OS case GREEN, report7pass, wrong101/restoredpass. Run2 initial harness detached compiler group, no fixture ran; fixed inherited group. Runtime2 rkpxw522/run3 dd3x8va2 independently absent. Misattributed whzxsy69 is foreign/preserved. Added text/cwd/Engine-limit tests are unverified. Run4 setup NameError, exact runtime5vbjvz_t cleanup check pending. History preserved.

# Deliverable
Write .scratch/all-tickets/escalations/05-process-harness.answer.md in your own worktree with concise source-backed defects and smallest coherent correction/check route; no code edits. Check all variable/function definition order, mutable source capture, subprocess result handling, watchdog/cleanup ownership, storage sampler lifetime/error path, restored control and evidence export. Distinguish static proof from native proof. Return at most15lines plus absolute answer path.

# Budget
Read-only review checkpoint10minutes; no builds/install/native execution. One Expert and one bounded responsible follow-up for this harness cause. Preserve cumulative elapsed work and all actual safety caps.
