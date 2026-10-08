# Native bootstrap failure, allocation 01

The corrected whole-script console invocation reached the native bootstrap and
its nested setup-failure control. No C# compiler was started. The complete
invocation-bound serial export contains nine files whose lengths/hashes were
independently verified. The nested child wrote the intended setup exception,
its own PID7764 and PING child PID3184 before teardown. The outer bootstrap
rejected `Setup-failure control unexpectedly succeeded.` Its observer received
exit0 but accepted=false because no post-disposition result existed. Neither
zero is accepted as successful work.

The selected source's failure finally closes a kill-on-close job containing its
own controller, without supplying a failure exit. These original outputs show
zero status for that path despite preserved failures. This is a custody-tool
status defect, not a Rhai backend assertion or proof of a leaked PING process.
The failed observer and original logs remain retained in bootstrap-export and
bootstrap-serial-original.txt; the corresponding guest session is preserved.

Repair only failure disposition: explicitly terminate the owned job with
nonzero E0000003, retaining the exact job/watchdog owner through process death.
If termination unexpectedly returns without terminating the owner, FailFast.
Success still requires exact owner-only accounting, clear/close, timer drain
and the final result. The unexecuted zero/17/compiler controls may then run in a
new owned session after the same combined reviewer checks the changed source.
No product Cargo, broad suite repeat, new runner or routine approval is required.
