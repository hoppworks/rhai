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
        if (args.Length == 2 && args[1] == "--job-resources") return JobResourceContract(args[0], false);
        if (args.Length == 2 && args[1] == "--job-resources-leaf") return JobResourceContract(args[0], true);
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
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool QueryInformationJobObject(IntPtr job, int kind, IntPtr buffer, uint bytes, IntPtr returned);

    // Read the real caller Job's configured limits. Both actors publish their
    // own kernel readback before useful work; no controller-limit inference.
    private static int JobResourceContract(string record, bool leaf)
    {
        if (IntPtr.Size != 8) throw new InvalidOperationException("resource contract requires the reviewed64bit native layout");
        IntPtr information = Marshal.AllocHGlobal(144);
        uint flags, active; ulong processBytes, jobBytes;
        try {
            if (!QueryInformationJobObject(IntPtr.Zero, 9, information, 144, IntPtr.Zero))
                throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "query actual payload Job limits");
            flags = unchecked((uint)Marshal.ReadInt32(information, 16));
            active = unchecked((uint)Marshal.ReadInt32(information, 40));
            processBytes = unchecked((ulong)Marshal.ReadInt64(information, 112));
            jobBytes = unchecked((ulong)Marshal.ReadInt64(information, 120));
        } finally { Marshal.FreeHGlobal(information); }
        bool passed = flags == 0x2308 && active == 16 && processBytes == 1073741824UL && jobBytes == 2147483648UL;
        using (Process self = Process.GetCurrentProcess()) {
            string[] values = {
                "pid=" + self.Id.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "creation=" + self.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(System.Globalization.CultureInfo.InvariantCulture),
                "flags=" + flags.ToString("X8", System.Globalization.CultureInfo.InvariantCulture),
                "active_process_limit=" + active.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "process_memory_bytes=" + processBytes.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "job_memory_bytes=" + jobBytes.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "contract=" + (passed ? "PASS" : "FAIL")
            };
            string pending = record + ".pending";
            using (FileStream stream = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (StreamWriter writer = new StreamWriter(stream, new System.Text.UTF8Encoding(false))) {
                foreach (string value in values) writer.Write(value + "\r\n");
                writer.Flush(); stream.Flush(true);
            }
            File.Move(pending, record);
            if (!passed) { Console.Error.WriteLine("FAIL native payload Job resource contract"); return 42; }
            if (leaf) {
                using (ManualResetEvent hold = new ManualResetEvent(false)) hold.WaitOne(120000);
                return 126;
            }
            Process child = null; bool started = false, transferred = false;
            try {
                child = new Process { StartInfo = new ProcessStartInfo {
                    FileName = self.MainModule.FileName, Arguments = "\"" + Path.GetFullPath(record + ".child") + "\" --job-resources-leaf",
                    WorkingDirectory = Environment.CurrentDirectory, UseShellExecute = false, CreateNoWindow = true } };
                if (!child.Start()) throw new InvalidOperationException("resource child did not start");
                started = true;
                Stopwatch ready = Stopwatch.StartNew();
                while (!File.Exists(record + ".child")) {
                    if (child.HasExited) throw new InvalidOperationException("resource child exited before readiness");
                    if (ready.ElapsedMilliseconds >= 5000) throw new TimeoutException("resource child readiness exceeded5seconds");
                    Thread.Sleep(10);
                }
                string[] observed = File.ReadAllLines(record + ".child");
                if (observed.Length != 7 || observed[0] != "pid=" + child.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) ||
                    observed[1] != "creation=" + child.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(System.Globalization.CultureInfo.InvariantCulture) ||
                    observed[6] != "contract=PASS") throw new InvalidDataException("exact child resource contract failed");
                File.WriteAllText(record + ".work", "both-actors-resource-bounded\r\n", new System.Text.UTF8Encoding(false));
                // Public monitor retains the ordinary child and closes the whole
                // Job after root exit. Natural leaf126 cannot satisfy early stop.
                transferred = true;
                Console.WriteLine("PASS native payload Job resource contract");
                return 0;
            } finally {
                if (started && !transferred) {
                    if (!child.HasExited) child.Kill();
                    if (!child.WaitForExit(10000)) throw new TimeoutException("resource child cleanup did not finish");
                }
                if (child != null) child.Dispose();
            }
        }
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
