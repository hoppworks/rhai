# Bounded reparse-probe ownership and interruption handling

One native run uses an owned Windows Driver/Job and the exact scope from
`binding.json`, with Driver/observer/export bounds of 180/185/180 seconds.
The test creates its own unique directory under the Driver's private temp
directory. Before making the junction, it writes `owner.marker` containing
`rhai-reparse-probe-v1` and logs the exact fixture root. Both junction source
and destination are children of this same root. The child is held through its
exact `std::process::Child` handle; timeout termination and polling are bounded.

On normal or assertion-panic cleanup, the test deletes the junction tag using
its own open no-follow handle, checks that the reparse attribute is absent,
closes handles, and only then permits ordinary fixture cleanup. An unknown child
state or failed tag removal retains the fixture instead. The existing scoped
runner's source bound in the accepted native build has SHA-256
`26b7468a0868271a555f6ed450212267b01d7d3fd0a8dd5b3fb51b01b7a05629` and
refuses an observed reparse point before recursive runtime disposition.

If the process is interrupted or cleanup remains unconfirmed, do not recursively
remove the scope. First retain and read the Driver, journal and exact fixture
path; prove the exact owned actors stopped and independently verify scope,
owner marker and path identity without following reparse points. Only then may
the exact owned `allowed` entry be queried and its reparse tag removed with
`fsutil reparsepoint query/delete`. Verify the tag is absent before retiring the
scope. Unknown identity, failed query, or unresolved custody means retain it.
No foreign path, active process, shared volume or original VM medium is reset.
