# Affected invocation review —2026-10-25

PASS. Same SHA-guarded control text and named arguments are invoked as ScriptBlock.
Its param binding, child scope and global explicit return remain valid. No
PSScriptRoot, PSCommandPath or MyInvocation dependency exists; absolute parameters,
USERPROFILE and PSHOME supply the paths. No policy/config/environment modification,
Start re-entry or compile occurs. Prior exact build/receipt/parser/manifest/fresh
fixture guards passed in this same original console; those results remain valid.
No additional entry/context prerequisite found. Reviewer ran no guest/build/test.
