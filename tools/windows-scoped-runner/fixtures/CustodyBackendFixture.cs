// Source-only Windows custody fixture. Build and execution require the reviewed
// external custody/native acceptance gate; this file is deliberately unexecuted.
using System;
using System.IO;
using System.Security.Principal;
using System.Threading;
using Microsoft.Win32.SafeHandles;
using System.Runtime.InteropServices;

internal static class CustodyBackendFixture
{
    private static int failures;

    private static void Expect(string name, bool passed)
    {
        if (!passed)
        {
            failures++;
            Console.Error.WriteLine("FAIL " + name);
        }
        else Console.WriteLine("PASS " + name);
    }

    public static int Main()
    {
        Expect("evidence budget includes staged source and bytes already saved",
            WindowsCustodyBackend.RuntimeAllocation.RemainingEvidenceBytes(400,100)==WindowsCustodyBackend.MaximumTotalStagedBytes-500);
        Expect("full staged source leaves no evidence capacity",
            WindowsCustodyBackend.RuntimeAllocation.RemainingEvidenceBytes(WindowsCustodyBackend.MaximumTotalStagedBytes,0)==0);
        bool sharedEvidenceOverflow=false;
        try { WindowsCustodyBackend.RuntimeAllocation.RemainingEvidenceBytes(400,WindowsCustodyBackend.MaximumTotalStagedBytes); }
        catch(IOException) { sharedEvidenceOverflow=true; }
        Expect("evidence budget rejects source plus evidence overflow before writing",sharedEvidenceOverflow);
        string fixture = Path.Combine(Path.GetTempPath(), "rhai-custody-fixture-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(fixture);
        string moved = fixture + ".moved";
        try
        {
            using (WindowsCustodyBackend.PinnedDirectory pin = WindowsCustodyBackend.PinDirectoryForFixture(fixture))
            {
                WindowsCustodyBackend.FileIdentity before = pin.Identity;
                Expect("pinned directory identity is nonempty", before.FileId != Guid.Empty && before.VolumeSerial != 0);

                bool renameBlocked = false;
                try { Directory.Move(fixture, moved); }
                catch (IOException) { renameBlocked = true; }
                catch (UnauthorizedAccessException) { renameBlocked = true; }
                if (!renameBlocked && Directory.Exists(moved))
                {
                    try { Directory.Move(moved, fixture); }
                    catch (Exception e) { Console.Error.WriteLine("could not restore fixture path: " + e.Message); }
                }
                Expect("pinned directory cannot be renamed while held", renameBlocked);

                string journalPath;
                using (WindowsCustodyBackend.DurableJournal journal = WindowsCustodyBackend.CreateJournal(pin, out journalPath))
                {
                    journal.Append("INTENT|" + Guid.NewGuid().ToString("N") + "|C:\\RhaiQuality\\runs\\scoped-fixture");
                    journal.Append("UNKNOWN_GAP|allocation-identity-not-recorded");
                    Expect("record limit rejects before accepting another record", !journal.TryAppend(new string('x', WindowsCustodyBackend.MaximumRecordBytes + 1)));
                }

                string[] records = WindowsCustodyBackend.ReadJournalForFixture(journalPath);
                Expect("journal readback retains both flushed records", records.Length == 2 &&
                    records[0].StartsWith("INTENT|", StringComparison.Ordinal) &&
                    records[1] == "UNKNOWN_GAP|allocation-identity-not-recorded");
                byte[] validBytes = File.ReadAllBytes(journalPath);
                Expect("journal reader rejects a missing final newline", RejectsJournal(Path.Combine(fixture, "truncated-newline"),
                    Slice(validBytes, validBytes.Length - 1)));
                int firstNewline = Array.IndexOf(validBytes, (byte)'\n');
                Expect("journal reader rejects a truncated record body", RejectsJournal(Path.Combine(fixture, "truncated-body"),
                    RemoveByte(validBytes, firstNewline - 1)));
                Expect("journal is outside runtime candidate path", !journalPath.StartsWith(
                    Path.Combine(fixture, "runtime") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase));
                File.Delete(journalPath);
            }
            AllocationTransitions(fixture);
            SourceStagingContracts(fixture);
            PayloadPendingIoOwnershipContracts();
            PayloadLogBoundContracts(fixture);
            PayloadEvidenceCaptureContracts(fixture);
            PayloadEvidenceFailureContracts(fixture);
            RuntimeDispositionContracts(fixture);
        }
        finally
        {
            DeleteIfOwnedPlainEmptyDirectory(fixture);
            DeleteIfOwnedPlainEmptyDirectory(moved);
        }
        return failures == 0 ? 0 : 1;
    }

    private static void DeleteIfOwnedPlainEmptyDirectory(string path)
    {
        if (!Directory.Exists(path)) return;
        if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) return;
        try { Directory.Delete(path, false); }
        catch (IOException) { Console.Error.WriteLine("retaining nonempty fixture directory: " + path); }
        catch (UnauthorizedAccessException) { Console.Error.WriteLine("retaining inaccessible fixture directory: " + path); }
    }

    private static bool RejectsJournal(string path, byte[] bytes)
    {
        File.WriteAllBytes(path, bytes);
        try
        {
            WindowsCustodyBackend.ReadJournalForFixture(path);
            return false;
        }
        catch (IOException) { return true; }
        catch (FormatException) { return true; }
        finally { File.Delete(path); }
    }

    private static byte[] Slice(byte[] source, int length)
    {
        byte[] result = new byte[length];
        Buffer.BlockCopy(source, 0, result, 0, length);
        return result;
    }

    private static byte[] RemoveByte(byte[] source, int index)
    {
        byte[] result = new byte[source.Length - 1];
        Buffer.BlockCopy(source, 0, result, 0, index);
        Buffer.BlockCopy(source, index + 1, result, index, source.Length - index - 1);
        return result;
    }

    private static void AllocationTransitions(string fixture)
    {
        string successRoot = Path.Combine(fixture, "allocation-success");
        Directory.CreateDirectory(successRoot);
        string successPath;
        string successJournal;
        WindowsCustodyBackend.FileIdentity successRuntimeIdentity;
        WindowsCustodyBackend.FileIdentity successEvidenceIdentity;
        WindowsCustodyBackend.FileIdentity successJournalIdentity;
        using (WindowsCustodyBackend.RuntimeAllocation success = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(successRoot), Guid.NewGuid(), false))
        {
            successPath = success.RuntimePath;
            successJournal = success.JournalPath;
            Expect("allocation intent is flushed before runtime creation", success.State == WindowsCustodyBackend.AllocationState.IntentFlushed && !Directory.Exists(successPath));
            Expect("runtime allocation verifies protected ACL and records identity", success.CreateRuntime() &&
                success.State == WindowsCustodyBackend.AllocationState.IdentityRecorded && success.IsAclVerified &&
                success.RuntimeIdentity != null && success.EvidenceIdentity != null);
            successRuntimeIdentity = success.RuntimeIdentity;
            successEvidenceIdentity = success.EvidenceIdentity;
            successJournalIdentity = success.JournalIdentity;
        }
        string[] successRecords = WindowsCustodyBackend.ReadJournalForFixture(successJournal);
        Expect("allocation journal orders intent before identity", successRecords.Length == 2 &&
            successRecords[0].StartsWith("INTENT|", StringComparison.Ordinal) &&
            successRecords[0].Contains(successPath) && successRecords[0].Contains(successJournal) &&
            successRecords[0].Contains(successEvidenceIdentity.FileId.ToString("N")) &&
            successRecords[0].Contains(successJournalIdentity.FileId.ToString("N")) &&
            successRecords[1].StartsWith("IDENTITY|", StringComparison.Ordinal) &&
            successRecords[1].Contains(successRuntimeIdentity.FileId.ToString("N")) &&
            successRecords[1].Contains(successEvidenceIdentity.FileId.ToString("N")) &&
            successRecords[1].Contains(successJournalIdentity.FileId.ToString("N")));
        RetainPair("successful allocation", successPath, successJournal);
        // Allocation fixtures retain their runtime and journal; the separate
        // disposition contracts below exercise only their typed fixture gate.

        string collisionRoot = Path.Combine(fixture, "allocation-collision");
        Directory.CreateDirectory(collisionRoot);
        Guid collisionId = Guid.NewGuid();
        string collisionPath;
        string firstJournal;
        using (WindowsCustodyBackend.RuntimeAllocation first = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(collisionRoot), collisionId, false))
        {
            collisionPath = first.RuntimePath;
            firstJournal = first.JournalPath;
            Expect("first exclusive runtime owner records identity", first.CreateRuntime() && first.State == WindowsCustodyBackend.AllocationState.IdentityRecorded);
        }
        File.WriteAllText(Path.Combine(collisionPath, "foreign-marker.txt"), "preserve-existing-owner");
        string collisionJournal;
        using (WindowsCustodyBackend.RuntimeAllocation collision = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(collisionRoot), collisionId, false))
        {
            collisionJournal = collision.JournalPath;
            bool collisionRejected = !collision.CreateRuntime() && collision.State == WindowsCustodyBackend.AllocationState.FailedBeforeCreation;
            Expect("existing runtime name is refused without adopting its marker", collisionRejected &&
                File.ReadAllText(Path.Combine(collisionPath, "foreign-marker.txt")) == "preserve-existing-owner" &&
                collision.Failure.Contains(collisionPath) && collision.Failure.Contains(collisionJournal));
        }
        string[] collisionRecords = WindowsCustodyBackend.ReadJournalForFixture(collisionJournal);
        Expect("collision journal retains intent without a false identity", collisionRecords.Length == 1 &&
            collisionRecords[0].StartsWith("INTENT|", StringComparison.Ordinal));
        RetainPair("collision owner", collisionPath, firstJournal);
        RetainPair("collision attempt", collisionPath, collisionJournal);

        string partialRoot = Path.Combine(fixture, "allocation-partial");
        Directory.CreateDirectory(partialRoot);
        string partialPath;
        string partialJournal;
        using (WindowsCustodyBackend.RuntimeAllocation partial = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(partialRoot), Guid.NewGuid(), true))
        {
            partialPath = partial.RuntimePath;
            partialJournal = partial.JournalPath;
            bool partialFailed = !partial.CreateRuntime() && partial.State == WindowsCustodyBackend.AllocationState.FailedRetained &&
                Directory.Exists(partialPath) && partial.RuntimeIdentity != null && !partial.IsIdentityRecorded &&
                partial.Failure.Contains(partialPath) && partial.Failure.Contains(partialJournal);
            Expect("post-create journal failure retains exact runtime and incomplete state", partialFailed);
        }
        string[] partialRecords = WindowsCustodyBackend.ReadJournalForFixture(partialJournal);
        Expect("uncertain allocation journal contains intent but no identity receipt", partialRecords.Length == 1 &&
            partialRecords[0].StartsWith("INTENT|", StringComparison.Ordinal));
        RetainPair("uncertain partial allocation", partialPath, partialJournal);
        // Retain this uncertain directory; identity observation alone does not
        // authorize path-based cleanup or prove safe disposition semantics.
    }

    private static void RetainPair(string label, string runtimePath, string journalPath)
    {
        Console.WriteLine("RETAINED " + label + " runtime=" + runtimePath);
        Console.WriteLine("RETAINED " + label + " journal=" + journalPath);
    }

    // These executable source contract fixtures are deliberately not compiled
    // or run in this source-only step; every allocated runtime and journal is retained.
    private static void SourceStagingContracts(string fixture)
    {
        Expect("executable syntax rejects DOS device names before source I/O",
            RejectsExecutableBeforeIo(fixture, new[] { "NUL.txt", @"bin\..\runner.exe", @"C:runner.exe", @"bin\runner.exe:stream" }));

        string successRoot = NewStageCase(fixture, "stage-success");
        string successSource = Path.Combine(successRoot, "source");
        Directory.CreateDirectory(Path.Combine(successSource, "bin"));
        Directory.CreateDirectory(Path.Combine(successSource, "assets", "nested"));
        File.WriteAllBytes(Path.Combine(successSource, "bin", "runner.exe"), new byte[] { 0x4d, 0x5a, 0x01, 0x02 });
        File.WriteAllText(Path.Combine(successSource, "assets", "nested", "message.txt"), "independent nested readback");
        string successRuntime, successJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(successRoot, out successRuntime, out successJournal))
        {
            bool allocated = allocation.CreateRuntime() && allocation.IsIdentityRecorded;
            bool staged = allocated && allocation.StageSourceTreeForFixture(successSource, @"bin\runner.exe", CancellationToken.None, null, null);
            long expectedSourceBytes=new FileInfo(Path.Combine(successSource,"bin","runner.exe")).Length+
                new FileInfo(Path.Combine(successSource,"assets","nested","message.txt")).Length;
            Expect("nested source tree copies and staged executable stays pinned", staged && allocation.IsStaged &&
                allocation.StagedExecutableIdentity != null && allocation.StagedExecutableHandle != null &&
                allocation.StagedSourceBytes==expectedSourceBytes &&
                WindowsCustodyBackend.RuntimeAllocation.RemainingEvidenceBytes(allocation.StagedSourceBytes,0)==WindowsCustodyBackend.MaximumTotalStagedBytes-expectedSourceBytes &&
                File.ReadAllText(Path.Combine(successRuntime, "assets", "nested", "message.txt")) == "independent nested readback" &&
                File.ReadAllBytes(Path.Combine(successRuntime, "bin", "runner.exe")).Length == 4);
        }
        Expect("successful staging has a flushed completion receipt", HasStagedReceipt(successJournal));
        RetainPair("successful source staging", successRuntime, successJournal);

        string missingRoot = NewStageCase(fixture, "stage-missing-exe");
        string missingSource = Path.Combine(missingRoot, "source");
        Directory.CreateDirectory(missingSource);
        File.WriteAllText(Path.Combine(missingSource, "readme.txt"), "tree has no executable");
        ExpectRetainedStageFailure(missingRoot, missingSource, "bin\\runner.exe", "missing executable");

        string directoryExeRoot = NewStageCase(fixture, "stage-directory-exe");
        string directoryExeSource = Path.Combine(directoryExeRoot, "source");
        Directory.CreateDirectory(Path.Combine(directoryExeSource, "bin", "runner.exe"));
        ExpectRetainedStageFailure(directoryExeRoot, directoryExeSource, @"bin\runner.exe", "directory executable");

        string mutationRoot = NewStageCase(fixture, "stage-source-mutation");
        string mutationSource = PrepareSimpleStageTree(mutationRoot);
        ExpectRetainedStageFailure(mutationRoot, mutationSource, @"bin\runner.exe", "source mutation",
            delegate(string sourcePath) { File.WriteAllText(Path.Combine(sourcePath, "added-during-stage.txt"), "changed"); });

        string sharingRoot = NewStageCase(fixture, "stage-sharing-refusal");
        string sharingSource = PrepareSimpleStageTree(sharingRoot);
        string lockedPath = Path.Combine(sharingSource, "bin", "runner.exe");
        using (var exclusiveWriter = new FileStream(lockedPath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            ExpectRetainedStageFailure(sharingRoot, sharingSource, @"bin\runner.exe", "source sharing refusal");

        string sourceReparseRoot = NewStageCase(fixture, "stage-source-reparse");
        string sourceReparse = PrepareSimpleStageTree(sourceReparseRoot);
        CreateDirectoryLink(Path.Combine(sourceReparse, "linked"), Path.Combine(sourceReparse, "bin"));
        ExpectRetainedStageFailure(sourceReparseRoot, sourceReparse, @"bin\runner.exe", "source reparse refusal");

        string destinationCollisionRoot = NewStageCase(fixture, "stage-destination-collision");
        string collisionSource = PrepareSimpleStageTree(destinationCollisionRoot);
        string collisionRuntime, collisionJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(destinationCollisionRoot, out collisionRuntime, out collisionJournal))
        {
            bool allocated = allocation.CreateRuntime();
            File.WriteAllText(Path.Combine(collisionRuntime, "bin"), "foreign collision");
            bool refused = allocated && !allocation.StageSourceTreeForFixture(collisionSource, @"bin\runner.exe", CancellationToken.None, null, null) && !allocation.IsStaged;
            Expect("destination collision is not adopted", refused &&
                File.ReadAllText(Path.Combine(collisionRuntime, "bin")) == "foreign collision");
        }
        Expect("destination collision journal has no staged receipt", !HasStagedReceipt(collisionJournal));
        RetainPair("destination collision", collisionRuntime, collisionJournal);

        string partialRoot = NewStageCase(fixture, "stage-partial-failure");
        string partialSource = Path.Combine(partialRoot, "source");
        Directory.CreateDirectory(Path.Combine(partialSource, "assets", "nested"));
        Directory.CreateDirectory(Path.Combine(partialSource, "bin"));
        File.WriteAllText(Path.Combine(partialSource, "assets", "nested", "first.txt"), "copied before injected failure");
        File.WriteAllBytes(Path.Combine(partialSource, "bin", "runner.exe"), new byte[] { 0x4d, 0x5a });
        string partialRuntime, partialJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(partialRoot, out partialRuntime, out partialJournal))
        {
            bool allocated = allocation.CreateRuntime();
            bool failed = allocated && !allocation.StageSourceTreeForFixture(partialSource, @"bin\runner.exe", CancellationToken.None, null,
                @"bin\runner.exe") && !allocation.IsStaged;
            Expect("mid-copy fixture fails after retaining an earlier copied entry", failed &&
                File.Exists(Path.Combine(partialRuntime, "assets", "nested", "first.txt")));
        }
        Expect("partial staging journal has no staged receipt", !HasStagedReceipt(partialJournal));
        RetainPair("partial staging failure", partialRuntime, partialJournal);

        string inventoryRoot = NewStageCase(fixture, "stage-inventory-bound");
        string inventorySource = PrepareSimpleStageTree(inventoryRoot);
        for (int i = 0; i <= WindowsCustodyBackend.MaximumInventoryEntries; i++)
            File.WriteAllText(Path.Combine(inventorySource, "entry-" + i.ToString("D5") + ".dat"), "bounded entry");
        ExpectRetainedStageFailure(inventoryRoot, inventorySource, @"bin\runner.exe", "inventory bound", null,
            "fixed inventory bound");

        string byteBoundRoot = NewStageCase(fixture, "stage-byte-bound");
        string byteBoundSource = PrepareSimpleStageTree(byteBoundRoot);
        // Source fixture only: up to 576 MiB logical input and 512 MiB output
        // may be involved. Native execution requires a separately bounded disk budget.
        for (int i = 0; i < 9; i++)
            using (FileStream large = new FileStream(Path.Combine(byteBoundSource, "large-" + i.ToString("D2") + ".dat"), FileMode.CreateNew, FileAccess.Write, FileShare.None))
                large.SetLength(WindowsCustodyBackend.MaximumSingleStagedFileBytes);
        ExpectRetainedStageFailure(byteBoundRoot, byteBoundSource, @"bin\runner.exe", "total byte bound", null,
            "source tree exceeds the fixed total byte bound");

        string fileBoundRoot = NewStageCase(fixture, "stage-file-bound");
        string fileBoundSource = PrepareSimpleStageTree(fileBoundRoot);
        using (FileStream oversized = new FileStream(Path.Combine(fileBoundSource, "oversized.dat"), FileMode.CreateNew, FileAccess.Write, FileShare.None))
            oversized.SetLength(WindowsCustodyBackend.MaximumSingleStagedFileBytes + 1);
        ExpectRetainedStageFailure(fileBoundRoot, fileBoundSource, @"bin\runner.exe", "single file bound", null,
            "source file size or type is outside the fixed bound");

        string depthRoot = NewStageCase(fixture, "stage-depth-bound");
        string depthSource = PrepareSimpleStageTree(depthRoot);
        string nested = depthSource;
        for (int i = 0; i <= WindowsCustodyBackend.MaximumSourceDepth; i++)
        {
            nested = Path.Combine(nested, "d");
            Directory.CreateDirectory(nested);
        }
        ExpectRetainedStageFailure(depthRoot, depthSource, @"bin\runner.exe", "source depth bound", null,
            "source directory depth exceeds the fixed bound");

        string cancellationRoot = NewStageCase(fixture, "stage-cancellation");
        string cancellationSource = PrepareSimpleStageTree(cancellationRoot);
        using (var cancellation = new CancellationTokenSource())
        {
            cancellation.Cancel();
            ExpectRetainedStageFailure(cancellationRoot, cancellationSource, @"bin\runner.exe", "staging cancellation", null,
                "OperationCanceledException", cancellation.Token);
        }

        string stagedReparseRoot = NewStageCase(fixture, "stage-destination-reparse");
        string stagedReparseSource = PrepareSimpleStageTree(stagedReparseRoot);
        string stagedRuntime, stagedJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(stagedReparseRoot, out stagedRuntime, out stagedJournal))
        {
            bool allocated = allocation.CreateRuntime();
            CreateDirectoryLink(Path.Combine(stagedRuntime, "linked"), Path.Combine(stagedReparseSource, "bin"));
            bool refused = allocated && !allocation.StageSourceTreeForFixture(stagedReparseSource, @"bin\runner.exe", CancellationToken.None, null, null) && !allocation.IsStaged;
            Expect("staged reparse entry is rejected", refused);
        }
        Expect("staged reparse journal has no completion receipt", !HasStagedReceipt(stagedJournal));
        RetainPair("staged reparse refusal", stagedRuntime, stagedJournal);
    }

    // Source-only contract coverage. These call the typed fixture capability;
    // they do not simulate or claim exact-job closure or workload acceptance.
    private static void RuntimeDispositionContracts(string fixture)
    {
        string successRoot = NewStageCase(fixture, "remove-success");
        string successRuntime, successJournal;
        string sentinel = Path.Combine(successRoot, "separate-sentinel.txt");
        File.WriteAllText(sentinel, "must remain unchanged");
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(successRoot, out successRuntime, out successJournal))
        {
            string source = PrepareDispositionTree(successRoot, true);
            bool staged = allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null);
            Expect("nested runtime removal starts from exact recorded staged identity", staged && allocation.IsStaged);
            bool missingAuthorization = !allocation.RemoveRuntime() && allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.Blocked;
            Expect("production disposition refuses without monitor exact-job proof", missingAuthorization);
            var fixtureOperations=new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } };
            var fixtureJob=MonitorPayloadJob.ForClosureFixture(allocation,fixtureOperations);
            MonitorPayloadJob.ClosureReceipt fixtureReceipt=fixtureJob.CloseAndVerify();
            LeaseMonitor.ExactJobClosureProof fixtureProof=fixtureJob.ClosureAuthorization;
            Expect("proof binds to exact allocation object and immutable runtime identity",
                fixtureReceipt!=null && fixtureProof!=null && fixtureProof.Authorizes(allocation,allocation.RuntimeIdentity));
            Expect("proof rejects a different allocation reference or immutable identity",
                fixtureProof!=null && !fixtureProof.Authorizes(null,allocation.RuntimeIdentity) &&
                !fixtureProof.Authorizes(allocation,new WindowsCustodyBackend.FileIdentity(
                    allocation.RuntimeIdentity.VolumeSerial^1UL,allocation.RuntimeIdentity.FileId)));
            ulong finalizationDeadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
            allocation.RecordLifecycleDiagnostics(null,null,fixtureProof,finalizationDeadline);
            bool proofOnlyRemovalRefused=!allocation.RemoveRuntimeAfterExactJobClosure(fixtureProof,CancellationToken.None);
            Expect("exact-job proof alone cannot remove a runtime before local outcome finalization",
                proofOnlyRemovalRefused && allocation.DispositionState==WindowsCustodyBackend.RuntimeDispositionState.Blocked);
            var localEvidence=allocation.RecordLocalOutcomeMetadata(fixtureProof,0,
                WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,finalizationDeadline);
            string[] finalizedRecords=WindowsCustodyBackend.ReadJournalForFixture(successJournal);
            Expect("bounded outcome metadata is flushed and honestly marks payload evidence unsaved",
                localEvidence!=null && localEvidence.LocalMetadataSaved && !localEvidence.PayloadEvidenceSaved && !localEvidence.HostExported &&
                finalizedRecords.Length>0 && HasRecord(finalizedRecords,"OUTCOME|") &&
                HasRecord(finalizedRecords,"LIFECYCLE|") &&
                finalizedRecords[finalizedRecords.Length-1].Contains("|cleanup=CONFIRMED|diagnostics_saved=1|local_metadata_saved=1|payload_evidence_saved=0|host_exported=0|runtime_removed=0"));
            bool mismatchedOutcomeRejected=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(fixtureProof,1,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,finalizationDeadline);
            }
            catch(InvalidOperationException) { mismatchedOutcomeRejected=true; }
            bool mismatchedSupervisionRejected=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(fixtureProof,0,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.MonitorStopped,finalizationDeadline);
            }
            catch(InvalidOperationException) { mismatchedSupervisionRejected=true; }
            bool mismatchedDeadlineRejected=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(fixtureProof,0,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,finalizationDeadline-1);
            }
            catch(InvalidOperationException) { mismatchedDeadlineRejected=true; }
            Expect("metadata receipt cannot be rebound to a different exit, supervision result, or deadline",
                mismatchedOutcomeRejected && mismatchedSupervisionRejected && mismatchedDeadlineRejected);
            string foreignRoot=NewStageCase(fixture,"proof-foreign-owner");
            string foreignRuntime,foreignJournal;
            WindowsCustodyBackend.RuntimeAllocation.OutcomeMetadataReceipt foreignEvidence;
            using(WindowsCustodyBackend.RuntimeAllocation foreign=BeginStageAllocation(foreignRoot,out foreignRuntime,out foreignJournal))
            {
                bool foreignCreated=foreign.CreateRuntime() && foreign.RuntimeIdentity!=null;
                Expect("foreign proof allocation identity is recorded",foreignCreated);
                if(foreignCreated)
                {
                    var foreignJob=MonitorPayloadJob.ForClosureFixture(foreign,
                        new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
                    foreignJob.CloseAndVerify();
                    ulong foreignDeadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
                    foreign.RecordLifecycleDiagnostics(null,null,foreignJob.ClosureAuthorization,foreignDeadline);
                    foreignEvidence=foreign.RecordLocalOutcomeMetadata(foreignJob.ClosureAuthorization,null,
                        WindowsCustodyBackend.PayloadSupervisionOutcome.TransitionFailed,foreignDeadline);
                }
                else foreignEvidence=null;
                Expect("fixture can mint metadata only after the foreign exact-job algorithm closes",foreignEvidence!=null);
                Expect("runtime removal rejects another allocation's outcome metadata receipt",
                    foreignEvidence!=null && !allocation.TryRemoveRuntimeAfterOutcomeMetadata(foreignEvidence,CancellationToken.None));
            }
            RetainPair("foreign proof runtime",foreignRuntime,foreignJournal);
            bool metadataCannotRemove=!allocation.TryRemoveRuntimeAfterOutcomeMetadata(localEvidence,CancellationToken.None);
            Expect("outcome metadata alone retains runtime pending payload evidence capture",metadataCannotRemove &&
                allocation.Failure!=null && allocation.Failure.Contains("payload logs, results, and manifest") &&
                Directory.Exists(successRuntime) && allocation.DispositionState==WindowsCustodyBackend.RuntimeDispositionState.Blocked);
            bool removed = allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None,WindowsCustodyBackend.DispositionFailurePoint.None);
            Expect("fixture-only filesystem path still removes the nested runtime entries", removed &&
                allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.Removed &&
                !Directory.Exists(successRuntime) && File.ReadAllText(sentinel) == "must remain unchanged");
        }
        string[] successRecords = WindowsCustodyBackend.ReadJournalForFixture(successJournal);
        Expect("removal receipt follows independent absence readback", HasRecord(successRecords, "REMOVE_INTENT|") &&
            HasRecord(successRecords, "REMOVED|") && !Directory.Exists(successRuntime));
        RetainPair("removed runtime evidence", successRuntime, successJournal);

        string outcomeFailureRoot=NewStageCase(fixture,"outcome-append-failure");
        string outcomeFailureRuntime,outcomeFailureJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(outcomeFailureRoot,
            out outcomeFailureRuntime,out outcomeFailureJournal))
        {
            string source=PrepareDispositionTree(outcomeFailureRoot,false);
            bool staged=allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null);
            Expect("outcome append failure fixture has staged identity",staged && allocation.IsStaged);
            var operations=new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } };
            var payload=MonitorPayloadJob.ForClosureFixture(allocation,operations);
            payload.CloseAndVerify();
            LeaseMonitor.ExactJobClosureProof proof=payload.ClosureAuthorization;
            ulong failureDeadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
            allocation.RecordLifecycleDiagnostics(null,null,proof,failureDeadline);
            allocation.FailNextJournalAppendForFixture();
            bool appendFailed=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(proof,null,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.TransitionFailed,
                    failureDeadline);
            }
            catch(InvalidOperationException) { appendFailed=true; }
            bool proofOnlyStillRefused=!allocation.RemoveRuntimeAfterExactJobClosure(proof,CancellationToken.None);
            Expect("failed local outcome append retains runtime without a finalization receipt",
                appendFailed && proofOnlyStillRefused && Directory.Exists(outcomeFailureRuntime) &&
                allocation.DispositionState==WindowsCustodyBackend.RuntimeDispositionState.Blocked &&
                !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(outcomeFailureJournal),"OUTCOME|") &&
                !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(outcomeFailureJournal),"REMOVED|"));
        }
        RetainPair("outcome append failure runtime and journal",outcomeFailureRuntime,outcomeFailureJournal);

        string outcomeDeadlineRoot=NewStageCase(fixture,"outcome-deadline-expired");
        string outcomeDeadlineRuntime,outcomeDeadlineJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(outcomeDeadlineRoot,
            out outcomeDeadlineRuntime,out outcomeDeadlineJournal))
        {
            string source=PrepareDispositionTree(outcomeDeadlineRoot,false);
            bool staged=allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null);
            Expect("expired outcome deadline fixture has staged identity",staged && allocation.IsStaged);
            var payload=MonitorPayloadJob.ForClosureFixture(allocation,
                new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
            payload.CloseAndVerify();
            ulong expiredDeadline=WindowsCustodyBackend.RuntimeAllocation.ExpiredFinalizationDeadlineForFixture();
            bool expired=false;
            try { allocation.RecordLifecycleDiagnostics(null,null,payload.ClosureAuthorization,expiredDeadline); }
            catch(TimeoutException) { expired=true; }
            bool outcomeRejected=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(payload.ClosureAuthorization,null,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.TransitionFailed,expiredDeadline);
            }
            catch(InvalidOperationException) { outcomeRejected=true; }
            Expect("expired shared finalization deadline prevents diagnostics and withholds outcome receipt",
                expired && outcomeRejected && Directory.Exists(outcomeDeadlineRuntime) &&
                !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(outcomeDeadlineJournal),"OUTCOME|") &&
                !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(outcomeDeadlineJournal),"REMOVED|"));
        }
        RetainPair("expired outcome deadline runtime and journal",outcomeDeadlineRuntime,outcomeDeadlineJournal);

        string noProofRoot=NewStageCase(fixture,"diagnostics-without-proof");
        string noProofRuntime,noProofJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(noProofRoot,out noProofRuntime,out noProofJournal))
        {
            bool created=allocation.CreateRuntime() && allocation.IsIdentityRecorded;
            ulong deadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
            if(created) allocation.RecordLifecycleDiagnostics(null,null,null,deadline);
            string[] records=WindowsCustodyBackend.ReadJournalForFixture(noProofJournal);
            bool noProofIsUnconfirmed=records.Length>0 && records[records.Length-1].Contains("cleanup_confirmed=0");
            bool reboundRejected=false;
            if(created)
            {
                var payload=MonitorPayloadJob.ForClosureFixture(allocation,
                    new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
                payload.CloseAndVerify();
                try { allocation.RecordLifecycleDiagnostics(null,null,payload.ClosureAuthorization,deadline); }
                catch(InvalidOperationException) { reboundRejected=true; }
            }
            Expect("diagnostics without exact closure proof remain explicitly unconfirmed and cannot be rebound",
                created && noProofIsUnconfirmed && reboundRejected && Directory.Exists(noProofRuntime) &&
                !HasRecord(records,"OUTCOME|") && !HasRecord(records,"REMOVED|"));
        }
        RetainPair("no-proof diagnostic runtime and journal",noProofRuntime,noProofJournal);

        string cleanupFailureRoot=NewStageCase(fixture,"cleanup-failure-diagnostics");
        string cleanupFailureRuntime,cleanupFailureJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(cleanupFailureRoot,
            out cleanupFailureRuntime,out cleanupFailureJournal))
        {
            bool created=allocation.CreateRuntime() && allocation.IsIdentityRecorded;
            Expect("cleanup diagnostic case has recorded allocation",created);
            var payload=created ? MonitorPayloadJob.ForClosureFixture(allocation,
                new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } }) : null;
            if(payload!=null) payload.CloseAndVerify();
            ulong failureDeadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
            if(created) allocation.RecordLifecycleDiagnostics(new IOException("transition failed"),new IOException("job query failed"),null,failureDeadline);
            bool failureOutcomeRejected=false;
            try
            {
                allocation.RecordLocalOutcomeMetadata(payload==null ? null : payload.ClosureAuthorization,null,
                    WindowsCustodyBackend.PayloadSupervisionOutcome.TransitionFailed,failureDeadline);
            }
            catch(InvalidOperationException) { failureOutcomeRejected=true; }
            string[] diagnosticRecords=WindowsCustodyBackend.ReadJournalForFixture(cleanupFailureJournal);
            bool retained=Directory.Exists(cleanupFailureRuntime) &&
                failureOutcomeRejected &&
                HasRecord(diagnosticRecords,"LIFECYCLE|") &&
                diagnosticRecords[diagnosticRecords.Length-1].Contains("operation=IOException:transition failed") &&
                diagnosticRecords[diagnosticRecords.Length-1].Contains("cleanup=IOException:job query failed") &&
                diagnosticRecords[diagnosticRecords.Length-1].Contains("cleanup_confirmed=0") &&
                !HasRecord(diagnosticRecords,"OUTCOME|") && !HasRecord(diagnosticRecords,"REMOVED|") &&
                !allocation.RemoveRuntime();
            Expect("operation and cleanup failures are durably recorded without closure, evidence, or removal authority",retained);
        }
        RetainPair("cleanup diagnostic retained runtime and journal",cleanupFailureRuntime,cleanupFailureJournal);

        string identityRoot = NewStageCase(fixture, "remove-unrecorded-identity");
        string identityRuntime, identityJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(identityRoot), Guid.NewGuid(), true))
        {
            identityRuntime = allocation.RuntimePath; identityJournal = allocation.JournalPath;
            Expect("unrecorded identity cannot authorize disposition", !allocation.CreateRuntime() &&
                !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                    CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None) &&
                allocation.DispositionState != WindowsCustodyBackend.RuntimeDispositionState.Removed);
        }
        Expect("unrecorded identity has no removal receipt after handles close",
            !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(identityJournal), "REMOVED|"));
        RetainPair("unrecorded identity runtime", identityRuntime, identityJournal);

        string partialRoot = NewStageCase(fixture, "remove-partial");
        string partialRuntime, partialJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(partialRoot, out partialRuntime, out partialJournal))
        {
            string source = PrepareDispositionTree(partialRoot, true);
            Expect("partial removal fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool failed = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.AfterFirstDisposition);
            Expect("partial disposition is retained with explicit failure", failed &&
                allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.PartialRetained &&
                Directory.Exists(partialRuntime) && allocation.Failure != null);
        }
        string[] partialLeaves =
        {
            Path.Combine(partialRuntime, "bin", "runner.exe"),
            Path.Combine(partialRuntime, "data", "data.txt"),
            Path.Combine(partialRuntime, "data", "nested", "inner.txt")
        };
        int remainingLeaves = 0;
        int absentLeaves = 0;
        for (int i = 0; i < partialLeaves.Length; i++)
        {
            if (File.Exists(partialLeaves[i])) remainingLeaves++;
            else absentLeaves++;
        }
        Expect("partial disposition independently reads one removed leaf and remaining leaves after owner handles close",
            Directory.Exists(partialRuntime) && remainingLeaves == 2 && absentLeaves == 1);
        Expect("partial removal never writes successful receipt", !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(partialJournal), "REMOVED|"));
        RetainPair("partial runtime removal", partialRuntime, partialJournal);

        string reparseRoot = NewStageCase(fixture, "remove-reparse");
        string reparseRuntime, reparseJournal;
        string outside = Path.Combine(reparseRoot, "foreign-target");
        Directory.CreateDirectory(outside);
        File.WriteAllText(Path.Combine(outside, "sentinel.txt"), "foreign target intact");
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(reparseRoot, out reparseRuntime, out reparseJournal))
        {
            string source = PrepareDispositionTree(reparseRoot, false);
            Expect("reparse removal fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            CreateDirectoryLink(Path.Combine(reparseRuntime, "linked"), outside);
            bool refused = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None);
            Expect("runtime reparse target is refused and separately owned sentinel remains", refused &&
                File.ReadAllText(Path.Combine(outside, "sentinel.txt")) == "foreign target intact" &&
                allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.PartialRetained);
        }
        Expect("reparse refusal has no removal receipt after handles close",
            !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(reparseJournal), "REMOVED|"));
        RetainPair("reparse runtime removal refusal", reparseRuntime, reparseJournal);

        string sharingRoot = NewStageCase(fixture, "remove-sharing");
        string sharingRuntime, sharingJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(sharingRoot, out sharingRuntime, out sharingJournal))
        {
            string source = PrepareDispositionTree(sharingRoot, false);
            Expect("sharing refusal fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            string locked = Path.Combine(sharingRuntime, "data", "data.txt");
            using (var held = new FileStream(locked, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                bool refused = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                    CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None);
                Expect("sharing refusal retains runtime without receipt", refused && Directory.Exists(sharingRuntime) &&
                    allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.PartialRetained);
            }
        }
        Expect("sharing refusal has no removal receipt", !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(sharingJournal), "REMOVED|"));
        RetainPair("sharing-refused runtime", sharingRuntime, sharingJournal);

        string readbackRoot = NewStageCase(fixture, "remove-readback-failure");
        string readbackRuntime, readbackJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(readbackRoot, out readbackRuntime, out readbackJournal))
        {
            string source = PrepareDispositionTree(readbackRoot, false);
            Expect("readback failure fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool unknown = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.Readback);
            Expect("failed absence readback remains unknown with no successful receipt", unknown &&
                allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.Unknown);
        }
        string[] readbackRecords = WindowsCustodyBackend.ReadJournalForFixture(readbackJournal);
        Expect("failed readback cannot emit successful removal receipt", HasRecord(readbackRecords, "REMOVE_INTENT|") &&
            !HasRecord(readbackRecords, "REMOVED|"));
        RetainPair("unknown removal readback", readbackRuntime, readbackJournal);

        string journalRoot = NewStageCase(fixture, "remove-journal-failure");
        string journalRuntime, journalPath;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(journalRoot, out journalRuntime, out journalPath))
        {
            string source = PrepareDispositionTree(journalRoot, true);
            Expect("journal failure fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            allocation.FailNextJournalAppendForFixture();
            bool stopped = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None);
            Expect("failed removal intent stops before mutation", stopped && File.Exists(Path.Combine(journalRuntime, "data", "data.txt")) &&
                allocation.DispositionState != WindowsCustodyBackend.RuntimeDispositionState.Removed);
        }
        Expect("journal failure has no removal receipt after handles close",
            !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(journalPath), "REMOVED|"));
        RetainPair("journal failure before removal", journalRuntime, journalPath);

        string boundsRoot = NewStageCase(fixture, "remove-bounds");
        string boundsRuntime, boundsJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(boundsRoot, out boundsRuntime, out boundsJournal))
        {
            string source = PrepareDispositionTree(boundsRoot, false);
            Expect("bounds fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool cancelled = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                new CancellationToken(true), WindowsCustodyBackend.DispositionFailurePoint.None);
            Expect("cancellation before first disposition retains runtime", cancelled && Directory.Exists(boundsRuntime) &&
                allocation.DispositionState != WindowsCustodyBackend.RuntimeDispositionState.Removed);
        }
        Expect("cancellation has no removal receipt after handles close",
            !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(boundsJournal), "REMOVED|"));
        RetainPair("cancelled runtime removal", boundsRuntime, boundsJournal);

        string entryBoundRoot = NewStageCase(fixture, "remove-entry-bound");
        string entryBoundRuntime, entryBoundJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(entryBoundRoot, out entryBoundRuntime, out entryBoundJournal))
        {
            string source = PrepareDispositionTree(entryBoundRoot, false);
            Expect("entry-bound fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool bounded = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None, 1, WindowsCustodyBackend.MaximumSourceDepth);
            Expect("runtime inventory limit is enforced before disposition", bounded && allocation.Failure != null &&
                allocation.Failure.Contains("inventory exceeds the fixture limit") && Directory.Exists(entryBoundRuntime));
        }
        Expect("entry-bound failure has no successful receipt", !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(entryBoundJournal), "REMOVED|"));
        RetainPair("runtime entry-bound refusal", entryBoundRuntime, entryBoundJournal);

        string depthRoot = NewStageCase(fixture, "remove-depth-bound");
        string depthRuntime, depthJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(depthRoot, out depthRuntime, out depthJournal))
        {
            string source = PrepareDispositionTree(depthRoot, true);
            Expect("depth-bound fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool bounded = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None,
                WindowsCustodyBackend.MaximumInventoryEntries, 0);
            Expect("runtime depth limit is enforced before descent", bounded && allocation.Failure != null &&
                allocation.Failure.Contains("runtime depth exceeds the fixture limit") && Directory.Exists(depthRuntime));
        }
        Expect("depth-bound failure has no successful receipt", !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(depthJournal), "REMOVED|"));
        RetainPair("runtime depth-bound refusal", depthRuntime, depthJournal);

        string readOnlyRoot = NewStageCase(fixture, "remove-read-only");
        string readOnlyRuntime, readOnlyJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(readOnlyRoot, out readOnlyRuntime, out readOnlyJournal))
        {
            string source = PrepareDispositionTree(readOnlyRoot, false);
            Expect("read-only fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            string readOnlyFile = Path.Combine(readOnlyRuntime, "data", "data.txt");
            File.SetAttributes(readOnlyFile, File.GetAttributes(readOnlyFile) | FileAttributes.ReadOnly);
            bool refused = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.None);
            Expect("read-only entry is retained without clearing attributes", refused && Directory.Exists(readOnlyRuntime) &&
                (File.GetAttributes(readOnlyFile) & FileAttributes.ReadOnly) != 0 && allocation.Failure != null &&
                allocation.Failure.Contains("read-only runtime entry is refused"));
        }
        Expect("read-only refusal has no successful receipt", !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(readOnlyJournal), "REMOVED|"));
        RetainPair("read-only runtime refusal", readOnlyRuntime, readOnlyJournal);

        string mismatchRoot = NewStageCase(fixture, "remove-identity-mismatch");
        string mismatchRuntime, mismatchJournal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(mismatchRoot, out mismatchRuntime, out mismatchJournal))
        {
            string source = PrepareDispositionTree(mismatchRoot, false);
            Expect("identity mismatch fixture has recorded staged identity", allocation.CreateRuntime() && allocation.IsIdentityRecorded &&
                allocation.StageSourceTreeForFixture(source, @"bin\runner.exe", CancellationToken.None, null, null));
            bool refused = !allocation.RemoveRuntimeForFixture(WindowsCustodyBackend.RuntimeAllocation.NoPayloadAuthorizationForFixture(),
                CancellationToken.None, WindowsCustodyBackend.DispositionFailurePoint.IdentityMismatch);
            Expect("runtime identity mismatch refuses disposition", refused && Directory.Exists(mismatchRuntime) &&
                allocation.DispositionState == WindowsCustodyBackend.RuntimeDispositionState.PartialRetained);
        }
        Expect("identity mismatch has no removal receipt after handles close",
            !HasRecord(WindowsCustodyBackend.ReadJournalForFixture(mismatchJournal), "REMOVED|"));
        RetainPair("identity mismatch runtime", mismatchRuntime, mismatchJournal);
    }

    // Drives the production bounded snapshot/readback/receipt and removal path
    // against a staged fixture tree. This source fixture is intentionally not
    // compiled or executed in the source-only checkpoint.
    private static void PayloadEvidenceCaptureContracts(string fixture)
    {
        string root=NewStageCase(fixture,"payload-evidence-capture");
        string source=PrepareDispositionTree(root,true);
        string runtime,journal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(root,out runtime,out journal))
        {
            bool staged=allocation.CreateRuntime() && allocation.StageSourceTreeForFixture(source, @"bin\runner.exe",CancellationToken.None,null,null);
            Expect("evidence capture fixture owns a complete staged runtime",staged && allocation.IsStaged);
            if(!staged) { RetainPair("payload evidence capture refusal",runtime,journal); return; }
            using(WindowsCustodyBackend.RuntimeAllocation.PayloadLogHandles logs=allocation.CreatePayloadLogHandles())
            {
                Expect("payload log handles belong to the allocation evidence root",logs.EvidenceIdentity!=null &&
                    logs.EvidenceIdentity.SameAs(allocation.PayloadEvidenceIdentity));
            }
            ulong deadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
            var job=MonitorPayloadJob.ForClosureFixture(allocation,
                new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
            MonitorPayloadJob.ClosureReceipt closure=job.CloseAndVerify(deadline);
            LeaseMonitor.ExactJobClosureProof proof=job.ClosureAuthorization;
            allocation.RecordLifecycleDiagnostics(null,null,proof,deadline);
            WindowsCustodyBackend.RuntimeAllocation.PayloadEvidenceReceipt evidence=null;
            try { evidence=allocation.CapturePayloadEvidence(proof,0,
                WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline); }
            catch(Exception error) { Console.Error.WriteLine("payload evidence capture fixture failed: "+error); }
            string snapshot=Path.Combine(allocation.PayloadEvidencePath,"runtime");
            Expect("production evidence capture receipt binds exact proof and independent snapshot readback",
                evidence!=null && evidence.CapturedBytes>0 && evidence.Deadline==deadline &&
                File.ReadAllText(Path.Combine(snapshot,"data","nested","inner.txt"))=="nested disposition fixture payload" &&
                File.Exists(Path.Combine(snapshot,"bin","runner.exe")) && File.Exists(Path.Combine(allocation.PayloadEvidencePath,"manifest.txt")));
            bool changedEvidenceOutcomeRejected=false;
            try { allocation.CapturePayloadEvidence(proof,1,WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline); }
            catch(InvalidOperationException) { changedEvidenceOutcomeRejected=true; }
            bool mismatchedEvidenceOutcomeRejected=false;
            try { allocation.RecordLocalOutcomeMetadata(proof,1,WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline,evidence); }
            catch(InvalidOperationException) { mismatchedEvidenceOutcomeRejected=true; }
            var metadata=evidence==null ? null : allocation.RecordLocalOutcomeMetadata(proof,0,
                WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline,evidence);
            bool removed=metadata!=null && allocation.TryRemoveRuntimeAfterOutcomeMetadata(metadata,CancellationToken.None);
            string[] records=WindowsCustodyBackend.ReadJournalForFixture(journal);
            Expect("evidence receipt cannot be rebound and production removal follows evidence and outcome records",
                changedEvidenceOutcomeRejected && mismatchedEvidenceOutcomeRejected && removed && !Directory.Exists(runtime) && HasRecord(records,"EVIDENCE|") &&
                HasRecord(records,"OUTCOME|") && HasRecord(records,"REMOVE_INTENT|") && HasRecord(records,"REMOVED|"));
            Expect("external snapshot and payload logs remain after runtime removal",
                Directory.Exists(snapshot) && File.Exists(Path.Combine(allocation.PayloadEvidencePath,"stdout.log")) &&
                File.Exists(Path.Combine(allocation.PayloadEvidencePath,"stderr.log")));
            GC.KeepAlive(closure);
        }
        RetainPair("payload evidence capture",runtime,journal);
    }

    private static void PayloadEvidenceFailureContracts(string fixture)
    {
        string mutationRoot=NewStageCase(fixture,"payload-evidence-readback-mismatch");
        string mutationSource=PrepareDispositionTree(mutationRoot,true);
        string mutationRuntime,mutationJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(mutationRoot,out mutationRuntime,out mutationJournal))
        {
            bool staged=allocation.CreateRuntime() && allocation.StageSourceTreeForFixture(mutationSource,@"bin\runner.exe",CancellationToken.None,null,null);
            if(staged)
            {
                using(WindowsCustodyBackend.RuntimeAllocation.PayloadLogHandles logs=allocation.CreatePayloadLogHandles()) { }
                var job=MonitorPayloadJob.ForClosureFixture(allocation,new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
                job.CloseAndVerify();
                LeaseMonitor.ExactJobClosureProof proof=job.ClosureAuthorization;
                ulong deadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
                allocation.RecordLifecycleDiagnostics(null,null,proof,deadline);
                bool mutationExecuted=false;
                allocation.SetEvidenceReadbackMutationForFixture(snapshot=>{ mutationExecuted=true; File.WriteAllText(Path.Combine(snapshot,"data","nested","inner.txt"),"tampered after copy"); });
                bool mismatch=false;
                try { allocation.CapturePayloadEvidence(proof,0,WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline); }
                catch(IOException error) { mismatch=error.Message.IndexOf("content differs from the source manifest",StringComparison.Ordinal)>=0; }
                string[] records=WindowsCustodyBackend.ReadJournalForFixture(mutationJournal);
                Expect("independent payload snapshot readback mismatch withholds evidence receipt and retains runtime",
                    mutationExecuted && mismatch && Directory.Exists(mutationRuntime) && HasRecord(records,"LIFECYCLE|") &&
                    !HasRecord(records,"EVIDENCE|") && !HasRecord(records,"OUTCOME|") && !HasRecord(records,"REMOVED|"));
            }
            else Expect("readback mismatch fixture staged runtime",false);
        }
        RetainPair("payload readback mismatch retained runtime",mutationRuntime,mutationJournal);

        string identityRoot=NewStageCase(fixture,"payload-evidence-identity-mismatch");
        string identitySource=PrepareDispositionTree(identityRoot,false);
        string identityRuntime,identityJournal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(identityRoot,out identityRuntime,out identityJournal))
        {
            bool staged=allocation.CreateRuntime() && allocation.StageSourceTreeForFixture(identitySource,@"bin\runner.exe",CancellationToken.None,null,null);
            if(staged)
            {
                using(WindowsCustodyBackend.RuntimeAllocation.PayloadLogHandles logs=allocation.CreatePayloadLogHandles()) { }
                var job=MonitorPayloadJob.ForClosureFixture(allocation,new MonitorPayloadJob.ScriptedClosureOperations { ActiveCounts=new uint[] { 0 } });
                job.CloseAndVerify();
                LeaseMonitor.ExactJobClosureProof proof=job.ClosureAuthorization;
                ulong deadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
                allocation.RecordLifecycleDiagnostics(null,null,proof,deadline);
                allocation.CorruptEvidenceIdentityForFixture();
                bool identityMismatch=false;
                try { allocation.CapturePayloadEvidence(proof,0,WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited,deadline); }
                catch(IOException error) { identityMismatch=error.Message=="payload evidence root identity changed before capture"; }
                string[] records=WindowsCustodyBackend.ReadJournalForFixture(identityJournal);
                Expect("payload evidence identity mismatch withholds receipt and retains runtime",
                    identityMismatch && Directory.Exists(identityRuntime) && !HasRecord(records,"EVIDENCE|") &&
                    !HasRecord(records,"OUTCOME|") && !HasRecord(records,"REMOVED|"));
            }
            else Expect("evidence identity mismatch fixture staged runtime",false);
        }
        RetainPair("payload evidence identity mismatch retained runtime",identityRuntime,identityJournal);
    }

    // These state-only cases use the exact production release predicate. They
    // do not claim to inject ConnectNamedPipe, CancelIoEx, or GetOverlappedResult.
    private static void PayloadPendingIoOwnershipContracts()
    {
        Expect("inheritable output writers and NUL stdin bind the Unicode CreateFileW entry point",
            MonitorPayloadJob.CreateFileEntryPointForFixture());
        Expect("constructor failure after pending connect retains OVERLAPPED storage",
            !MonitorPayloadJob.CanReleaseCaptureStorageForFixture(true,false,false));
        Expect("deadline cancellation without terminal observation retains buffers and handles",
            !MonitorPayloadJob.CanReleaseCaptureStorageForFixture(false,true,false));
        Expect("terminal cancellation observation permits exact capture resource disposal",
            MonitorPayloadJob.CanReleaseCaptureStorageForFixture(false,true,true));
        Expect("already terminal channels permit disposal",
            MonitorPayloadJob.CanReleaseCaptureStorageForFixture(false,false,true));
        Expect("unresolved output owner stays strongly held until terminal release",
            MonitorPayloadJob.PendingOwnerKeeperContractForFixture());
        ulong setupDeadline=1000,finalizationDeadline=5000;
        ulong firstCleanup=MonitorPayloadJob.BindCleanupDeadlineForFixture(false,setupDeadline,finalizationDeadline);
        ulong subsequent=MonitorPayloadJob.BindCleanupDeadlineForFixture(true,firstCleanup,finalizationDeadline+1000);
        ulong shortened=MonitorPayloadJob.BindCleanupDeadlineForFixture(true,firstCleanup,finalizationDeadline-1000);
        ulong setupFailure=MonitorPayloadJob.BindCleanupDeadlineForFixture(false,0,setupDeadline);
        Expect("successful long-lived setup binds its first cleanup to lifecycle deadline while unwind and later calls never extend",
            firstCleanup==finalizationDeadline && subsequent==firstCleanup && shortened==finalizationDeadline-1000 && setupFailure==setupDeadline);
        Expect("stdout/stderr append limit rejects overflow without unsigned wraparound",
            MonitorPayloadJob.CanAppendLogBytesForFixture(64U*1024U*1024U-65536U,65536U) &&
            !MonitorPayloadJob.CanAppendLogBytesForFixture(64U*1024U*1024U-65535U,65536U) &&
            !MonitorPayloadJob.CanAppendLogBytesForFixture(64U*1024U*1024U+1U,1U));
    }

    private static void PayloadLogBoundContracts(string fixture)
    {
        string root=NewStageCase(fixture,"payload-log-shared-bound");
        string source=PrepareDispositionTree(root,false);
        string runtime,journal;
        using(WindowsCustodyBackend.RuntimeAllocation allocation=BeginStageAllocation(root,out runtime,out journal))
        {
            bool staged=allocation.CreateRuntime() && allocation.StageSourceTreeForFixture(source, @"bin\runner.exe",CancellationToken.None,null,null);
            Expect("concurrent output accounting starts from a staged allocation",staged && allocation.IsStaged);
            if(staged)
            {
                long charge=(WindowsCustodyBackend.MaximumTotalStagedBytes-allocation.StagedSourceBytes)*3/4;
                bool[] accepted=new bool[2];
                var ready=new ManualResetEvent(false);
                Thread[] writers=new Thread[2];
                for(int i=0;i<writers.Length;i++)
                {
                    int index=i;
                    writers[i]=new Thread(()=>{ ready.WaitOne(); accepted[index]=allocation.TryChargePayloadLogBytes(charge); });
                    writers[i].IsBackground=true; writers[i].Start();
                }
                ready.Set();
                bool bothFinished=writers[0].Join(5000) && writers[1].Join(5000);
                int acceptedCount=(accepted[0]?1:0)+(accepted[1]?1:0);
                Expect("concurrent stdout/stderr accounting admits one charge before the shared staged-plus-output cap",
                    bothFinished && acceptedCount==1 && allocation.PayloadLogBytes==charge);
                ready.Dispose();
            }
            RetainPair("payload shared log bound",runtime,journal);
        }
    }

    private static string PrepareDispositionTree(string root, bool nested)
    {
        string source = Path.Combine(root, "source");
        Directory.CreateDirectory(Path.Combine(source, "bin"));
        Directory.CreateDirectory(Path.Combine(source, "data"));
        if (nested) Directory.CreateDirectory(Path.Combine(source, "data", "nested"));
        File.WriteAllBytes(Path.Combine(source, "bin", "runner.exe"), new byte[] { 0x4d, 0x5a, 0x01 });
        File.WriteAllText(Path.Combine(source, "data", "data.txt"), "disposition fixture payload");
        if (nested) File.WriteAllText(Path.Combine(source, "data", "nested", "inner.txt"), "nested disposition fixture payload");
        return source;
    }

    private static string NewStageCase(string fixture, string label)
    {
        string path = Path.Combine(fixture, label + "-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }

    private static string PrepareSimpleStageTree(string root)
    {
        string source = Path.Combine(root, "source");
        Directory.CreateDirectory(Path.Combine(source, "bin"));
        File.WriteAllBytes(Path.Combine(source, "bin", "runner.exe"), new byte[] { 0x4d, 0x5a, 0x01 });
        return source;
    }

    private static WindowsCustodyBackend.RuntimeAllocation BeginStageAllocation(string root, out string runtime, out string journal)
    {
        WindowsCustodyBackend.RuntimeAllocation allocation = WindowsCustodyBackend.BeginAllocationForFixture(
            WindowsCustodyBackend.PinDirectoryForFixture(root), Guid.NewGuid(), false);
        runtime = allocation.RuntimePath;
        journal = allocation.JournalPath;
        return allocation;
    }

    private static void ExpectRetainedStageFailure(string root, string source, string executable, string label,
        Action<string> beforeFinalRescan = null, string expectedDiagnostic = null,
        CancellationToken cancellationToken = default(CancellationToken))
    {
        string runtime, journal;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(root, out runtime, out journal))
        {
            bool allocated = allocation.CreateRuntime() && allocation.IsIdentityRecorded;
            Expect(label + " starts from a recorded allocation", allocated);
            bool failed = allocated && !allocation.StageSourceTreeForFixture(source, executable, cancellationToken, beforeFinalRescan, null) && !allocation.IsStaged;
            Expect(label + " fails closed", failed);
            if (expectedDiagnostic != null)
                Expect(label + " reports its intended failure", allocation.Failure != null && allocation.Failure.IndexOf(expectedDiagnostic, StringComparison.Ordinal) >= 0);
        }
        string[] records = WindowsCustodyBackend.ReadJournalForFixture(journal);
        Expect(label + " retains its exact runtime and identity record", Directory.Exists(runtime) && HasRecord(records, "IDENTITY|"));
        Expect(label + " journal has no staged receipt after disposal", !HasRecord(records, "STAGED|"));
        RetainPair(label, runtime, journal);
    }

    private static bool RejectsExecutableBeforeIo(string fixture, string[] invalidExecutables)
    {
        string root = NewStageCase(fixture, "stage-invalid-executable");
        string runtime, journal;
        bool allRejectedBeforeIo = true;
        using (WindowsCustodyBackend.RuntimeAllocation allocation = BeginStageAllocation(root, out runtime, out journal))
        {
            allRejectedBeforeIo = allocation.CreateRuntime() && allocation.IsIdentityRecorded;
            for (int i = 0; i < invalidExecutables.Length; i++)
            {
                try
                {
                    allocation.StageSourceTreeForFixture(Path.Combine(root, "source-that-does-not-exist"),
                        invalidExecutables[i], CancellationToken.None, null, null);
                    allRejectedBeforeIo = false;
                }
                catch (ArgumentException) { }
                catch { allRejectedBeforeIo = false; }
            }
            allRejectedBeforeIo = allRejectedBeforeIo && allocation.StageStatus == WindowsCustodyBackend.StagingState.NotStarted;
        }
        string[] records = WindowsCustodyBackend.ReadJournalForFixture(journal);
        RetainPair("invalid executable syntax", runtime, journal);
        return allRejectedBeforeIo && records.Length == 2 && !HasStagedReceipt(journal);
    }

    private static bool HasStagedReceipt(string journal)
    {
        return HasRecord(WindowsCustodyBackend.ReadJournalForFixture(journal), "STAGED|");
    }

    private static bool HasRecord(string[] records, string prefix)
    {
        for (int i = 0; i < records.Length; i++)
            if (records[i].StartsWith(prefix, StringComparison.Ordinal)) return true;
        return false;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateSymbolicLinkW")]
    private static extern bool CreateSymbolicLink(string link, string target, uint flags);

    private static void CreateDirectoryLink(string link, string target)
    {
        if (!CreateSymbolicLink(link, target, 1 | 2))
            throw new IOException("fixture could not create directory reparse point: " + link,
                new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
    }
}
