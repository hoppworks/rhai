// Candidate Windows guest payload supervisor. This source is intentionally not
// advertised as production-ready until the native acceptance gates in README.md
// have been run on the authorized Windows guest.
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

internal static class ScopedRunner
{
    private const uint CREATE_SUSPENDED = 0x00000004;
    private const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    private const uint EXTENDED_STARTUPINFO_PRESENT = 0x00080000;
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private const int PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D;
    private const int JobObjectBasicAccountingInformation = 1;
    private const uint WAIT_OBJECT_0 = 0;
    private const uint WAIT_TIMEOUT = 258;
    private const uint CLEANUP_WAIT_MS = 30000;

    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes
    {
        public int nLength; public IntPtr lpSecurityDescriptor; public int bInheritHandle;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] private struct StartupInfo
    {
        public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute;
        public int dwFlags; public short wShowWindow, cbReserved2; public IntPtr lpReserved2;
        public IntPtr hStdInput, hStdOutput, hStdError;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] private struct StartupInfoEx
    {
        public StartupInfo StartupInfo;
        public IntPtr lpAttributeList;
    }
    [StructLayout(LayoutKind.Sequential)] private struct ProcessInformation
    {
        public IntPtr hProcess, hThread; public uint dwProcessId, dwThreadId;
    }
    [StructLayout(LayoutKind.Sequential)] private struct BasicAccounting
    {
        public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
    }
    [StructLayout(LayoutKind.Sequential)] private struct BasicLimitInformation
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)] private struct JobExtendedLimitInformation
    {
        public BasicLimitInformation BasicLimitInformation;
        public IoCounters IoInfo;
        public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObjectW(IntPtr attributes, string name);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateDirectoryW(string path, IntPtr securityAttributes);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref JobExtendedLimitInformation info, uint length);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateProcessW")]
    private static extern bool CreateProcessExW(string app, StringBuilder command, IntPtr procAttr, IntPtr threadAttr,
        bool inherit, uint flags, IntPtr environment, string cwd, ref StartupInfoEx startup, out ProcessInformation process);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref IntPtr size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr attribute, IntPtr value, UIntPtr size, IntPtr previous, IntPtr returnedSize);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern uint WaitForSingleObject(IntPtr handle, uint ms);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetExitCodeProcess(IntPtr process, out uint code);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool TerminateJobObject(IntPtr job, uint code);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool TerminateProcess(IntPtr process, uint code);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool QueryInformationJobObject(IntPtr job, int infoClass, out BasicAccounting info, uint length, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool CloseHandle(IntPtr handle);

    private static Exception Win32(string operation) { return new Win32Exception(Marshal.GetLastWin32Error(), operation); }
    private static void Check(bool ok, string operation) { if (!ok) throw Win32(operation); }

    private static void WaitForProcessExit(IntPtr process, string context)
    {
        uint result = WaitForSingleObject(process, CLEANUP_WAIT_MS);
        if (result == WAIT_TIMEOUT) throw new TimeoutException(context + ": process did not exit within 30 seconds");
        if (result != WAIT_OBJECT_0) throw Win32(context + ": WaitForSingleObject");
    }

    private static void WaitForJobEmpty(IntPtr job, string context)
    {
        var timer = System.Diagnostics.Stopwatch.StartNew();
        while (timer.ElapsedMilliseconds < CLEANUP_WAIT_MS)
        {
            BasicAccounting accounting;
            Check(QueryInformationJobObject(job, JobObjectBasicAccountingInformation, out accounting,
                (uint)Marshal.SizeOf(typeof(BasicAccounting)), IntPtr.Zero), context + ": QueryInformationJobObject");
            if (accounting.ActiveProcesses == 0) return;
            Thread.Sleep(100);
        }
        throw new TimeoutException(context + ": job still has active members after 30 seconds");
    }

    private static IntPtr CreateJobAttributeList(IntPtr job, out IntPtr jobArray)
    {
#if SCOPED_RUNNER_TESTING
        if (Array.IndexOf(Environment.GetCommandLineArgs(), "--test-inject-job-list-failure") >= 0)
            job = new IntPtr(-1); // Pseudo-process handle is not a job; creation must fail closed.
#endif
        IntPtr size = IntPtr.Zero;
        InitializeProcThreadAttributeList(IntPtr.Zero, 1, 0, ref size);
        int error = Marshal.GetLastWin32Error();
        if (size == IntPtr.Zero || error != 122) // ERROR_INSUFFICIENT_BUFFER is the sizing call's expected result.
            throw new Win32Exception(error, "InitializeProcThreadAttributeList(size)");

        IntPtr list = IntPtr.Zero;
        jobArray = IntPtr.Zero;
        bool initialized = false;
        try
        {
            list = Marshal.AllocHGlobal(size);
            jobArray = Marshal.AllocHGlobal(IntPtr.Size);
            if (list == IntPtr.Zero || jobArray == IntPtr.Zero) throw new OutOfMemoryException("Unable to allocate process attribute storage");
            Marshal.WriteIntPtr(jobArray, job);
            Check(InitializeProcThreadAttributeList(list, 1, 0, ref size), "InitializeProcThreadAttributeList");
            initialized = true;
            Check(UpdateProcThreadAttribute(list, 0, new IntPtr(PROC_THREAD_ATTRIBUTE_JOB_LIST), jobArray,
                new UIntPtr((uint)IntPtr.Size), IntPtr.Zero, IntPtr.Zero), "UpdateProcThreadAttribute(JOB_LIST)");
            return list;
        }
        catch (Exception setupFailure)
        {
            var cleanupFailures = new List<Exception>();
            if (initialized)
            {
                try { DeleteProcThreadAttributeList(list); }
                catch (Exception e) { cleanupFailures.Add(e); }
            }
            if (jobArray != IntPtr.Zero)
            {
                try { Marshal.FreeHGlobal(jobArray); }
                catch (Exception e) { cleanupFailures.Add(e); }
            }
            if (list != IntPtr.Zero)
            {
                try { Marshal.FreeHGlobal(list); }
                catch (Exception e) { cleanupFailures.Add(e); }
            }
            jobArray = IntPtr.Zero;
            if (cleanupFailures.Count != 0)
            {
                cleanupFailures.Insert(0, setupFailure);
                throw new AggregateException("Process attribute setup failed and its allocations could not all be released", cleanupFailures);
            }
            throw;
        }
    }

    // Windows command-line quoting for one argv item (CreateProcess has no argv API).
    private static string Quote(string value)
    {
        var b = new StringBuilder("\""); int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1).Append('"'); slashes = 0; continue; }
            b.Append('\\', slashes).Append(c); slashes = 0;
        }
        return b.Append('\\', slashes * 2).Append('"').ToString();
    }

    private static IntPtr EnvironmentBlock(string runtime)
    {
        var vars = new SortedDictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (DictionaryEntry item in Environment.GetEnvironmentVariables())
            vars[(string)item.Key] = (string)item.Value;
        string cargoHome = Path.Combine(runtime, "cargo-home");
        string target = Path.Combine(runtime, "target");
        string temp = Path.Combine(runtime, "tmp");
        Directory.CreateDirectory(cargoHome); Directory.CreateDirectory(target); Directory.CreateDirectory(temp);
        vars["CARGO_HOME"] = cargoHome; vars["CARGO_TARGET_DIR"] = target;
        vars["TEMP"] = temp; vars["TMP"] = temp;
        var block = new StringBuilder();
        foreach (var pair in vars) block.Append(pair.Key).Append('=').Append(pair.Value).Append('\0');
        block.Append('\0');
        IntPtr p = Marshal.StringToHGlobalUni(block.ToString());
        return p;
    }

    private static void CopyTree(string source, string destination)
    {
        Directory.CreateDirectory(destination);
        foreach (string file in Directory.GetFiles(source))
        {
            if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("source tree contains a reparse point: " + file);
            File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), false);
        }
        foreach (string directory in Directory.GetDirectories(source))
        {
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("source tree contains a reparse point: " + directory);
            CopyTree(directory, Path.Combine(destination, Path.GetFileName(directory)));
        }
    }

    private static int Main(string[] args)
    {
#if SCOPED_RUNNER_TESTING
        bool failBeforeResume = args.Contains("--test-fail-before-resume");
        args = args.Where(a => a != "--test-fail-before-resume" && a != "--test-inject-job-list-failure").ToArray();
#endif
        if (args.Length < 4 || args[0] != "--source" || args[2] != "--exe" || Array.IndexOf(args, "--") < 4)
        {
            Console.Error.WriteLine("usage: ScopedRunner.exe --source <source-dir> --exe <relative-exe> -- [args...]");
            return 64;
        }
        int separator = Array.IndexOf(args, "--");
        string source = Path.GetFullPath(args[1]);
        if (!Directory.Exists(source)) { Console.Error.WriteLine("source directory does not exist"); return 64; }
        if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0)
        {
            Console.Error.WriteLine("source root must not be a reparse point");
            return 64;
        }
        string relativeExe = args[3];
        if (Path.IsPathRooted(relativeExe) || relativeExe.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar).Any(p => p == ".."))
        {
            Console.Error.WriteLine("--exe must be a relative path without parent traversal");
            return 64;
        }
#if SCOPED_RUNNER_TESTING
        string fixtureRoot = Environment.GetEnvironmentVariable("RHAI_SCOPED_RUNNER_TEST_ROOT");
        if (String.IsNullOrEmpty(fixtureRoot)) { Console.Error.WriteLine("test runtime root was not supplied"); return 64; }
        string allowedRoot = Path.GetFullPath(fixtureRoot);
#else
        string allowedRoot = Path.GetFullPath(@"C:\RhaiQuality\runs");
#endif
        string runtime = Path.Combine(allowedRoot, "scoped-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(allowedRoot);
        Check(CreateDirectoryW(runtime, IntPtr.Zero), "CreateDirectoryW (exclusive runtime allocation)");
        string stagedSource = Path.Combine(runtime, "source");
        CopyTree(source, stagedSource);
        string exe = Path.GetFullPath(Path.Combine(stagedSource, relativeExe));
        string sourceRoot = Path.GetFullPath(stagedSource) + Path.DirectorySeparatorChar;
        if (!exe.StartsWith(sourceRoot, StringComparison.OrdinalIgnoreCase) || !File.Exists(exe))
        {
            Console.Error.WriteLine("payload executable was not found under the staged source tree");
            return 64;
        }
        IntPtr job = IntPtr.Zero, environment = IntPtr.Zero, attributeList = IntPtr.Zero, jobArray = IntPtr.Zero;
        ProcessInformation pi = new ProcessInformation();
        try
        {
            job = CreateJobObjectW(IntPtr.Zero, null); if (job == IntPtr.Zero) throw Win32("CreateJobObjectW");
            var limits = new JobExtendedLimitInformation
            {
                BasicLimitInformation = new BasicLimitInformation { LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE }
            };
            Check(SetInformationJobObject(job, 9, ref limits, (uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))), "SetInformationJobObject");
            environment = EnvironmentBlock(runtime);
            attributeList = CreateJobAttributeList(job, out jobArray);
            var startup = new StartupInfoEx
            {
                StartupInfo = new StartupInfo { cb = Marshal.SizeOf(typeof(StartupInfoEx)) },
                lpAttributeList = attributeList
            };
            var command = new StringBuilder(Quote(exe));
            for (int i = separator + 1; i < args.Length; i++) command.Append(' ').Append(Quote(args[i]));
            Check(CreateProcessExW(exe, command, IntPtr.Zero, IntPtr.Zero, false,
                EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT,
                environment, runtime, ref startup, out pi), "CreateProcessW(creation-time job assignment)");

            bool inJob;
            Check(IsProcessInJob(pi.hProcess, job, out inJob), "IsProcessInJob(payload, owned job)");
            if (!inJob) throw new InvalidOperationException("payload was not created in the owned job; refusing to resume");

#if SCOPED_RUNNER_TESTING
            if (failBeforeResume)
                throw new InvalidOperationException("injected fixture failure before ResumeThread");
#endif
            uint previousSuspendCount = ResumeThread(pi.hThread);
            if (previousSuspendCount == 0xffffffff) throw Win32("ResumeThread");
            if (previousSuspendCount != 1)
                throw new InvalidOperationException("ResumeThread returned an unexpected prior suspend count: " + previousSuspendCount);
            uint wait = WaitForSingleObject(pi.hProcess, 30 * 60 * 1000);
            if (wait == WAIT_TIMEOUT)
            {
                Check(TerminateJobObject(job, 124), "TerminateJobObject on deadline");
                WaitForProcessExit(pi.hProcess, "deadline cleanup");
                Check(CloseHandle(pi.hProcess), "CloseHandle after deadline cleanup"); pi.hProcess = IntPtr.Zero;
                WaitForJobEmpty(job, "deadline cleanup");
                Console.Error.WriteLine("deadline exceeded; owned job terminated");
                return 124;
            }
            if (wait != WAIT_OBJECT_0) throw Win32("WaitForSingleObject");
            uint exitCode; Check(GetExitCodeProcess(pi.hProcess, out exitCode), "GetExitCodeProcess");
            // The accounting ActiveProcesses count may not decrement until the
            // process object has no external references; release this handle first.
            Check(CloseHandle(pi.hProcess), "CloseHandle after payload exit"); pi.hProcess = IntPtr.Zero;
            BasicAccounting accounting;
            Check(QueryInformationJobObject(job, JobObjectBasicAccountingInformation, out accounting,
                (uint)Marshal.SizeOf(typeof(BasicAccounting)), IntPtr.Zero), "QueryInformationJobObject");
            if (accounting.ActiveProcesses != 0)
            {
                Check(TerminateJobObject(job, 125), "TerminateJobObject for residual members");
                WaitForJobEmpty(job, "residual-member cleanup");
                Console.Error.WriteLine("payload exited with residual job members; terminated them");
                return 125;
            }
            return unchecked((int)exitCode);
        }
        finally
        {
            // CREATE_SUSPENDED and PROC_THREAD_ATTRIBUTE_JOB_LIST make every
            // successfully returned process handle a member of this exact job.
            // Thus every exceptional pre-completion path is cleaned up through
            // that job; no ordinary process-create/assign gap or PID fallback exists.
            Exception cleanupFailure = null;
            try
            {
                if (pi.hProcess != IntPtr.Zero)
                {
                    bool terminated = job != IntPtr.Zero && TerminateJobObject(job, 126);
                    if (!terminated)
                    {
                        cleanupFailure = Win32("TerminateJobObject during incomplete payload setup");
                        // Closing the sole kill-on-close job handle is the kernel
                        // fallback if explicit termination failed.
                        if (job != IntPtr.Zero && CloseHandle(job)) job = IntPtr.Zero;
                        else if (job != IntPtr.Zero) cleanupFailure = new AggregateException(cleanupFailure, Win32("CloseHandle(job fallback)"));
                    }

                    bool processSignaled = false;
                    try { WaitForProcessExit(pi.hProcess, "incomplete payload setup cleanup"); processSignaled = true; }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }

                    if (!processSignaled && job != IntPtr.Zero)
                    {
                        if (CloseHandle(job)) job = IntPtr.Zero;
                        else if (cleanupFailure == null) cleanupFailure = Win32("CloseHandle(job after process wait timeout)");
                        try { WaitForProcessExit(pi.hProcess, "kill-on-close fallback cleanup"); processSignaled = true; }
                        catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    }

                    if (CloseHandle(pi.hProcess)) pi.hProcess = IntPtr.Zero;
                    else if (cleanupFailure == null) cleanupFailure = Win32("CloseHandle after incomplete payload cleanup");

                    if (job != IntPtr.Zero)
                    {
                        try { WaitForJobEmpty(job, "incomplete payload setup cleanup"); }
                        catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    }
#if SCOPED_RUNNER_TESTING
                    if (failBeforeResume && processSignaled && terminated && cleanupFailure == null)
                    {
                        File.WriteAllText(Path.Combine(runtime, "fixture-cleanup-receipt.txt"),
                            "root_process_signaled=true\r\njob_active_processes=0\r\n");
                    }
#endif
                }
            }
            finally
            {
                // Release every retained resource independently. One close
                // failure must not skip the kernel job fallback or later frees.
                if (pi.hThread != IntPtr.Zero)
                {
                    try { if (!CloseHandle(pi.hThread) && cleanupFailure == null) cleanupFailure = Win32("CloseHandle(thread)"); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    pi.hThread = IntPtr.Zero;
                }
                if (pi.hProcess != IntPtr.Zero)
                {
                    try { if (!CloseHandle(pi.hProcess) && cleanupFailure == null) cleanupFailure = Win32("CloseHandle(process)"); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    pi.hProcess = IntPtr.Zero;
                }
                if (attributeList != IntPtr.Zero)
                {
                    try { DeleteProcThreadAttributeList(attributeList); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    try { Marshal.FreeHGlobal(attributeList); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    attributeList = IntPtr.Zero;
                }
                if (jobArray != IntPtr.Zero)
                {
                    try { Marshal.FreeHGlobal(jobArray); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    jobArray = IntPtr.Zero;
                }
                if (environment != IntPtr.Zero)
                {
                    try { Marshal.FreeHGlobal(environment); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    environment = IntPtr.Zero;
                }
                if (job != IntPtr.Zero)
                {
                    try { if (!CloseHandle(job) && cleanupFailure == null) cleanupFailure = Win32("CloseHandle(job)"); }
                    catch (Exception e) { if (cleanupFailure == null) cleanupFailure = e; }
                    job = IntPtr.Zero;
                }
            }
            // Deliberately do not delete runtime here: after supervisor death no independent
            // monitor exists to prove all members are gone and preserve diagnostics first.
            if (cleanupFailure != null) throw cleanupFailure;
        }
    }
}
