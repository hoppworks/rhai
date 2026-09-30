# Rhai host standard library

Vocabulary for the optional host-access packages being planned in this fork.

## Language

**Host standard library**:
The optional packages through which Rhai scripts access host facilities under
host-granted authority. This effort covers sys and an initial TCP net package.
_Avoid_: Using this term interchangeably with Rhai's existing StandardPackage.

**Reviewed script**:
A script whose behavior the host owner has examined and chosen to authorize.
Review does not turn the programs it invokes into isolated programs.
