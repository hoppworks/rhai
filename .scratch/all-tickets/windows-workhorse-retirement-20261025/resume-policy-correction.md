# Actual entry-path diagnosis

The native completed-build continuation passed exact run/receipt/custody guards,
frozen control SHA, empty old parser RED, one ReadAllLines pin and fresh binary
hash. Calling the .ps1 pathname then failed with UnauthorizedAccess because this
interactive guest process disables script-file execution. No native control/Driver
was started and its absent scope was not consumed.

The bounded continuation changes only the final invocation to an in-process
ScriptBlock made from that same hash-pinned immutable control, as already used
for the outer Start entry. Original parameters, child scope, Driver bounds,
serial-export bounds and explicit returned status remain. The control reads no
PSCommandPath or PSScriptRoot. No policy/configuration/environment is changed.
The native build and preceding checks are reused; no compile is repeated.
