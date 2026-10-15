# Revision binding

The source copy came from fork-main revision
`eee64f0f832f673ed60ae01ebf4ecca75d2a75fd`. Both profiles used Cargo defaults
plus their listed features and preserved lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Current Unix process source SHA-256:
`2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`.
Restored test source SHA-256:
`9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe`.
For both RED runs only the public `killed_report` expectation was inverted;
its marked panic was reached after the independent lifecycle readbacks. The
four source-hash receipts preserve RED and restored GREEN identities.

Related accepted checked and unchecked non-sync rows are bound separately in
`.scratch/all-tickets/linux-x34-kill-base-20261015/revision-binding.md` and
`.scratch/all-tickets/linux-x34-kill-unchecked-20261015/revision-binding.md`.
