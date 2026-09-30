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
                WindowsCustodyBackend.DirectoryIdentity before = pin.Identity;
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
                Expect("journal is outside runtime candidate path", !journalPath.StartsWith(
                    Path.Combine(fixture, "runtime") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase));
                File.Delete(journalPath);
            }
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
}
