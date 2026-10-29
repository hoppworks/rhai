# Independent combined review, attempt 03

The reviewer reloaded the current global and project rules and reviewed the
source-to-runtime command, original failure export, rotation capture, custody
and next diagnostic seam. This is a read-only review.

- Payload exit `0x55` is the sole CMD exit 85 guard, reached after `cd /d %~dp0`.
  `MonitorPayloadJob.cs` launches from the runtime root, whereas the guard
  compared the changed directory with `runtime\work`. Compilation did not start.
- `WindowsCustodyBackend.cs` retires `work` before snapshotting evidence. That
  explains why a file left only there is absent from a retained snapshot;
  attempt 02 still does not prove whether the linker created the file.
- For a correction, keep the launch directory explicit, put generated outputs
  under private `work`, check and execute the fresh probe with an observable
  marker, then copy bounded diagnostic outputs to the runtime root before
  work retirement. Recheck the export whitelist and hashes.
- The rotated capture has preflight inode/offset, stable old/new segments,
  ordered frames and per-file hashes. Journal and observer establish closed
  custody and removed runtime; guest screenshots show the exact scope absent.
  Host cleanup also needs a saved readback record (now `host-cleanup-readback.json`).
- **Claim:** valid bounded infrastructure failure with exact own-resource
  cleanup. No native SDK-link or Rhai product acceptance.
