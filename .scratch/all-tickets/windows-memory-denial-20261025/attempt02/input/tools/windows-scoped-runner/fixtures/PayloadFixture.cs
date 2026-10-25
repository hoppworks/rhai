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
        if (args.Length == 2 && args[1] == "--job-memory") return JobMemoryContract(args[0]);
        if (args.Length == 2 && args[1] == "--job-memory-leaf") return JobMemoryLeaf(args[0]);
        if (args.Length == 2 && args[1] == "--job-quota") return JobQuotaContract(args[0]);
        if (args.Length == 2 && (args[1] == "--job-quota-leaf" || args[1] == "--job-quota-excess"))
            return JobQuotaLeaf(args[0], args[1] == "--job-quota-excess");
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
    private static extern IntPtr VirtualAlloc(IntPtr address, UIntPtr bytes, uint allocationType, uint protection);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool VirtualFree(IntPtr address, UIntPtr bytes, uint freeType);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool inJob);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GlobalMemoryStatusEx(ref MemoryStatus status);

    [StructLayout(LayoutKind.Sequential)]
    private struct MemoryStatus
    {
        public uint length, load;
        public ulong totalPhysical, availablePhysical, totalPageFile, availablePageFile;
        public ulong totalVirtual, availableVirtual, availableExtendedVirtual;
    }

    private static void MemoryRecord(string path, string text)
    {
        using (FileStream file = new FileStream(path + ".pending", FileMode.CreateNew, FileAccess.Write, FileShare.Read)) {
            byte[] bytes = new System.Text.UTF8Encoding(false).GetBytes(text + "\r\n");
            file.Write(bytes, 0, bytes.Length); file.Flush(true);
        }
        File.Move(path + ".pending", path);
    }

    private static string MemoryIdentity(Process process)
    {
        bool inJob;
        if (!IsProcessInJob(process.Handle, IntPtr.Zero, out inJob) || !inJob)
            throw new InvalidDataException("memory actor is not in the actual Job");
        return "pid=" + process.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) +
            ";creation=" + process.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(System.Globalization.CultureInfo.InvariantCulture) + ";job_member=True";
    }

    private static int JobMemoryLeaf(string path)
    {
        // Commit without touching pages: Job limits charge committed memory,
        // while this fixture does not consume 768 MiB of physical RAM.
        IntPtr allocation = VirtualAlloc(IntPtr.Zero, new UIntPtr(768UL * 1024UL * 1024UL), 0x3000, 4);
        if (allocation == IntPtr.Zero) {
            MemoryRecord(path + ".failure", "phase=leaf-commit;native_error=" + Marshal.GetLastWin32Error());
            return 42;
        }
        try {
            using (Process self = Process.GetCurrentProcess())
                MemoryRecord(path, MemoryIdentity(self) + ";committed_bytes=805306368;private_bytes=" + self.PrivateMemorySize64);
            using (ManualResetEvent hold = new ManualResetEvent(false)) hold.WaitOne(120000);
            return 126;
        } finally {
            if (!VirtualFree(allocation, UIntPtr.Zero, 0x8000))
                Console.Error.WriteLine("memory leaf VirtualFree failed: " + Marshal.GetLastWin32Error());
        }
    }

    private static int JobMemoryContract(string path)
    {
        if (IntPtr.Size != 8) throw new InvalidOperationException("memory contract requires 64-bit Job layout");
        Process[] leaves = new Process[2]; bool[] started = new bool[2];
        IntPtr recovered = IntPtr.Zero; string phase = "initial";
        try {
            IntPtr limits = Marshal.AllocHGlobal(144);
            uint flags, active; ulong processLimit, jobLimit;
            try {
                phase = "query-limits";
                if (!QueryInformationJobObject(IntPtr.Zero, 9, limits, 144, IntPtr.Zero))
                    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "query actual memory Job limits");
                flags = unchecked((uint)Marshal.ReadInt32(limits, 16));
                active = unchecked((uint)Marshal.ReadInt32(limits, 40));
                processLimit = unchecked((ulong)Marshal.ReadInt64(limits, 112));
                jobLimit = unchecked((ulong)Marshal.ReadInt64(limits, 120));
            } finally { Marshal.FreeHGlobal(limits); }
            if (flags != 0x2308 || active != 16 || processLimit != 1073741824UL || jobLimit != 2147483648UL)
                throw new InvalidDataException("actual memory Job limits differ from the contract");
            MemoryStatus memory = new MemoryStatus(); memory.length = (uint)Marshal.SizeOf(typeof(MemoryStatus));
            if (!GlobalMemoryStatusEx(ref memory) || memory.availablePageFile < 3221225472UL)
                throw new InvalidOperationException("global commit headroom below 3 GiB before memory denial controls");
            using (Process self = Process.GetCurrentProcess())
                MemoryRecord(path + ".root", MemoryIdentity(self) + ";flags=00002308;process_limit=1073741824;job_limit=2147483648;global_available_commit=" + memory.availablePageFile + ";private_bytes=" + self.PrivateMemorySize64);

            phase = "process-limit-denial";
            IntPtr tooLarge = VirtualAlloc(IntPtr.Zero, new UIntPtr(1073741824UL), 0x3000, 4);
            int processError = tooLarge == IntPtr.Zero ? Marshal.GetLastWin32Error() : 0;
            if (tooLarge != IntPtr.Zero) {
                VirtualFree(tooLarge, UIntPtr.Zero, 0x8000);
                throw new InvalidDataException("1 GiB allocation unexpectedly succeeded despite root baseline");
            }
            MemoryRecord(path + ".process-denial", "bytes=1073741824;returned=False;native_error=" + processError + ";protected_unchanged=" + !File.Exists(path + ".protected"));
            if (processError == 0 || File.Exists(path + ".protected"))
                throw new InvalidDataException("process memory denial has no native error or changed protected state");

            string executable;
            using (Process self = Process.GetCurrentProcess()) executable = self.MainModule.FileName;
            for (int index = 0; index < 2; index++) {
                phase = "leaf-" + index + "-start";
                string leafPath = Path.GetFullPath(path + ".leaf-" + index);
                leaves[index] = new Process { StartInfo = new ProcessStartInfo {
                    FileName = executable, Arguments = "\"" + leafPath + "\" --job-memory-leaf",
                    WorkingDirectory = Environment.CurrentDirectory, UseShellExecute = false, CreateNoWindow = true } };
                if (!leaves[index].Start()) throw new InvalidOperationException("memory leaf did not start");
                started[index] = true;
                Stopwatch ready = Stopwatch.StartNew();
                while (!File.Exists(leafPath)) {
                    if (leaves[index].HasExited) throw new InvalidOperationException("memory leaf exited before committed readiness");
                    if (ready.ElapsedMilliseconds >= 5000) throw new TimeoutException("memory leaf readiness exceeded5seconds");
                    Thread.Sleep(10);
                }
                string observed = File.ReadAllText(leafPath);
                string expected = MemoryIdentity(leaves[index]) + ";committed_bytes=805306368;private_bytes=";
                long privateBytes;
                if (!observed.StartsWith(expected) || !observed.EndsWith("\r\n") ||
                    !long.TryParse(observed.Substring(expected.Length, observed.Length - expected.Length - 2), out privateBytes) ||
                    privateBytes < 805306368L || leaves[index].HasExited)
                    throw new InvalidDataException("memory leaf identity/readiness mismatch");
            }

            phase = "job-limit-denial";
            long rootPrivate;
            using (Process self = Process.GetCurrentProcess()) rootPrivate = self.PrivateMemorySize64;
            if (rootPrivate <= 0 || rootPrivate >= 536870912L)
                throw new InvalidDataException("root private memory leaves no independent per-process headroom for Job denial");
            MemoryStatus beforeJob = new MemoryStatus(); beforeJob.length = (uint)Marshal.SizeOf(typeof(MemoryStatus));
            if (!GlobalMemoryStatusEx(ref beforeJob) || beforeJob.availablePageFile < 1073741824UL)
                throw new InvalidOperationException("global commit headroom below 1 GiB immediately before Job denial");
            IntPtr denied = VirtualAlloc(IntPtr.Zero, new UIntPtr(536870912UL), 0x3000, 4);
            int jobError = denied == IntPtr.Zero ? Marshal.GetLastWin32Error() : 0;
            if (denied != IntPtr.Zero) {
                VirtualFree(denied, UIntPtr.Zero, 0x8000);
                throw new InvalidDataException("job-wide 512 MiB allocation unexpectedly succeeded with two committed leaves");
            }
            MemoryRecord(path + ".job-denial", "bytes=536870912;returned=False;native_error=" + jobError + ";root_private_before=" + rootPrivate +
                ";global_available_commit_before=" + beforeJob.availablePageFile + ";protected_unchanged=" + !File.Exists(path + ".protected"));
            if (jobError == 0 || File.Exists(path + ".protected"))
                throw new InvalidDataException("job memory denial has no native error or changed protected state");

            phase = "release-and-retry";
            leaves[0].Kill();
            if (!leaves[0].WaitForExit(5000)) throw new TimeoutException("memory leaf release exceeded5seconds");
            Stopwatch retry = Stopwatch.StartNew(); int retries = 0;
            do {
                recovered = VirtualAlloc(IntPtr.Zero, new UIntPtr(536870912UL), 0x3000, 4);
                if (recovered != IntPtr.Zero) break;
                retries++;
                if (retry.ElapsedMilliseconds >= 5000) throw new TimeoutException("identical 512 MiB allocation stayed denied after exact leaf exit");
                Thread.Sleep(10);
            } while (true);
            MemoryRecord(path + ".protected", "same-allocation-succeeded-after-exact-leaf-exit");
            using (Process self = Process.GetCurrentProcess())
                MemoryRecord(path, MemoryIdentity(self) + ";process_error=" + processError + ";job_error=" + jobError +
                    ";released_leaf=" + leaves[0].Id + ";retained_leaf=" + leaves[1].Id +
                    ";retries=" + retries + ";contract=PASS");
            Console.WriteLine("PASS native process and Job committed-memory denials");
            return 0;
        } catch (Exception error) {
            try { MemoryRecord(path + ".failure", "phase=" + phase + ";" + error); } catch { }
            Console.Error.WriteLine("FAIL native Job committed-memory contract: " + error);
            return 42;
        } finally {
            if (recovered != IntPtr.Zero && !VirtualFree(recovered, UIntPtr.Zero, 0x8000))
                Console.Error.WriteLine("memory root VirtualFree failed: " + Marshal.GetLastWin32Error());
            for (int index = 0; index < leaves.Length; index++) if (leaves[index] != null) {
                try {
                    if (started[index] && !leaves[index].HasExited) leaves[index].Kill();
                    if (started[index] && !leaves[index].WaitForExit(10000))
                        Console.Error.WriteLine("memory child wait incomplete; Job closure retains ownership");
                } catch (Exception cleanupError) { Console.Error.WriteLine("memory child cleanup failed: " + cleanupError); }
                finally { leaves[index].Dispose(); }
            }
        }
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

    // The public monitor's real Job owns these ordinary descendants at creation.
    // Keep wrappers strongly owned before Start; failed cleanup keeps them until
    // this fixture exits and the independent monitor closes the whole exact Job.
    private static Process[] quotaOwners;
    private static bool[] quotaStarted;
    private static string QuotaIdentity(Process process)
    {
        return "pid=" + process.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) +
            ";creation=" + process.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(System.Globalization.CultureInfo.InvariantCulture);
    }
    private static bool quotaTraceEnabled;
    private static string quotaPhase = "initial";
    private static int quotaQuerySequence;
    private static void QuotaTrace(string text)
    {
        if (!quotaTraceEnabled) return;
        byte[] bytes = new System.Text.UTF8Encoding(false).GetBytes(text + "\r\n");
        using (FileStream stream = new FileStream("quota-observation.log", FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read)) {
            if (stream.Length + bytes.Length > 262144) throw new InvalidDataException("quota observation exceeded256KiB");
            stream.Seek(0, SeekOrigin.End); stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
        }
    }
    private static int[] QuotaMembers()
    {
        // Observation capacity is not the permitted active count. Record the
        // native headers/error, including a failed call, without parsing its IDs.
        const int capacity = 64, bytes = 8 + capacity * 8;
        IntPtr list = Marshal.AllocHGlobal(bytes), returnLength = IntPtr.Zero;
        try {
            returnLength = Marshal.AllocHGlobal(4);
            for (int offset = 0; offset < bytes; offset += 4) Marshal.WriteInt32(list, offset, 0);
            Marshal.WriteInt32(returnLength, 0);
            bool succeeded = QueryInformationJobObject(IntPtr.Zero, 3, list, bytes, returnLength);
            int nativeError = succeeded ? 0 : Marshal.GetLastWin32Error();
            int assigned = Marshal.ReadInt32(list), returned = Marshal.ReadInt32(list, 4);
            string diagnostic = "query=" + (++quotaQuerySequence) + ";phase=" + quotaPhase +
                ";class=3;capacity=64;bytes=520;success=" + succeeded + ";native_error=" + nativeError +
                ";return_bytes=" + Marshal.ReadInt32(returnLength) + ";assigned=" + assigned + ";returned=" + returned;
            QuotaTrace(diagnostic);
            if (!succeeded) throw new System.ComponentModel.Win32Exception(nativeError, "query quota Job members: " + diagnostic);
            if (assigned < 1 || assigned > capacity || returned != assigned)
                throw new InvalidDataException("quota membership list is incomplete or outside diagnostic capacity: " + diagnostic);
            int[] values = new int[returned];
            for (int index = 0; index < returned; index++) values[index] = checked((int)Marshal.ReadIntPtr(list, 8 + index * IntPtr.Size).ToInt64());
            Array.Sort(values);
            for (int index = 0; index < values.Length; index++)
                if (values[index] <= 0 || (index != 0 && values[index] == values[index - 1]))
                    throw new InvalidDataException("quota membership has invalid/duplicate PIDs");
            return values;
        } finally {
            if (returnLength != IntPtr.Zero) Marshal.FreeHGlobal(returnLength);
            Marshal.FreeHGlobal(list);
        }
    }
    private static int QuotaAccounting()
    {
        IntPtr information = Marshal.AllocHGlobal(48);
        try {
            for (int offset = 0; offset < 48; offset += 4) Marshal.WriteInt32(information, offset, 0);
            bool succeeded = QueryInformationJobObject(IntPtr.Zero, 1, information, 48, IntPtr.Zero);
            int error = succeeded ? 0 : Marshal.GetLastWin32Error();
            int total = Marshal.ReadInt32(information, 36), active = Marshal.ReadInt32(information, 40), terminated = Marshal.ReadInt32(information, 44);
            QuotaTrace("accounting;phase=" + quotaPhase + ";success=" + succeeded + ";native_error=" + error +
                ";total=" + total + ";active=" + active + ";terminated=" + terminated);
            if (!succeeded) throw new System.ComponentModel.Win32Exception(error, "quota accounting phase=" + quotaPhase + ";native_error=" + error);
            if (active < 1 || active > 64 || total < active || terminated < 0) throw new InvalidDataException("quota accounting is outside its diagnostic bound");
            return active;
        } finally { Marshal.FreeHGlobal(information); }
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool QueryFullProcessImageName(IntPtr process, uint flags, System.Text.StringBuilder path, ref uint size);
    private static void QuotaMemberImages(string path, int[] members, int[] fixturePids, string executable)
    {
        if (members.Length < fixturePids.Length || members.Length > 32) throw new InvalidDataException("quota census exceeds bounded known payload/helper membership");
        foreach (int pid in fixturePids) if (Array.IndexOf(members, pid) < 0) throw new InvalidDataException("known payload absent from quota census");
        string helper = Path.Combine(Environment.SystemDirectory, "conhost.exe");
        string[] images = new string[members.Length];
        for (int index = 0; index < members.Length; index++) using (Process member = Process.GetProcessById(members[index])) {
            // The exact handle stays owned while image and creation are read.
            IntPtr handle = member.Handle;
            System.Text.StringBuilder image = new System.Text.StringBuilder(32768); uint size = 32768;
            if (!QueryFullProcessImageName(handle, 0, image, ref size)) {
                int error = Marshal.GetLastWin32Error();
                throw new System.ComponentModel.Win32Exception(error, "quota member image native_error=" + error);
            }
            string actual = image.ToString(); bool fixture = Array.IndexOf(fixturePids, member.Id) >= 0;
            if (!String.Equals(actual, fixture ? executable : helper, StringComparison.OrdinalIgnoreCase) || member.HasExited)
                throw new InvalidDataException("quota member has an unknown image/role or ended during census: " + member.Id + ";image=" + actual);
            images[index] = QuotaIdentity(member) + ";image_b64=" + Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(actual));
        }
        QuotaRecord(path, String.Join("\r\n", images));
    }
    private static void AssertQuotaConfiguration()
    {
        if (IntPtr.Size != 8) throw new InvalidOperationException("quota fixture requires64bit native layout");
        IntPtr info = Marshal.AllocHGlobal(144);
        try {
            if (!QueryInformationJobObject(IntPtr.Zero, 9, info, 144, IntPtr.Zero))
                throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "query quota Job configuration");
            if (Marshal.ReadInt32(info, 16) != 0x2308 || Marshal.ReadInt32(info, 40) != 16 ||
                Marshal.ReadInt64(info, 112) != 1073741824L || Marshal.ReadInt64(info, 120) != 2147483648L)
                throw new InvalidDataException("quota fixture requires actual16process/1GiBprocess/2GiBJob limits without breakaway");
        } finally { Marshal.FreeHGlobal(info); }
    }
    private static void QuotaRecord(string path, string text)
    {
        string pending = path + ".pending";
        using (FileStream stream = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
        using (StreamWriter writer = new StreamWriter(stream, new System.Text.UTF8Encoding(false))) {
            writer.Write(text + "\r\n"); writer.Flush(); stream.Flush(true);
        }
        File.Move(pending, path);
    }
    private static int JobQuotaLeaf(string path, bool excess)
    {
        if (excess) File.AppendAllText("quota-protected.txt", "EXCESS_PROCESS_RAN\r\n");
        AssertQuotaConfiguration();
        using (Process self = Process.GetCurrentProcess()) {
            if (Array.IndexOf(QuotaMembers(), self.Id) < 0) throw new InvalidDataException("quota leaf is not an actual Job member");
            QuotaRecord(path, QuotaIdentity(self) + ";job_member=True");
        }
        using (ManualResetEvent hold = new ManualResetEvent(false)) hold.WaitOne(120000);
        return 126;
    }
    private static int JobQuotaContract(string path)
    {
        bool transferred = false;
        quotaOwners = new Process[17]; quotaStarted = new bool[17];
        try {
            quotaTraceEnabled = true; quotaPhase = "fill";
            QuotaTrace("phase=begin;active_limit=16;observation_capacity=64");
            AssertQuotaConfiguration();
            string executable;
            using (Process self = Process.GetCurrentProcess()) executable = self.MainModule.FileName;
            for (int index = 0; index < quotaOwners.Length; index++) {
                string record = index >= 15 ? "quota-excess.txt" : "quota-child-" + index.ToString("D2", System.Globalization.CultureInfo.InvariantCulture) + ".txt";
                quotaOwners[index] = new Process { StartInfo = new ProcessStartInfo {
                    FileName = executable, Arguments = "\"" + record + "\" " + (index >= 15 ? "--job-quota-excess" : "--job-quota-leaf"),
                    WorkingDirectory = Environment.CurrentDirectory, UseShellExecute = false, CreateNoWindow = true } };
            }
            File.WriteAllText("quota-protected.txt", "protected-before-quota\r\n", new System.Text.UTF8Encoding(false));
            int count = 0; int[] full;
            // Console helpers can appear in the census without consuming the
            // ordinary-payload quota. Fill the finite 15 known app descendants;
            // classify every additional Job member instead of assuming its role.
            while (count < 15) {
                full = QuotaMembers();
                if (full.Length > 32) throw new InvalidDataException("quota fill census exceeded32actors");
                Process child = quotaOwners[count];
                if (!child.Start()) throw new InvalidOperationException("quota child did not start");
                quotaStarted[count] = true;
                string record = "quota-child-" + count.ToString("D2", System.Globalization.CultureInfo.InvariantCulture) + ".txt";
                Stopwatch ready = Stopwatch.StartNew();
                while (!File.Exists(record)) {
                    if (child.HasExited) throw new InvalidOperationException("quota child exited before readiness");
                    if (ready.ElapsedMilliseconds >= 5000) throw new TimeoutException("quota child readiness exceeded5seconds");
                    Thread.Sleep(10);
                }
                if (File.ReadAllText(record) != QuotaIdentity(child) + ";job_member=True\r\n" ||
                    Array.IndexOf(QuotaMembers(), child.Id) < 0 || child.HasExited)
                    throw new InvalidDataException("exact quota child readiness/membership differs");
                count++;
            }
            full = QuotaMembers();
            if (count != 15 || full.Length < 16 || full.Length > 32) throw new InvalidDataException("no real bounded16payload quota fill occurred");
            int[] fixturePids = new int[16];
            using (Process self = Process.GetCurrentProcess()) fixturePids[0] = self.Id;
            for (int index = 0; index < count; index++) fixturePids[index + 1] = quotaOwners[index].Id;
            QuotaMemberImages("quota-member-images.txt", full, fixturePids, executable);
            string[] memberIdentities = new string[full.Length];
            long[] memberCreations = new long[full.Length];
            for (int index = 0; index < full.Length; index++) {
                using (Process member = Process.GetProcessById(full[index])) {
                    if (member.HasExited) throw new InvalidDataException("full quota member exited before denial");
                    memberCreations[index] = member.StartTime.ToUniversalTime().ToFileTimeUtc();
                    memberIdentities[index] = QuotaIdentity(member);
                }
            }
            QuotaRecord("quota-members.txt", String.Join("\r\n", memberIdentities));
            quotaPhase = "before-admission";
            int[] immediatelyBefore = QuotaMembers();
            if (String.Join(",", full) != String.Join(",", immediatelyBefore)) throw new InvalidDataException("quota membership changed before the admission attempt");
            int accountingFull = QuotaAccounting();
            int apiError = 0; bool createReturned = false, excessWaited = false;
            int excessPid = 0; long excessCreation = 0; string excessExit = "NONE";
            quotaPhase = "admission-start";
            QuotaTrace("phase=before-start;before=" + String.Join(",", immediatelyBefore));
            try {
                createReturned = quotaOwners[15].Start();
                if (createReturned) quotaStarted[15] = true;
            } catch (System.ComponentModel.Win32Exception error) { apiError = error.NativeErrorCode; }
            QuotaTrace("phase=start-result;create_returned=" + createReturned + ";native_error=" + apiError);
            if (createReturned) {
                // Observe and persist the exact returned handle's natural exit
                // BEFORE another membership query or any exceptional cleanup.
                quotaPhase = "admission-identity";
                excessPid = quotaOwners[15].Id;
                QuotaTrace("phase=returned-pid;pid=" + excessPid);
                if (quotaOwners[15].Handle == IntPtr.Zero) throw new InvalidDataException("returned excess process has no exact retained handle");
                excessCreation = quotaOwners[15].StartTime.ToUniversalTime().ToFileTimeUtc();
                QuotaTrace("phase=returned-identity;pid=" + excessPid + ";creation=" + excessCreation);
                quotaPhase = "admission-wait";
                excessWaited = quotaOwners[15].WaitForExit(5000);
                if (excessWaited) excessExit = unchecked((uint)quotaOwners[15].ExitCode).ToString("X8", System.Globalization.CultureInfo.InvariantCulture);
            }
            QuotaRecord(path + ".admission", "create_returned=" + createReturned + ";api_error=" + apiError +
                ";pid=" + excessPid + ";creation=" + excessCreation + ";wait_confirmed=" + excessWaited + ";exit=" + excessExit +
                ";before=" + String.Join(",", immediatelyBefore));
            if ((createReturned && (!excessWaited || excessExit == "00000000")) || (!createReturned && apiError == 0) ||
                File.Exists("quota-excess.txt") || File.ReadAllText("quota-protected.txt") != "protected-before-quota\r\n")
                throw new InvalidDataException("full-capacity admission did not stop before excess user code");
            if (createReturned) { quotaOwners[15].Dispose(); quotaStarted[15] = false; }
            quotaPhase = "settled-denial";
            int[] after = QuotaMembers();
            int accountingAfter = QuotaAccounting();
            if (String.Join(",", full) != String.Join(",", after)) throw new InvalidDataException("quota denial changed original membership");
            for (int index = 0; index < full.Length; index++) {
                using (Process member = Process.GetProcessById(full[index])) {
                    if (member.HasExited || member.StartTime.ToUniversalTime().ToFileTimeUtc() != memberCreations[index])
                        throw new InvalidDataException("original full quota member identity changed after denial");
                }
            }
            File.Copy("quota-protected.txt", "quota-protected-after-denial.txt");
            // Countercase changes capacity, while executable/arguments/token stay
            // identical. This must not stand in for the full-capacity evidence.
            if (count < 2) throw new InvalidDataException("quota countercase needs two independently owned children");
            int[] releasedFixturePids = new[] { quotaOwners[0].Id, quotaOwners[1].Id };
            for (int index = 0; index < 2; index++) {
                if (quotaOwners[index].HasExited) throw new InvalidDataException("countercase child ended before explicit capacity release");
                quotaOwners[index].Kill();
                if (!quotaOwners[index].WaitForExit(5000)) throw new TimeoutException("countercase child release exceeded5seconds");
                quotaOwners[index].Dispose(); quotaStarted[index] = false;
            }
            quotaPhase = "released-capacity";
            Stopwatch capacity = Stopwatch.StartNew(); int[] released;
            while (true) {
                released = QuotaMembers();
                if (Array.IndexOf(released, releasedFixturePids[0]) < 0 && Array.IndexOf(released, releasedFixturePids[1]) < 0) break;
                if (capacity.ElapsedMilliseconds >= 5000) throw new TimeoutException("two released quota slots did not become available within5seconds");
                Thread.Sleep(10);
            }
            if (!quotaOwners[16].Start()) throw new InvalidOperationException("identical quota countercase did not start after capacity release");
            quotaStarted[16] = true;
            Stopwatch recoveredReady = Stopwatch.StartNew();
            while (!File.Exists("quota-excess.txt")) {
                if (quotaOwners[16].HasExited) throw new InvalidOperationException("countercase exited before its real user-code record");
                if (recoveredReady.ElapsedMilliseconds >= 5000) throw new TimeoutException("countercase readiness exceeded5seconds");
                Thread.Sleep(10);
            }
            string recoveryIdentity = QuotaIdentity(quotaOwners[16]);
            if (File.ReadAllText("quota-excess.txt") != recoveryIdentity + ";job_member=True\r\n" ||
                File.ReadAllText("quota-protected.txt") != "protected-before-quota\r\nEXCESS_PROCESS_RAN\r\n")
                throw new InvalidDataException("countercase did not independently reach the same executable's user code");
            quotaPhase = "recovered-countercase";
            int[] recovered = QuotaMembers();
            if (Array.IndexOf(recovered, quotaOwners[16].Id) < 0 || recovered.Length > 32 || quotaOwners[16].HasExited)
                throw new InvalidDataException("countercase is not live in the actual bounded Job");
            System.Collections.Generic.List<int> recoveredFixturePids = new System.Collections.Generic.List<int>();
            using (Process self = Process.GetCurrentProcess()) recoveredFixturePids.Add(self.Id);
            for (int index = 2; index < count; index++) recoveredFixturePids.Add(quotaOwners[index].Id);
            recoveredFixturePids.Add(quotaOwners[16].Id);
            QuotaMemberImages("quota-recovered-images.txt", recovered, recoveredFixturePids.ToArray(), executable);
            int accountingRecovered = QuotaAccounting();
            string[] recoveredIdentities = new string[recovered.Length];
            for (int index = 0; index < recovered.Length; index++) using (Process member = Process.GetProcessById(recovered[index])) {
                if (member.HasExited) throw new InvalidDataException("countercase Job member ended before final record");
                recoveredIdentities[index] = QuotaIdentity(member);
            }
            QuotaRecord("quota-recovered-members.txt", String.Join("\r\n", recoveredIdentities));
            using (Process self = Process.GetCurrentProcess()) {
                if (Array.IndexOf(full, self.Id) < 0) throw new InvalidDataException("quota root absent from original full Job");
                for (int index = 2; index < count; index++) if (quotaOwners[index].HasExited || Array.IndexOf(recovered, quotaOwners[index].Id) < 0)
                    throw new InvalidDataException("countercase lost another original fixture child");
                QuotaRecord(path, QuotaIdentity(self) + ";active_limit=16;payload_count=16;accounting_full=" + accountingFull + ";accounting_after=" + accountingAfter + ";accounting_recovered=" + accountingRecovered + ";members=" + String.Join(",", full) +
                    ";members_after=" + String.Join(",", after) + ";spawned=" + count + ";api_create_returned=" + createReturned +
                    ";api_error=" + apiError + ";excess_pid=" + excessPid + ";excess_creation=" + excessCreation +
                    ";excess_exit=" + excessExit + ";excess_wait_confirmed=" + excessWaited +
                    ";released_fixture_children=2;recovered_members=" + String.Join(",", recovered) +
                    ";recovery_pid=" + quotaOwners[16].Id + ";recovery_creation=" + quotaOwners[16].StartTime.ToUniversalTime().ToFileTimeUtc() +
                    ";excess_user_code=False;protected_unchanged_at_denial=True;countercase_user_code=True;contract=PASS");
            }
            // Natural leaf126 cannot satisfy the observer's immediate exact-Job closure.
            transferred = true;
            Console.WriteLine("PASS native actual Job process quota denial");
            return 0;
        } catch (Exception error) {
            try {
                System.ComponentModel.Win32Exception native = error as System.ComponentModel.Win32Exception;
                QuotaTrace("phase=failure;at=" + quotaPhase + ";native_error=" + (native == null ? "NONE" : native.NativeErrorCode.ToString(System.Globalization.CultureInfo.InvariantCulture)));
                QuotaRecord(path + ".failure", "phase=" + quotaPhase + "\r\n" + error.ToString());
            } catch { }
            Console.Error.WriteLine("FAIL native actual Job process quota denial: " + error);
            return 42;
        } finally {
            if (!transferred) {
                Stopwatch close = Stopwatch.StartNew();
                for (int index = 0; index < quotaOwners.Length; index++) if (quotaStarted[index]) {
                    try { if (!quotaOwners[index].HasExited) quotaOwners[index].Kill(); } catch (Exception error) { Console.Error.WriteLine("quota cleanup kill failed: " + error); }
                }
                for (int index = 0; index < quotaOwners.Length; index++) if (quotaStarted[index]) {
                    try { if (!quotaOwners[index].WaitForExit(Math.Max(1, 10000 - (int)close.ElapsedMilliseconds))) { Console.Error.WriteLine("quota child wait incomplete; exact wrapper retained until fixture teardown"); continue; } }
                    catch (Exception error) { Console.Error.WriteLine("quota cleanup wait failed; wrapper retained: " + error); continue; }
                    quotaOwners[index].Dispose();
                }
                // Unconfirmed wrappers stay strongly rooted until fixture teardown;
                // independent monitor/Job ownership remains live throughout.
            } else foreach (Process process in quotaOwners) if (process != null) process.Dispose();
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
