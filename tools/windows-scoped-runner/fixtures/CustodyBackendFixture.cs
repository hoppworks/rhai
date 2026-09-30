// Source-only Windows custody fixture. Build and execution require the reviewed
// external custody/native acceptance gate; this file is deliberately unexecuted.
using System;
using System.IO;
using System.Security.Principal;

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
        File.Delete(successJournal);
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
        File.Delete(firstJournal);
        File.Delete(collisionJournal);
        // Retain the exact collision owner directory and marker for inspection.

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
        File.Delete(partialJournal);
        // Retain this uncertain directory; identity observation alone does not
        // authorize path-based cleanup or prove safe disposition semantics.
    }
}
