# Native public custody build refresh (2026-10-28)

The 21 pinned Windows Runner/Driver source inputs match the prior accepted
BuildOnly inputs and the current repository bytes. Only the private nonce and
medium identity changed. The independent pre-execution review returned READY.
The exact source manifest is `175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276`.

One native `-PublicToolsOnly` BuildOnly ran on the owned RhaiTest VM under the
600-second build and 180-second serial-export bounds. The original COM1 segment
(`serial-original.bin`, SHA-256 `39a1be223ef96b2e4c4bcb34f074da8eab656dca5719b6d0ea40d0ce3d9639d8`)
contains 21 ordered frames and six hash-verified files. `original-export/project-readback.json`
records BuildOnly success, manifest `8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1`,
Runner `ff836aa0ce75807c817097327b60a2a9cd8741a0937cfb072bd17adefd994c7f`,
and Driver `090d29d3eb3642c6acb53f241c340cd7ef800f07977671039465ae140837e5a0`.
The guest build remains reusable only through its original 2026-10-30 12:00 UTC
expiry with matching inputs. This BuildOnly result is an execution prerequisite,
not Rhai product acceptance. Its exact host staging directory and ISO were
retired after original-export readback; the guest build retention is separate
(`../attempt14/host-cleanup-readback.json`).
