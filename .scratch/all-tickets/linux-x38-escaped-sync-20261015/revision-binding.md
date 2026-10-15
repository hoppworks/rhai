# Revision binding

The test source archive is fork-main revision
`2a1fce7916e9d6e97404f3d68caaf646dc3077a9`. Each profile uses Cargo defaults,
its explicit feature list, and lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Current Unix source SHA-256 is
`2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`;
restored test source SHA-256 is
`9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe`.
The four RED receipts bind the corresponding single assertion inversion.

The prior accepted X38 unchecked source is revision
`9042ee19628e9794ff37d5814386406a894a0c0d`, with the same lock. Current
tracked-source diffs since that revision add only a test-only cfg on an unrelated
stdin test in `unix.rs`, two unrelated stdin-test cfgs, and the no_index scalar
test. The two selected X38 test functions are earlier and unchanged. The existing
reviewed base and unchecked rows therefore remain applicable; this package adds
only the two sync profile rows and does not rerun either accepted profile.
