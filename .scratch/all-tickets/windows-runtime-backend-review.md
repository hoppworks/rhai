# Windows runtime backend foundation source review

Reviewed candidate 4bf0e3a50b8b7e42a27c49ee6fe3ef8feaa723e6 and related
correction 967500f39eae9c0f08fde65e0a80c855143ff461 in the owned
/Users/hoppworks/projects/rhai-windows-scoped-runner checkout. Neither is
integrated into the coordinator or accepted as native custody implementation.

## Coverage and actual checks

OCR commit previews selected WindowsCustodyBackend.cs under the default system
rule. README.md (unsupported extension) and fixtures/CustodyBackendFixture.cs
(default fixture exclusion) were also manually reviewed in full. Three unique
files reviewed, zero skipped, coverage 100 percent. Related correction diff was
reviewed for all three files. git show --check passed and candidate checkout
was clean. No compiler, fixture, guest, process or temporary runtime was launched.
There is no TDD RED/GREEN or native behavior proof from this substep.

## Findings corrected in the responsible context

- LocalFree was declared against advapi32 rather than kernel32. The DLL was
  corrected. See [Microsoft LocalFree documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-localfree).
- DACL retrieval now requests DACL_SECURITY_INFORMATION and separately checks
  protected descriptor flags and exact principals/access. See
  [GetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo).
- DOS path validation rejects forward separators before opening any component;
  unsupported raw parent/ADS components are rejected rather than accepted after
  normalization. Ancestors remain pinned without delete sharing.
- Any write or flush error faults the journal irreversibly; subsequent appends
  reject. Current-user identity token lifetime is explicitly disposed.
- Fixture rename unexpectedly succeeding no longer loses the owned moved path;
  cleanup tracks both exact paths and only removes plain empty directories.
- Oversized input is rejected before scanning/encoding. Fixture parsing requires
  a final LF, canonical ASCII/hex, record/count bounds and matching length/CRC.
  Missing-final-LF and truncated-body fixture sources were added. The former
  ReadAllLines loses the distinction between final LF and EOF; see
  [Microsoft ReadAllLines remarks](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.readalllines?view=netframework-4.8.1).

## Scope and remaining requirements

This source foundation pins each existing local directory component, records
handle-derived identities, and exclusively creates bounded flushed journal
files with verified protected current-user/SYSTEM ACLs. CreateJournal still
depends on a future integration supplying an external pinned evidence root.
The fixture parser is only for the fixture's closed, owned journal; its
FileInfo/read sequence is not a production concurrent-file recovery reader.
Production recovery must use bounded handle reads and preserve uncertainty.

No monitor backend call, exclusive runtime allocation/ACL/identity, allocation
intent ordering, source staging, executable validation, evidence completion or
export, payload/job connection, termination/finalization bounds, safe handle
deletion or independently verified absence exists. Running lease challenges
remain unsupported and must be corrected before actual payload integration.
Synchronous filesystem calls must not block the watchdog when integrated.
All native ABI, ACL, sharing, transport-loss and job behavior remains unverified.
Public workload entry remains disabled. The full Expert contract is unchanged.

This is intermediate source progress within escalation 02's existing correction;
no completed failed full-custody correction or infrastructure recovery occurred.
Reviewed source findings and corrections remain recorded here. No new Expert
chain or execution budget was created, and no backlog ticket was closed.
