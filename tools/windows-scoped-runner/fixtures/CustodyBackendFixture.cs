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
        // Runtime directories are retained: this fixture does not claim a
        // handle-safe removal operation, which belongs to a later backend step.

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
            Expect("nested source tree copies and staged executable stays pinned", staged && allocation.IsStaged &&
                allocation.StagedExecutableIdentity != null && allocation.StagedExecutableHandle != null &&
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
