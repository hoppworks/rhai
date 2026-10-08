# Allocation02 native result and narrow repair

The complete 19-file serial export binds the reviewed allocation02 inputs and
actual observer exit -536870909 (E0000003). The setup-failure control, outer
owner-only accounting and real exit-0/17/mismatch controls passed. Production
ScopedRunner compilation exited zero. Driver compilation exited one with
CS0103 at MonitorAcceptanceDriver.cs:143: TerminateJobObject was called but not
declared. No public driver, payload or Cargo was launched. This is a source
compilation defect in the existing acceptance driver, not Rhai product RED.

The repair adds the existing kernel32 API's matching retained-job/uint-exit
DllImport and updates the two checked source pins. Allocation03 preserves the
same native bootstrap, resource bounds and export, with fresh identity. No
new wrapper is introduced. The short C# bootstrap is rerun because no prior
BuildOnly invocation has reached its post-disposition manifest/result; the
accepted Unix/Darwin product runs remain applicable and are not repeated.
Allocation02 inputs, logs, failed guest run and partial production binary remain
preserved until evidence/identity-bound retirement. No cleanup or native driver
acceptance is inferred from the compiler result alone.
