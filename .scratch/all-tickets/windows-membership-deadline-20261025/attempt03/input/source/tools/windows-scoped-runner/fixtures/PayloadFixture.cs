using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

internal static class PayloadFixture
{
    private static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--retirement-abort") return WorkRetirementAbort();
        if (args.Length == 2 && args[1] == "--environment") return EnvironmentContract(args[0]);
        bool held = args.Length == 2 && args[1] == "--hold";
        if (args.Length != 1 && !held) return 64;
        File.WriteAllText(args[0], "payload-started\r\n");
        if (!held) return 0;

        // A finite held payload for disconnect/client-death/replay controls. The
        // record is readiness; this bounded wait is deliberate test input, never
        // a readiness substitute. Natural expiry126 cannot satisfy monitor125.
        using (Process self = Process.GetCurrentProcess())
        {
            File.WriteAllText(args[0] + ".identity",
                "pid=" + self.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) +
                " creation=" + self.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(System.Globalization.CultureInfo.InvariantCulture) + "\r\n");
        }
        using (ManualResetEvent hold = new ManualResetEvent(false)) hold.WaitOne(120000);
        return 126;
    }
    private const int FormerInventoryBound = 2048;
    private const long FormerSingleFileBound = 64L * 1024L * 1024L;
    private const long ExpectedWorkBytes = 613419011L;
    private const int ExpectedMinimumWorkEntries = 2060;
    private const int FormerPathBound = 248;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateDirectoryW")]
    private static extern bool CreateDirectoryForRetirement(string path, IntPtr securityAttributes);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateFileW")]
    private static extern SafeFileHandle CreateFileForRetirement(string path, uint access, uint share, IntPtr security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true, EntryPoint = "WriteFile")]
    private static extern bool WriteFileForRetirement(SafeFileHandle file, byte[] buffer, uint bytesToWrite,
        out uint bytesWritten, IntPtr overlapped);

    private static string ExtendedPath(string path) { return @"\\?\" + path; }

    private static void CreateExtendedDirectoryTree(string parent, string target)
    {
        string relative = target.Substring(parent.Length).TrimStart(Path.DirectorySeparatorChar);
        string current = parent;
        foreach (string component in relative.Split(new[] { Path.DirectorySeparatorChar }, StringSplitOptions.RemoveEmptyEntries))
        {
            current = Path.Combine(current, component);
            if (!CreateDirectoryForRetirement(ExtendedPath(current), IntPtr.Zero))
                throw new IOException("retirement fixture CreateDirectoryW failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        }
    }

    private static void WriteExtendedFile(string path)
    {
        using (SafeFileHandle file = CreateFileForRetirement(ExtendedPath(path), 0x40000000, 0,
            IntPtr.Zero, 1, 0x00000080, IntPtr.Zero))
        {
            if (file == null || file.IsInvalid)
                throw new IOException("retirement fixture CreateFileW failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            uint written;
            if (!WriteFileForRetirement(file, new[] { (byte)'x' }, 1, out written, IntPtr.Zero) || written != 1)
                throw new IOException("retirement fixture WriteFile failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        }
    }

    // This real child intentionally fails its assertion after creating private
    // work beyond the retired snapshot's old bounds. The supervisor must still
    // close its exact Job, retire work and export only bounded results.
    private static int WorkRetirementAbort()
    {
        string runtime = Environment.CurrentDirectory;
        string work = Path.Combine(runtime, "work");
        if (!Directory.Exists(work)) throw new IOException("private work directory is absent");
        long expectedBytes = 2050;
        for (int index = 0; index < 2050; index++)
            File.WriteAllText(Path.Combine(work, "entry-" + index.ToString("D4", System.Globalization.CultureInfo.InvariantCulture) + ".txt"), "x");
        for (int index = 0; index < 9; index++)
        {
            using (FileStream stream = new FileStream(Path.Combine(work, "oversized-" + index.ToString("D2", System.Globalization.CultureInfo.InvariantCulture) + ".bin"),
                FileMode.CreateNew, FileAccess.Write, FileShare.None)) stream.SetLength(65L * 1024L * 1024L);
            expectedBytes += 65L * 1024L * 1024L;
        }
        string longDirectory = work;
        while (Path.Combine(longDirectory, "long-path.txt").Substring(work.Length + 1).Length <= FormerPathBound)
            longDirectory = Path.Combine(longDirectory, new string('d', 20));
        string longFile = Path.Combine(longDirectory, "long-path.txt");
        CreateExtendedDirectoryTree(work, longDirectory);
        WriteExtendedFile(longFile);
        expectedBytes++;
        int relativePathLength = longFile.Substring(work.Length + 1).Length;
        if (expectedBytes != ExpectedWorkBytes || relativePathLength <= FormerPathBound ||
            ExpectedMinimumWorkEntries <= FormerInventoryBound || 65L * 1024L * 1024L <= FormerSingleFileBound)
            throw new InvalidDataException("retirement abort fixture does not exceed its frozen independent bounds");
        Console.WriteLine("INTENTIONAL_ASSERTION_FAILURE: retirement abort after bounded-work fixture");
        Console.WriteLine("WORK_RETIREMENT_EXPECTED_MIN_ENTRIES:" + ExpectedMinimumWorkEntries.ToString(System.Globalization.CultureInfo.InvariantCulture));
        Console.WriteLine("WORK_RETIREMENT_EXPECTED_BYTES:" + expectedBytes.ToString(System.Globalization.CultureInfo.InvariantCulture));
        Console.WriteLine("WORK_RETIREMENT_LONG_RELATIVE_PATH:" + relativePathLength.ToString(System.Globalization.CultureInfo.InvariantCulture));
        return 42;
    }

    // Real payload contract: child-only private paths and an independent record.
    // Native admission through the public Driver/lease client exercises the
    // actual CreateProcessW environment, never a source-text expectation.
    private static int EnvironmentContract(string record)
    {
        string runtime = Environment.CurrentDirectory;
        string work = Path.Combine(runtime, "work");
        string[] keys = { "AGENT_RUNTIME_DIR", "TMP", "TEMP", "CARGO_HOME", "CARGO_TARGET_DIR" };
        string[] expected = { runtime, Path.Combine(work, "temp"), Path.Combine(work, "temp"),
            Path.Combine(work, "cargo-home"), Path.Combine(work, "target") };
        string[] observed = new string[keys.Length + 2];
        observed[0] = "cwd=" + Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(runtime));
        bool passed = true;
        for (int index = 0; index < keys.Length; index++)
        {
            string value = Environment.GetEnvironmentVariable(keys[index]);
            observed[index + 1] = keys[index] + "=" +
                Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(value ?? ""));
            if (!String.Equals(value, expected[index], StringComparison.OrdinalIgnoreCase))
            {
                passed = false;
                Console.Error.WriteLine("FAIL native payload private environment " + keys[index]);
            }
        }
        observed[observed.Length - 1] = "contract=" + (passed ? "PASS" : "FAIL");
        File.WriteAllLines(record, observed, new System.Text.UTF8Encoding(false));
        if (passed) Console.WriteLine("PASS native payload private environment");
        return passed ? 0 : 42;
    }

}
