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
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
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
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateProcessW(string app, StringBuilder command, IntPtr procAttr, IntPtr threadAttr,
        bool inherit, uint flags, IntPtr environment, string cwd, ref StartupInfo startup, out ProcessInformation process);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
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
        string allowedRoot = Path.GetFullPath(@"C:\RhaiQuality\runs");
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
        IntPtr job = IntPtr.Zero, environment = IntPtr.Zero;
        ProcessInformation pi = new ProcessInformation(); bool assigned = false;
        try
        {
            job = CreateJobObjectW(IntPtr.Zero, null); if (job == IntPtr.Zero) throw Win32("CreateJobObjectW");
            var limits = new JobExtendedLimitInformation
            {
                BasicLimitInformation = new BasicLimitInformation { LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE }
            };
            Check(SetInformationJobObject(job, 9, ref limits, (uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))), "SetInformationJobObject");
            environment = EnvironmentBlock(runtime);
            var startup = new StartupInfo { cb = Marshal.SizeOf(typeof(StartupInfo)) };
            var command = new StringBuilder(Quote(exe));
            for (int i = separator + 1; i < args.Length; i++) command.Append(' ').Append(Quote(args[i]));
            Check(CreateProcessW(exe, command, IntPtr.Zero, IntPtr.Zero, false,
                CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT, environment, runtime, ref startup, out pi), "CreateProcessW");
            Check(AssignProcessToJobObject(job, pi.hProcess), "AssignProcessToJobObject (no fallback; child remains suspended)");
            assigned = true;
            if (ResumeThread(pi.hThread) == 0xffffffff) throw Win32("ResumeThread");
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
            if (pi.hProcess != IntPtr.Zero && !assigned)
            {
                // Assignment failure must never leave an unowned suspended payload.
                bool terminated = TerminateProcess(pi.hProcess, 126);
                int terminationError = terminated ? 0 : Marshal.GetLastWin32Error();
                uint result = WaitForSingleObject(pi.hProcess, CLEANUP_WAIT_MS);
                if (result == WAIT_TIMEOUT)
                {
                    if (!terminated)
                        throw new Win32Exception(terminationError, "TerminateProcess failed for unassigned suspended payload");
                    throw new TimeoutException("unassigned suspended payload did not exit within 30 seconds");
                }
                if (result != WAIT_OBJECT_0)
                    throw Win32("WaitForSingleObject for unassigned suspended payload");
            }
            if (pi.hThread != IntPtr.Zero) CloseHandle(pi.hThread);
            if (pi.hProcess != IntPtr.Zero) CloseHandle(pi.hProcess);
            if (environment != IntPtr.Zero) Marshal.FreeHGlobal(environment);
            if (job != IntPtr.Zero) CloseHandle(job); // KILL_ON_JOB_CLOSE is the crash/interruption fallback.
            // Deliberately do not delete runtime here: after supervisor death no independent
            // monitor exists to prove all members are gone and preserve diagnostics first.
        }
    }
}
