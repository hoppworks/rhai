# X28 attempt 04 preparation stop

No Cargo command or test ran. Before compiling, the mutation script found two
identical release writes in different fixtures and aborted with
`assertion=1 release=2`. The mutation target was therefore ambiguous and was
rejected before any test effect. Runner status was 1, the exact scoped runtime
was retired, and no build cache or child was created. The correction is to scope
the release-suppression mutation to the `DirectDropFixture` implementation only.
