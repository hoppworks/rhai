// Bounded Windows filesystem custody used by the monitor-owned payload worker.
// Source fixtures do not establish native runtime or deletion behavior.
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Microsoft.Win32.SafeHandles;

internal static class WindowsCustodyBackend
{
    // The independent controller selects a fresh session before launching the
    // client. Parsing grants no filesystem authority: PinAuthorizedRoot still
    // pins every ancestor and refuses reparses/mutation before allocation.
    internal static string AuthorizedRoot
    {
        get
        {
            string selected = Environment.GetEnvironmentVariable("AGENT_RUNTIME_DIR");
            string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (String.IsNullOrEmpty(selected) || String.IsNullOrEmpty(profile) ||
                selected.IndexOf('/') >= 0 || selected.EndsWith("\\", StringComparison.Ordinal))
                throw new IOException("an explicit canonical current-user private AGENT_RUNTIME_DIR is required");
            string prefix = Path.Combine(Path.GetFullPath(profile), @".local\share\agent-builds\rhai") + "\\";
            if (!selected.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new IOException("custody root must be inside the current user's private agent-builds/rhai tree");
            string[] parts = selected.Substring(prefix.Length).Split('\\');
            if (parts.Length != 2 || parts[1] != "run" || parts[0].Length == 0 || parts[0].Length > 96)
                throw new IOException("custody root must be <private-project-root>\\<unique-session>\\run");
            string session = parts[0];
            for (int index = 0; index < session.Length; index++)
            {
                char c = session[index];
                bool alphanumeric = IsAsciiLetter(c) || (c >= '0' && c <= '9');
                if ((!alphanumeric && (index == 0 || (c != '.' && c != '_' && c != '-'))) ||
                    (index == session.Length - 1 && c == '.'))
                    throw new IOException("custody session contains an unsupported or ambiguous component");
            }
            // Leave room for the allocation GUID, source and bounded flat inputs.
            if (selected.Length > MaximumPathLength - 80 ||
                !String.Equals(selected, Path.GetFullPath(selected), StringComparison.OrdinalIgnoreCase))
                throw new IOException("custody root exceeds its path budget or is not canonical");
            return selected;
        }
    }
    internal const int MaximumRecordBytes = 4096;
    internal const int MaximumInventoryEntries = 2048;
    internal const long MaximumTotalStagedBytes = 536870912;
    internal const long MaximumSingleStagedFileBytes = 67108864;
    internal const int MaximumSourceDepth = 32;
    private const int MaximumRecords = 64;
    private const int MaximumJournalBytes = MaximumRecords * (MaximumRecordBytes + 15);
    private const ulong LocalFinalizationBudgetMs = 30000;
    internal const int MaximumPathLengthForSpecification = 248;
    private const int MaximumPathLength = MaximumPathLengthForSpecification;
    private const uint FILE_READ_ATTRIBUTES = 0x0080;
    private const uint FILE_LIST_DIRECTORY = 0x00000001;
    private const uint DELETE_ACCESS = 0x00010000;
    private const uint READ_CONTROL = 0x00020000;
    private const uint GENERIC_WRITE = 0x40000000;
    private const uint FILE_SHARE_READ = 0x00000001;
    private const uint FILE_SHARE_WRITE = 0x00000002;
    private const uint FILE_SHARE_DELETE = 0x00000004;
    private const uint GENERIC_READ = 0x80000000;
    private const uint OPEN_EXISTING = 3;
    private const uint CREATE_NEW = 1;
    private const uint FILE_FLAG_WRITE_THROUGH = 0x80000000;
    private const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;
    private const uint FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000;
    private const uint FILE_ATTRIBUTE_DIRECTORY = 0x10;
    private const uint FILE_ATTRIBUTE_READONLY = 0x1;
    private const uint FILE_ATTRIBUTE_REPARSE_POINT = 0x400;
    private const uint FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000;
    private const uint FILE_FLAG_OVERLAPPED = 0x40000000;
    private const uint FILE_ATTRIBUTE_NORMAL = 0x00000080;
    private const int FileAttributeTagInfoClass = 9;
    private const int FileIdInfoClass = 18;
    private const int SE_FILE_OBJECT = 1;
    private const uint DACL_SECURITY_INFORMATION = 0x00000004;
    private const uint FILE_BEGIN = 0;
    private const int FileStandardInfoClass = 1;
    private const int FileBasicInfoClass = 0;
    private const int FileDispositionInfoClass = 4;
    private const int FileIdExtdDirectoryInfoClass = 19;
    private const int FileIdExtdDirectoryRestartInfoClass = 20;
    private const int ERROR_NO_MORE_FILES = 18;
    private const int DirectoryQueryBufferBytes = 65536;
    private const int FileIdExtdHeaderBytes = 88;
    private const int FileIdExtdFileNameLengthOffset = 60;
    private const int FileIdExtdAttributesOffset = 56;
    private const int FileIdExtdIdOffset = 72;
    private const int TransferBufferBytes = 65536;

    [StructLayout(LayoutKind.Sequential)] private struct FileAttributeTagInfo { internal uint Attributes, ReparseTag; }
    [StructLayout(LayoutKind.Sequential)] private struct FileIdInfo { internal ulong VolumeSerialNumber, FileIdLow, FileIdHigh; }
    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { internal int Length; internal IntPtr SecurityDescriptor; internal int InheritHandle; }
    [StructLayout(LayoutKind.Sequential)] private struct FileStandardInfo { internal long AllocationSize, EndOfFile; internal uint NumberOfLinks; [MarshalAs(UnmanagedType.U1)] internal bool DeletePending; [MarshalAs(UnmanagedType.U1)] internal bool Directory; }
    [StructLayout(LayoutKind.Sequential)] private struct FileBasicInfo { internal long CreationTime, LastAccessTime, LastWriteTime, ChangeTime; internal uint Attributes; }
    [StructLayout(LayoutKind.Sequential)] private struct FileDispositionInfo { [MarshalAs(UnmanagedType.U1)] internal bool DeleteFile; }
    private sealed class DirectoryEntrySnapshot
    {
        internal readonly string Name; internal readonly Guid FileId; internal readonly uint Attributes;
        internal DirectoryEntrySnapshot(string name, Guid id, uint attributes) { Name = name; FileId = id; Attributes = attributes; }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share, ref SecurityAttributes security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateDirectoryW")]
    private static extern bool CreateDirectoryW(string path, ref SecurityAttributes security);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileStandardInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileBasicInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadFile(SafeFileHandle file, IntPtr buffer, uint bytesToRead, out uint bytesRead, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetFilePointerEx(SafeFileHandle file, long distance, out long newPosition, uint moveMethod);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileAttributeTagInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileIdInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, IntPtr buffer, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetFileInformationByHandle(SafeFileHandle file, int infoClass, ref FileDispositionInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool WriteFile(SafeFileHandle file, IntPtr buffer, uint bytesToWrite, out uint bytesWritten, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FlushFileBuffers(SafeFileHandle file);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool DuplicateHandle(IntPtr sourceProcess, SafeFileHandle source,
        IntPtr targetProcess, out SafeFileHandle duplicate, uint desiredAccess, bool inherit, uint options);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern uint GetDriveTypeW(string rootPath);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string sddl, uint revision, out IntPtr descriptor, out uint size);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr LocalFree(IntPtr memory);
    [DllImport("kernel32.dll")] private static extern ulong GetTickCount64();

    // Shared by RuntimeAllocation and the enclosing bounded-copy/readback
    // helpers below. Keeping this at the backend scope makes the deadline
    // guard available to both call-site scopes without changing its behavior.
    private static void EnsureFinalizationBudget(ulong deadline, string phase)
    {
        if (deadline == 0) throw new InvalidOperationException("local outcome finalization requires a finite monotonic deadline");
        if (GetTickCount64() < deadline) return;
        throw new TimeoutException(phase + " exceeded the shared local finalization deadline");
    }

    private static void EnsureFinalizationBudgetIfSet(ulong deadline, string phase)
    {
        if (deadline != 0) EnsureFinalizationBudget(deadline, phase);
    }

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityInfo(SafeFileHandle handle, int objectType, uint info,
        out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr descriptor);
    [DllImport("advapi32.dll", SetLastError = true)] private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);

    internal sealed class FileIdentity
    {
        internal readonly ulong VolumeSerial;
        internal readonly Guid FileId;
        internal FileIdentity(ulong volume, Guid fileId) { VolumeSerial = volume; FileId = fileId; }
        internal bool SameAs(FileIdentity other)
        {
            return other != null && VolumeSerial == other.VolumeSerial && FileId == other.FileId;
        }
    }

    internal sealed class PinnedDirectory : IDisposable
    {
        private readonly List<SafeFileHandle> handles;
        private bool ownershipTransferred, disposed;
        internal readonly string Path;
        internal readonly FileIdentity[] AncestorIdentities;
        internal readonly FileIdentity Identity;
        internal SafeFileHandle Handle { get { return handles[handles.Count - 1]; } }

        internal PinnedDirectory(string path, List<SafeFileHandle> ownedHandles)
        {
            Path = path;
            handles = ownedHandles;
            AncestorIdentities = new FileIdentity[handles.Count];
            for (int i = 0; i < handles.Count; i++) AncestorIdentities[i] = ReadIdentity(handles[i]);
            Identity = AncestorIdentities[AncestorIdentities.Length - 1];
        }

        public void Dispose()
        {
            if (ownershipTransferred) return;
            DisposeOwned();
        }

        internal void TransferOwnership()
        {
            if (disposed || ownershipTransferred) throw new InvalidOperationException("pinned directory ownership is unavailable");
            ownershipTransferred = true;
        }

        internal void DisposeOwned()
        {
            if (disposed) return;
            disposed = true;
            Exception failure = null;
            for (int i = handles.Count - 1; i >= 0; i--)
            {
                try { handles[i].Dispose(); }
                catch (Exception e) { if (failure == null) failure = e; }
            }
            if (failure != null) throw new IOException("One or more pinned directory handles failed to close", failure);
        }
    }

    internal sealed class DurableJournal : IDisposable
    {
        private readonly SafeFileHandle handle;
        private int records;
        private bool disposed, failed;
#if SCOPED_RUNNER_TESTING
        private bool failNextAppend;
#endif
        internal readonly string Path;
        internal readonly FileIdentity Identity;
        internal bool IsFaulted { get { return failed; } }

        internal DurableJournal(string path, SafeFileHandle ownedHandle) { Path = path; handle = ownedHandle; Identity = ReadIdentity(ownedHandle); }
        internal void Append(string record)
        {
            if (!TryAppend(record)) throw new InvalidOperationException("journal record rejected by fixed record/count bounds");
        }

        internal bool TryAppend(string record)
        {
            if (disposed || failed || records >= MaximumRecords || record == null || record.Length > MaximumRecordBytes) return false;
#if SCOPED_RUNNER_TESTING
            if (failNextAppend) { failNextAppend = false; failed = true; return false; }
#endif
            for (int i = 0; i < record.Length; i++) if (record[i] < 0x20 || record[i] > 0x7e) return false;
            byte[] body = Encoding.ASCII.GetBytes(record);
            if (body.Length == 0 || body.Length > MaximumRecordBytes) return false;
            string line = body.Length.ToString("X4") + ":" + Crc32(body).ToString("X8") + ":" + record + "\n";
            byte[] frame = Encoding.ASCII.GetBytes(line);
            try
            {
                WriteAll(handle, frame);
                if (!FlushFileBuffers(handle)) throw new IOException("FlushFileBuffers(journal append) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            }
            catch { failed = true; throw; }
            records++;
            return true;
        }

#if SCOPED_RUNNER_TESTING
        internal void FailNextAppendForFixture() { if (disposed || failed) throw new InvalidOperationException("journal is not appendable"); failNextAppend = true; }
#endif

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            Exception failure = null;
            try { if (!FlushFileBuffers(handle)) failure = new IOException("FlushFileBuffers(journal close) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error())); }
            catch (Exception e) { failure = e; }
            try { handle.Dispose(); }
            catch (Exception e) { if (failure == null) failure = e; }
            if (failure != null) throw failure;
        }
    }

    internal static PinnedDirectory PinAuthorizedRoot()
    {
        return PinDirectory(AuthorizedRoot);
    }

#if SCOPED_RUNNER_TESTING
    internal static PinnedDirectory PinDirectoryForFixture(string path) { return PinDirectory(path); }
#endif

    private static PinnedDirectory PinDirectory(string path)
    {
        if (String.IsNullOrEmpty(path) || path.Length > MaximumPathLength || path.StartsWith(@"\\", StringComparison.Ordinal) ||
            path.StartsWith(@"\\?\", StringComparison.Ordinal) || path.StartsWith(@"\\.\", StringComparison.Ordinal))
            throw new IOException("custody directory must be a bounded local DOS path");
        if (path.Length < 3 || !IsAsciiLetter(path[0]) || path[1] != ':' || path[2] != '\\')
            throw new IOException("custody directory must use an absolute drive-rooted path");
        string rawTail = path.Substring(3);
        if (rawTail.EndsWith("\\", StringComparison.Ordinal)) rawTail = rawTail.Substring(0, rawTail.Length - 1);
        string[] rawComponents = rawTail.Length == 0 ? new string[0] : rawTail.Split(new[] { '\\' }, StringSplitOptions.None);
        for (int i = 0; i < rawComponents.Length; i++)
        {
            try { ValidatePathComponent(rawComponents[i], "custody path"); }
            catch (ArgumentException error) { throw new IOException("custody path contains an unsupported component", error); }
        }
        string full = System.IO.Path.GetFullPath(path);
        if (full.Length > MaximumPathLength || full.Length < 3 || full[1] != ':' || full[2] != '\\')
            throw new IOException("custody directory must be a bounded absolute drive path");
        string drive = full.Substring(0, 3);
        if (path.IndexOf('/') >= 0) throw new IOException("custody directory must use Windows separators");
        if (GetDriveTypeW(drive) != 3) throw new IOException("custody directory must be on a fixed local drive");

        var handles = new List<SafeFileHandle>();
        try
        {
            string current = drive;
            string[] components = full.Substring(3).Split(new[] { '\\' }, StringSplitOptions.RemoveEmptyEntries);
            handles.Add(OpenDirectory(current, false, components.Length == 0));
            for (int i = 0; i < components.Length; i++)
            {
                if (components[i] == "." || components[i] == ".." || components[i].IndexOfAny(new[] { ':', '\0' }) >= 0 ||
                    components[i].EndsWith(".", StringComparison.Ordinal) || components[i].EndsWith(" ", StringComparison.Ordinal))
                    throw new IOException("custody path contains an unsupported component");
                current = System.IO.Path.Combine(current, components[i]);
                handles.Add(OpenDirectory(current, false, i == components.Length - 1));
            }
            return new PinnedDirectory(full.Length == 3 ? full : full.TrimEnd('\\'), handles);
        }
        catch
        {
            for (int i = handles.Count - 1; i >= 0; i--) handles[i].Dispose();
            throw;
        }
    }

    private static bool IsAsciiLetter(char value)
    {
        return (value >= 'A' && value <= 'Z') || (value >= 'a' && value <= 'z');
    }

    private static SafeFileHandle OpenDirectory(string path, bool includeDeleteAccess = false, bool includeListAccess = true)
    {
        uint access = FILE_READ_ATTRIBUTES | READ_CONTROL | (includeDeleteAccess ? DELETE_ACCESS : 0) |
            (includeListAccess ? FILE_LIST_DIRECTORY : 0);
        SafeFileHandle handle = CreateFileW(path, access,
            FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (handle == null || handle.IsInvalid) throw new IOException("CreateFileW(pin directory) failed: " + path,
            new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        try
        {
            FileAttributeTagInfo tag;
            Check(GetFileInformationByHandleEx(handle, FileAttributeTagInfoClass, out tag, (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo");
            if ((tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) == 0 || (tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0)
                throw new IOException("custody path component is not a plain directory: " + path);
            ReadIdentity(handle);
            return handle;
        }
        catch { handle.Dispose(); throw; }
    }

    private static FileIdentity ReadIdentity(SafeFileHandle handle)
    {
        FileIdInfo info;
        Check(GetFileInformationByHandleEx(handle, FileIdInfoClass, out info, (uint)Marshal.SizeOf(typeof(FileIdInfo))), "FileIdInfo");
        byte[] bytes = new byte[16];
        Buffer.BlockCopy(BitConverter.GetBytes(info.FileIdLow), 0, bytes, 0, 8);
        Buffer.BlockCopy(BitConverter.GetBytes(info.FileIdHigh), 0, bytes, 8, 8);
        return new FileIdentity(info.VolumeSerialNumber, new Guid(bytes));
    }

    // FILE_ID_EXTD_DIR_INFO returns the full 128-bit file ID (information
    // classes 19/20). Its offsets and 88-byte fixed header follow the documented
    // Windows layout. Validate each variable-length record before reading it.
    private static List<DirectoryEntrySnapshot> ReadDirectoryEntries(SafeFileHandle directory, string path,
        int entryLimit, ref int observed, bool countTowardLimit = true)
    {
        if (IntPtr.Size != 8) throw new IOException("runtime disposition requires the reviewed 64-bit Windows record layout");
        var result = new List<DirectoryEntrySnapshot>();
        IntPtr buffer = Marshal.AllocHGlobal(DirectoryQueryBufferBytes);
        try
        {
            bool first = true;
            int parsedRecords = 0;
            while (true)
            {
                int infoClass = first ? FileIdExtdDirectoryRestartInfoClass : FileIdExtdDirectoryInfoClass;
                first = false;
                if (!GetFileInformationByHandleEx(directory, infoClass, buffer, DirectoryQueryBufferBytes))
                {
                    int error = Marshal.GetLastWin32Error();
                    if (error == ERROR_NO_MORE_FILES) break;
                    throw new IOException("pinned directory enumeration failed: " + path,
                        new System.ComponentModel.Win32Exception(error));
                }

                int offset = 0;
                while (true)
                {
                    if (offset < 0 || offset > DirectoryQueryBufferBytes - FileIdExtdHeaderBytes)
                        throw new IOException("directory enumeration returned a truncated native record: " + path);
                    uint next = unchecked((uint)Marshal.ReadInt32(buffer, offset));
                    uint attrs = unchecked((uint)Marshal.ReadInt32(buffer, offset + FileIdExtdAttributesOffset));
                    int nameBytes = Marshal.ReadInt32(buffer, offset + FileIdExtdFileNameLengthOffset);
                    if (nameBytes < 0 || (nameBytes & 1) != 0 || nameBytes > 510 ||
                        nameBytes > DirectoryQueryBufferBytes - offset - FileIdExtdHeaderBytes)
                        throw new IOException("directory enumeration returned an invalid filename length: " + path);
                    byte[] fileIdBytes = new byte[16];
                    Marshal.Copy(IntPtr.Add(buffer, offset + FileIdExtdIdOffset), fileIdBytes, 0, fileIdBytes.Length);
                    Guid fileId = new Guid(fileIdBytes);
                    string name = Marshal.PtrToStringUni(IntPtr.Add(buffer, offset + FileIdExtdHeaderBytes), nameBytes / 2);
                    if (String.IsNullOrEmpty(name))
                        throw new IOException("directory enumeration returned an unsupported entry name: " + path);
                    parsedRecords++;
                    if (parsedRecords > entryLimit)
                        throw new IOException(entryLimit == MaximumInventoryEntries
                            ? "runtime inventory exceeds the fixed entry bound: " + path
                            : "runtime inventory exceeds the fixture limit: " + path);
                    if (countTowardLimit)
                    {
                        observed++;
                        if (observed > entryLimit)
                            throw new IOException(entryLimit == MaximumInventoryEntries
                                ? "runtime inventory exceeds the fixed entry bound: " + path
                                : "runtime inventory exceeds the fixture limit: " + path);
                    }
                    if (name != "." && name != "..")
                    {
                        ValidateSourceComponent(name);
                        result.Add(new DirectoryEntrySnapshot(name, fileId, attrs));
                    }
                    // Dot pseudoentries count toward the work bound but are
                    // neither validated as ordinary names nor opened/deleted.
                    if (next == 0) break;
                    uint minimumNext = (uint)((FileIdExtdHeaderBytes + nameBytes + 7) & ~7);
                    if ((next & 7) != 0 || next < minimumNext ||
                        next > DirectoryQueryBufferBytes - offset - FileIdExtdHeaderBytes)
                        throw new IOException("directory enumeration returned an invalid next-record offset: " + path);
                    offset = checked(offset + (int)next);
                }
            }
            return result;
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private static SafeFileHandle OpenDispositionEntry(string path)
    {
        SafeFileHandle handle = CreateFileW(path, DELETE_ACCESS | READ_CONTROL | FILE_READ_ATTRIBUTES | GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (handle == null || handle.IsInvalid)
            throw new IOException("CreateFileW(open no-follow runtime entry) failed: " + path,
                new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        return handle;
    }

    private static void MarkForDisposition(SafeFileHandle handle, string description)
    {
        // FILE_DISPOSITION_INFO.DeleteFile is a native one-byte BOOLEAN.
        // Information class 4 requires DELETE access and takes effect on close.
        var info = new FileDispositionInfo { DeleteFile = true };
        Check(SetFileInformationByHandle(handle, FileDispositionInfoClass, ref info,
            (uint)Marshal.SizeOf(typeof(FileDispositionInfo))), "SetFileInformationByHandle(FileDispositionInfo) " + description);
    }

    private static bool DirectoryEntryExists(SafeFileHandle parent, string parentPath, string name, int limit)
    {
        int observed = 0;
        List<DirectoryEntrySnapshot> entries = ReadDirectoryEntries(parent, parentPath, limit, ref observed);
        for (int i = 0; i < entries.Count; i++)
            if (String.Equals(entries[i].Name, name, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private static bool HasUsable128BitFileId(Guid value)
    {
        if (value == Guid.Empty) return false;
        byte[] bytes = value.ToByteArray();
        for (int i = 0; i < bytes.Length; i++)
            if (bytes[i] != 0xff) return true;
        return false;
    }

    internal enum AllocationState { IntentFlushed, Created, Verified, IdentityRecorded, FailedBeforeCreation, FailedRetained }
    internal enum StagingState { NotStarted, Copying, Verifying, Staged, FailedRetained }
    internal enum PayloadSupervisionOutcome { PayloadExited, MonitorStopped, TransitionFailed }
    internal enum RuntimeDispositionState { NotStarted, Blocked, Removing, PartialRetained, Unknown, Removed }
    internal enum DispositionFailurePoint
    {
        None
#if SCOPED_RUNNER_TESTING
        , AfterFirstDisposition, Readback, IdentityMismatch
#endif
    }

    internal sealed class StagedEntry
    {
        internal readonly string RelativePath;
        internal readonly bool IsDirectory;
        internal readonly FileIdentity Identity;
        internal readonly long Length, LastWriteTime;
        internal readonly uint Attributes;
        internal readonly string ContentDigest;
        internal StagedEntry(string path, bool directory, FileIdentity identity, long length, long lastWrite, uint attributes, string digest)
        {
            RelativePath = path; IsDirectory = directory; Identity = identity; Length = length;
            LastWriteTime = lastWrite; Attributes = attributes; ContentDigest = digest;
        }
        internal bool SameAs(StagedEntry other)
        {
            return other != null && String.Equals(RelativePath, other.RelativePath, StringComparison.OrdinalIgnoreCase) &&
                IsDirectory == other.IsDirectory && Identity.SameAs(other.Identity) && Length == other.Length &&
                LastWriteTime == other.LastWriteTime && Attributes == other.Attributes &&
                String.Equals(ContentDigest, other.ContentDigest, StringComparison.Ordinal);
        }
    }

    // Owns the pinned parent, journal, and (after creation) runtime handle for
    // the complete allocation attempt. Disposal closes handles only; it never
    // removes a runtime or turns an uncertain attempt into a receipt.
    internal sealed class RuntimeAllocation : IDisposable
    {
        private readonly PinnedDirectory parent;
        private readonly DurableJournal journal;
        private readonly Guid invocationId;
        private readonly string userSid;
#if SCOPED_RUNNER_TESTING
        private readonly bool injectIdentityFailure;
        private Action<string> fixtureEvidenceAfterCopy;
#endif
        private SafeFileHandle runtimeHandle;
        private SafeFileHandle stagedExecutableHandle;
        private readonly List<SafeFileHandle> stagedExecutableParentPins = new List<SafeFileHandle>();
        private FileIdentity stagedExecutableIdentity;
        private string stagedExecutableRelativePath;
        private bool disposed;
        private bool outcomeRecordFlushed;
        private bool lifecycleDiagnosticsFlushed;
        private bool lifecycleOperationFailed;
        private bool lifecycleCleanupFailed;
        private ulong lifecycleDiagnosticsDeadline;
        private LeaseMonitor.ExactJobClosureProof lifecycleClosureProof;
        private string lifecycleOperationDiagnostic, lifecycleCleanupDiagnostic;
        private long stagedSourceBytes;
        private long payloadLogBytes;
        private string payloadEvidencePath;
        private FileIdentity payloadEvidenceIdentity;
        private FileIdentity payloadStdoutIdentity,payloadStderrIdentity;
        private bool evidenceCaptureStarted;
        private bool evidenceCaptureComplete;
        private PayloadEvidenceReceipt payloadEvidenceReceipt;
        private ulong outcomeFinalizationDeadline;
        private OutcomeMetadataReceipt outcomeMetadataReceipt;
        private uint? recordedPayloadExitCode;
        private PayloadSupervisionOutcome? recordedSupervisionOutcome;
        private LeaseMonitor.ExactJobClosureProof recordedClosureProof;
        private int dispositionEntries;
        private int dispositionCount;
        internal readonly string RuntimePath;
        internal readonly string JournalPath;
        internal readonly FileIdentity EvidenceIdentity;
        internal readonly FileIdentity JournalIdentity;
        internal FileIdentity RuntimeIdentity { get; private set; }
        internal AllocationState State { get; private set; }
        internal string Failure { get; private set; }
        internal bool IsAclVerified { get; private set; }
        internal bool IsIdentityRecorded { get { return State == AllocationState.IdentityRecorded; } }
        internal StagingState StageStatus { get; private set; }
        internal RuntimeDispositionState DispositionState { get; private set; }
        internal bool IsStaged { get { return StageStatus == StagingState.Staged; } }
        internal long StagedSourceBytes { get { return stagedSourceBytes; } }
        internal static long RemainingEvidenceBytes(long stagedBytes, long alreadySavedBytes)
        {
            if(stagedBytes<0 || stagedBytes>MaximumTotalStagedBytes || alreadySavedBytes<0 || alreadySavedBytes>MaximumTotalStagedBytes-stagedBytes)
                throw new IOException("staged source plus payload evidence exceeds the shared fixed storage bound");
            return MaximumTotalStagedBytes-stagedBytes-alreadySavedBytes;
        }

        internal sealed class PayloadLogHandles : IDisposable
        {
            internal readonly SafeFileHandle StandardOutput, StandardError;
            internal readonly string EvidencePath;
            internal readonly FileIdentity EvidenceIdentity;
            internal PayloadLogHandles(SafeFileHandle stdout,SafeFileHandle stderr,string path,FileIdentity identity)
            { StandardOutput=stdout; StandardError=stderr; EvidencePath=path; EvidenceIdentity=identity; }
            public void Dispose()
            {
                Exception failure=null;
                try { if(StandardOutput!=null) StandardOutput.Dispose(); } catch(Exception error) { failure=error; }
                try { if(StandardError!=null) StandardError.Dispose(); } catch(Exception error) { if(failure==null) failure=error; }
                if(failure!=null) throw new IOException("payload log handle close failed",failure);
            }
        }

        internal PayloadLogHandles CreatePayloadLogHandles()
        {
            lock(this)
            {
                if(disposed || !IsStaged || State!=AllocationState.IdentityRecorded || evidenceCaptureStarted || RuntimeIdentity==null || !ReadIdentity(runtimeHandle).SameAs(RuntimeIdentity))
                    throw new InvalidOperationException("payload evidence setup requires the live staged runtime allocation");
                string path=System.IO.Path.Combine(parent.Path,".scoped-evidence-"+invocationId.ToString("N"));
                if(path.Length>MaximumPathLength) throw new IOException("payload evidence path exceeds the fixed bound");
                CreateDestinationDirectory(path);
                SafeFileHandle root=OpenDirectory(path);
                SafeFileHandle stdout=null,stderr=null;
                try
                {
                    SecurityIdentifier user; using(WindowsIdentity current=WindowsIdentity.GetCurrent()) user=current==null ? null : current.User;
                    if(user==null) throw new IOException("current user SID unavailable for payload evidence directory");
                    VerifyProtectedDacl(root,user,AceFlags.ContainerInherit|AceFlags.ObjectInherit,"payload evidence directory");
                    FileIdentity identity=ReadIdentity(root);
                    stdout=CreateDestinationFile(System.IO.Path.Combine(path,"stdout.log"));
                    stderr=CreateDestinationFile(System.IO.Path.Combine(path,"stderr.log"));
                    payloadStdoutIdentity=ReadIdentity(stdout); payloadStderrIdentity=ReadIdentity(stderr);
                    payloadEvidencePath=path; payloadEvidenceIdentity=identity; evidenceCaptureStarted=true;
                    return new PayloadLogHandles(stdout,stderr,path,identity);
                }
                catch { if(stdout!=null) stdout.Dispose(); if(stderr!=null) stderr.Dispose(); throw; }
                finally { root.Dispose(); }
            }
        }

        internal bool TryChargePayloadLogBytes(long count)
        {
            lock(this)
            {
                if(count<0 || count>MaximumTotalStagedBytes-stagedSourceBytes-payloadLogBytes) return false;
                payloadLogBytes=checked(payloadLogBytes+count); return true;
            }
        }

        internal long PayloadLogBytes { get { lock(this) return payloadLogBytes; } }
        internal string PayloadEvidencePath { get { return payloadEvidencePath; } }
        internal FileIdentity PayloadEvidenceIdentity { get { return payloadEvidenceIdentity; } }
        internal SafeFileHandle StagedExecutableHandle { get { return stagedExecutableHandle; } }
        internal FileIdentity StagedExecutableIdentity { get { return stagedExecutableIdentity; } }
        internal string StagedExecutableRelativePath { get { return stagedExecutableRelativePath; } }

#if SCOPED_RUNNER_TESTING
        internal sealed class NoPayloadAuthorization
        {
            private NoPayloadAuthorization() { }
            internal static NoPayloadAuthorization Create() { return new NoPayloadAuthorization(); }
        }
#endif

        internal sealed class OutcomeMetadataReceipt
        {
            internal readonly PayloadSupervisionOutcome SupervisionOutcome;
            internal readonly uint? PayloadExitCode;
            internal readonly bool LocalMetadataSaved, PayloadEvidenceSaved, HostExported;
            internal readonly ulong Deadline;
            private readonly RuntimeAllocation allocation;
            private readonly FileIdentity runtimeIdentity;
            private readonly LeaseMonitor.ExactJobClosureProof closureProof;
            private readonly PayloadEvidenceReceipt payloadEvidence;
            private OutcomeMetadataReceipt(RuntimeAllocation owner, LeaseMonitor.ExactJobClosureProof proof,
                uint? exitCode, PayloadSupervisionOutcome supervision, ulong deadline,PayloadEvidenceReceipt evidence)
            {
                allocation=owner; runtimeIdentity=owner.RuntimeIdentity; closureProof=proof;
                payloadEvidence=evidence;
                PayloadExitCode=exitCode; SupervisionOutcome=supervision;
                LocalMetadataSaved=true; PayloadEvidenceSaved=evidence!=null; HostExported=false; Deadline=deadline;
            }
            internal static OutcomeMetadataReceipt FromVerifiedOwner(RuntimeAllocation owner,
                LeaseMonitor.ExactJobClosureProof proof, uint? exitCode, PayloadSupervisionOutcome supervision, ulong deadline,PayloadEvidenceReceipt evidence)
            {
                if(owner==null || !owner.outcomeRecordFlushed || !owner.lifecycleDiagnosticsFlushed || owner.lifecycleOperationFailed || owner.lifecycleCleanupFailed ||
                    owner.lifecycleDiagnosticsDeadline!=deadline || owner.journal==null || owner.journal.IsFaulted ||
                    owner.RuntimeIdentity==null || deadline==0 || owner.outcomeFinalizationDeadline!=deadline ||
                    !Nullable.Equals(owner.recordedPayloadExitCode,exitCode) || owner.recordedSupervisionOutcome!=supervision ||
                    !Object.ReferenceEquals(owner.recordedClosureProof,proof) || proof==null || !proof.Authorizes(owner,owner.RuntimeIdentity))
                    throw new InvalidOperationException("only the exact durably recorded allocation outcome can mint a metadata receipt");
                if(evidence!=null && !evidence.Authorizes(owner,owner.RuntimeIdentity,proof,exitCode,supervision,deadline))
                    throw new InvalidOperationException("outcome evidence receipt is not bound to the durable exact-job closure");
                return new OutcomeMetadataReceipt(owner,proof,exitCode,supervision,deadline,evidence);
            }
            internal bool IsBoundTo(RuntimeAllocation owner, LeaseMonitor.ExactJobClosureProof proof,
                uint? exitCode, PayloadSupervisionOutcome supervision, ulong deadline,PayloadEvidenceReceipt evidence)
            {
                return AuthorizesMetadata(owner,owner==null ? null : owner.RuntimeIdentity) &&
                    Object.ReferenceEquals(closureProof,proof) && Nullable.Equals(PayloadExitCode,exitCode) &&
                    SupervisionOutcome==supervision && Deadline==deadline && Object.ReferenceEquals(payloadEvidence,evidence);
            }
            internal bool AuthorizesMetadata(RuntimeAllocation owner, FileIdentity identity)
            {
                return Object.ReferenceEquals(allocation,owner) && runtimeIdentity!=null && runtimeIdentity.SameAs(identity) &&
                    closureProof!=null && closureProof.Authorizes(owner,identity) && LocalMetadataSaved &&
                    !HostExported && owner!=null && owner.outcomeRecordFlushed &&
                    owner.lifecycleDiagnosticsFlushed && !owner.lifecycleOperationFailed && !owner.lifecycleCleanupFailed &&
                    owner.lifecycleDiagnosticsDeadline==Deadline &&
                    owner.outcomeFinalizationDeadline==Deadline && Nullable.Equals(owner.recordedPayloadExitCode,PayloadExitCode) &&
                    owner.recordedSupervisionOutcome==SupervisionOutcome && Object.ReferenceEquals(owner.recordedClosureProof,closureProof) &&
                    PayloadEvidenceSaved==(payloadEvidence!=null) && (payloadEvidence==null || payloadEvidence.Authorizes(owner,identity,closureProof,PayloadExitCode,SupervisionOutcome,Deadline));
            }
        }

        internal sealed class PayloadEvidenceReceipt
        {
            internal readonly string ManifestDigest;
            internal readonly long CapturedBytes;
            internal readonly ulong Deadline;
            internal readonly uint? PayloadExitCode;
            internal readonly PayloadSupervisionOutcome SupervisionOutcome;
            private readonly RuntimeAllocation allocation;
            private readonly FileIdentity runtimeIdentity,evidenceIdentity;
            private readonly LeaseMonitor.ExactJobClosureProof closureProof;
            private PayloadEvidenceReceipt(RuntimeAllocation owner,LeaseMonitor.ExactJobClosureProof proof,string digest,long bytes,uint? exitCode,PayloadSupervisionOutcome supervision,ulong deadline)
            { allocation=owner; runtimeIdentity=owner.RuntimeIdentity; evidenceIdentity=owner.payloadEvidenceIdentity; closureProof=proof; ManifestDigest=digest; CapturedBytes=bytes; PayloadExitCode=exitCode; SupervisionOutcome=supervision; Deadline=deadline; }
            internal static PayloadEvidenceReceipt FromVerifiedOwner(RuntimeAllocation owner,LeaseMonitor.ExactJobClosureProof proof,string digest,long bytes,uint? exitCode,PayloadSupervisionOutcome supervision,ulong deadline)
            {
                if(owner==null || !owner.evidenceCaptureComplete || owner.lifecycleOperationFailed || owner.lifecycleCleanupFailed ||
                    owner.lifecycleDiagnosticsDeadline!=deadline || owner.lifecycleClosureProof==null || !Object.ReferenceEquals(owner.lifecycleClosureProof,proof) ||
                    owner.RuntimeIdentity==null || owner.payloadEvidenceIdentity==null || proof==null || !proof.Authorizes(owner,owner.RuntimeIdentity) ||
                    String.IsNullOrEmpty(digest) || bytes<0 || deadline==0 || owner.payloadEvidenceReceipt!=null)
                    throw new InvalidOperationException("payload evidence receipt requires this allocation's completed readback and exact closure proof");
                return new PayloadEvidenceReceipt(owner,proof,digest,bytes,exitCode,supervision,deadline);
            }
            internal bool Authorizes(RuntimeAllocation owner,FileIdentity identity,LeaseMonitor.ExactJobClosureProof proof,uint? exitCode,PayloadSupervisionOutcome supervision,ulong deadline)
            {
                return Object.ReferenceEquals(allocation,owner) && runtimeIdentity!=null && runtimeIdentity.SameAs(identity) &&
                    evidenceIdentity!=null && owner!=null && evidenceIdentity.SameAs(owner.payloadEvidenceIdentity) &&
                    Object.ReferenceEquals(closureProof,proof) && proof!=null && proof.Authorizes(owner,identity) && Deadline==deadline &&
                    Nullable.Equals(PayloadExitCode,exitCode) && SupervisionOutcome==supervision &&
                    owner.evidenceCaptureComplete && Object.ReferenceEquals(owner.payloadEvidenceReceipt,this);
            }
        }

#if SCOPED_RUNNER_TESTING
        internal static NoPayloadAuthorization NoPayloadAuthorizationForFixture() { return NoPayloadAuthorization.Create(); }
        internal static ulong ExpiredFinalizationDeadlineForFixture()
        { return GetTickCount64()-1; }
        internal void FailNextJournalAppendForFixture() { journal.FailNextAppendForFixture(); }
        internal void SetEvidenceReadbackMutationForFixture(Action<string> mutation)
        { fixtureEvidenceAfterCopy=mutation ?? throw new ArgumentNullException("mutation"); }
        internal void CorruptEvidenceIdentityForFixture()
        {
            if(payloadEvidenceIdentity==null) throw new InvalidOperationException("payload evidence identity is unavailable");
            payloadEvidenceIdentity=new FileIdentity(payloadEvidenceIdentity.VolumeSerial^1UL,payloadEvidenceIdentity.FileId);
        }
        internal bool RemoveRuntimeForFixture(NoPayloadAuthorization authorization, CancellationToken cancellationToken,
            DispositionFailurePoint failurePoint)
        {
            return RemoveRuntimeCore(authorization, cancellationToken, failurePoint, MaximumInventoryEntries, MaximumSourceDepth,0);
        }
        internal bool RemoveRuntimeForFixture(NoPayloadAuthorization authorization, CancellationToken cancellationToken,
            DispositionFailurePoint failurePoint, int fixtureEntryLimit, int fixtureDepthLimit)
        {
            if (fixtureEntryLimit < 0 || fixtureDepthLimit < 0) throw new ArgumentOutOfRangeException("fixture limits");
            return RemoveRuntimeCore(authorization, cancellationToken, failurePoint, fixtureEntryLimit, fixtureDepthLimit,0);
        }
#endif

        // The monitor staging worker can own a RuntimeAllocation, but no
        // production caller can authorize removal without exact-job closure
        // proof. The typed future gate is intentionally unconstructible
        // outside that monitor; a job-empty boolean or PID is never evidence.
        internal bool RemoveRuntimeAfterExactJobClosure(LeaseMonitor.ExactJobClosureProof proof, CancellationToken cancellationToken)
        {
            if (proof == null || !proof.Authorizes(this, RuntimeIdentity))
            {
                Failure = AllocationDiagnostic("runtime disposition lacks a monitor-issued exact-job closure proof", RuntimePath, JournalPath);
                DispositionState = RuntimeDispositionState.Blocked;
                return false;
            }
            Failure = AllocationDiagnostic("runtime disposition requires bounded payload logs, results, and manifest saved after exact-job closure", RuntimePath, JournalPath);
            DispositionState = RuntimeDispositionState.Blocked;
            return false;
        }

        internal static ulong StartLocalFinalizationDeadline()
        { return GetTickCount64()+LocalFinalizationBudgetMs; }

        private static void EnsureRemovalBudget(CancellationToken cancellationToken,ulong deadline,string phase)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(deadline!=0 && GetTickCount64()>=deadline)
                throw new TimeoutException(phase+" exceeded the shared local finalization deadline");
        }

        internal OutcomeMetadataReceipt RecordLocalOutcomeMetadata(LeaseMonitor.ExactJobClosureProof proof,
            uint? payloadExitCode, PayloadSupervisionOutcome supervision, ulong deadline,PayloadEvidenceReceipt evidenceReceipt=null)
        {
            lock(this)
            {
                if(outcomeMetadataReceipt!=null)
                {
                    if(outcomeMetadataReceipt.IsBoundTo(this,proof,payloadExitCode,supervision,deadline,evidenceReceipt)) return outcomeMetadataReceipt;
                    throw new InvalidOperationException("outcome metadata receipt is already bound to another proof or deadline");
                }
                if(disposed || State!=AllocationState.IdentityRecorded || RuntimeIdentity==null || journal==null || journal.IsFaulted || !lifecycleDiagnosticsFlushed || lifecycleOperationFailed || lifecycleCleanupFailed || lifecycleDiagnosticsDeadline!=deadline ||
                    proof==null || !proof.Authorizes(this,RuntimeIdentity))
                    throw new InvalidOperationException("local outcome requires flushed lifecycle diagnostics, a live identity-recorded allocation, and its exact-job closure proof");
                if(evidenceReceipt!=null && !evidenceReceipt.Authorizes(this,RuntimeIdentity,proof,payloadExitCode,supervision,deadline))
                    throw new InvalidOperationException("local outcome evidence belongs to another allocation, proof, or deadline");
                if(outcomeRecordFlushed) throw new IOException("outcome metadata was durably written after its finalization deadline; runtime retained");
                EnsureFinalizationBudget(deadline,"before outcome metadata append");
                outcomeFinalizationDeadline=deadline;
                recordedPayloadExitCode=payloadExitCode;
                recordedSupervisionOutcome=supervision;
                recordedClosureProof=proof;
                string exit=payloadExitCode.HasValue ? payloadExitCode.Value.ToString("X8") : "NONE";
                string record="OUTCOME|"+invocationId.ToString("N")+"|"+FormatIdentity(RuntimeIdentity)+"|payload="+exit+
                    "|supervision="+supervision.ToString()+"|cleanup=CONFIRMED|diagnostics_saved=1|local_metadata_saved=1|payload_evidence_saved="+(evidenceReceipt==null ? "0" : "1")+
                    "|evidence="+(evidenceReceipt==null ? "NONE" : evidenceReceipt.ManifestDigest)+"|evidence_identity="+(evidenceReceipt==null ? "NONE" : FormatIdentity(payloadEvidenceIdentity))+
                    "|evidence_bytes="+(evidenceReceipt==null ? "0" : evidenceReceipt.CapturedBytes.ToString())+"|host_exported=0|runtime_removed=0";
                journal.Append(record); // DurableJournal bounds, frames, and flushes each record.
                outcomeRecordFlushed=true;
                EnsureFinalizationBudget(deadline,"after outcome metadata flush");
                outcomeMetadataReceipt=OutcomeMetadataReceipt.FromVerifiedOwner(this,proof,payloadExitCode,supervision,deadline,evidenceReceipt);
                return outcomeMetadataReceipt;
            }
        }

        internal PayloadEvidenceReceipt CapturePayloadEvidence(LeaseMonitor.ExactJobClosureProof proof,
            uint? payloadExitCode,PayloadSupervisionOutcome supervision,ulong deadline)
        {
            lock(this)
            {
                if(payloadEvidenceReceipt!=null)
                {
                    if(payloadEvidenceReceipt.Authorizes(this,RuntimeIdentity,proof,payloadExitCode,supervision,deadline)) return payloadEvidenceReceipt;
                    throw new InvalidOperationException("payload evidence is already bound to another closure proof or deadline");
                }
                if(disposed || !IsStaged || State!=AllocationState.IdentityRecorded || RuntimeIdentity==null || runtimeHandle==null ||
                    journal==null || journal.IsFaulted || !lifecycleDiagnosticsFlushed || lifecycleOperationFailed || lifecycleCleanupFailed ||
                    lifecycleDiagnosticsDeadline!=deadline || proof==null || !proof.Authorizes(this,RuntimeIdentity) || supervision==PayloadSupervisionOutcome.TransitionFailed)
                    throw new InvalidOperationException("payload evidence requires a successful outcome, exact closure proof, and live allocation journal");
                EnsureFinalizationBudget(deadline,"before payload evidence inventory");
                if(payloadEvidencePath==null || payloadEvidenceIdentity==null || !ReadIdentity(runtimeHandle).SameAs(RuntimeIdentity))
                    throw new IOException("payload evidence root or exact runtime identity is unavailable");
                using(SafeFileHandle evidenceRoot=OpenDirectory(payloadEvidencePath))
                {
                    if(!ReadIdentity(evidenceRoot).SameAs(payloadEvidenceIdentity)) throw new IOException("payload evidence root identity changed before capture");
                    string snapshotPath=Path.Combine(payloadEvidencePath,"runtime");
                    if(snapshotPath.Length>MaximumPathLength) throw new IOException("payload snapshot path exceeds fixed bound");
                    CreateDestinationDirectory(snapshotPath);
                    using(PinnedDirectory source=PinSingleDirectory(RuntimePath,DuplicatePinnedHandle(runtimeHandle)))
                    using(SafeFileHandle snapshot=OpenDirectory(snapshotPath))
                    {
                        if(!source.Identity.SameAs(RuntimeIdentity)) throw new IOException("runtime identity changed before evidence snapshot");
                        var sourceManifest=new List<StagedEntry>();
                        var sourceIdentities=new HashSet<string>(StringComparer.Ordinal);
                        AddUniqueIdentity(sourceIdentities,source.Identity,"runtime evidence root");
                        sourceManifest.Add(ReadDirectoryEntry(source,String.Empty));
                        long sourceBytes=0;
                        ScanSourceTree(source,String.Empty,0,sourceManifest,sourceIdentities,ref sourceBytes,CancellationToken.None,deadline);
                        long totalBytes=checked(stagedSourceBytes+payloadLogBytes);
                        if(totalBytes>MaximumTotalStagedBytes-sourceBytes) throw new IOException("complete runtime snapshot plus staged source and payload logs exceeds shared evidence bound");
                        var copiedManifest=new List<StagedEntry> { sourceManifest[0] };
                        var copiedIdentities=new HashSet<string>(StringComparer.Ordinal);
                        AddUniqueIdentity(copiedIdentities,source.Identity,"runtime evidence copy root");
                        var filePins=new List<SafeFileHandle>(); var directoryPins=new List<PinnedDirectory>();
                        try
                        {
                            CopyDirectoryTree(source,String.Empty,snapshotPath,0,sourceManifest[0],copiedManifest,copiedIdentities,
                                ref totalBytes,CancellationToken.None,filePins,directoryPins
#if SCOPED_RUNNER_TESTING
                                ,null
#endif
                                ,deadline);
                            CompareManifests(sourceManifest,copiedManifest);
#if SCOPED_RUNNER_TESTING
                            Action<string> mutation=fixtureEvidenceAfterCopy;
                            fixtureEvidenceAfterCopy=null;
                            if(mutation!=null) mutation(snapshotPath);
#endif
                            EnsureFinalizationBudget(deadline,"after payload evidence copy");
                            var verification=new List<StagedEntry>(); var verificationIds=new HashSet<string>(StringComparer.Ordinal); long verifiedSourceBytes=0;
                            AddUniqueIdentity(verificationIds,source.Identity,"runtime evidence source recheck root");
                            verification.Add(ReadDirectoryEntry(source,String.Empty));
                            ScanSourceTree(source,String.Empty,0,verification,verificationIds,ref verifiedSourceBytes,CancellationToken.None,deadline);
                            if(verifiedSourceBytes!=sourceBytes) throw new IOException("runtime byte count changed during evidence capture");
                            CompareManifests(sourceManifest,verification);
                            Dictionary<string,FileIdentity> readbackIdentities;
                            ValidateDestinationTree(snapshotPath,snapshot,sourceManifest,CancellationToken.None,out readbackIdentities,deadline);
                        }
                        finally
                        {
                            for(int i=0;i<filePins.Count;i++) filePins[i].Dispose();
                            for(int i=0;i<directoryPins.Count;i++) directoryPins[i].DisposeOwned();
                        }
                        string manifestText=SerializeManifest(sourceManifest);
                        byte[] manifestBytes=Encoding.UTF8.GetBytes(manifestText);
                        if(manifestBytes.LongLength>MaximumRecordBytes*MaximumInventoryEntries) throw new IOException("payload evidence manifest exceeds fixed bound");
                        if(totalBytes>MaximumTotalStagedBytes-manifestBytes.LongLength) throw new IOException("manifest exceeds shared source and evidence byte bound");
                        string manifestPath=Path.Combine(payloadEvidencePath,"manifest.txt");
                        string manifestHash=HashText(manifestText);
                        using(SafeFileHandle manifestHandle=CreateDestinationFile(manifestPath))
                        {
                            FileIdentity writtenManifestIdentity=ReadIdentity(manifestHandle);
                            WriteBytes(manifestHandle,manifestBytes);
                            if(!FlushFileBuffers(manifestHandle)) throw new IOException("FlushFileBuffers(payload evidence manifest) failed",new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
                            using(SafeFileHandle readback=OpenEntryForInspection(manifestPath))
                            {
                                if(!ReadIdentity(readback).SameAs(writtenManifestIdentity)) throw new IOException("payload manifest path identity changed after flush");
                                FileStandardInfo standard; Check(GetFileInformationByHandleEx(readback,FileStandardInfoClass,out standard,(uint)Marshal.SizeOf(typeof(FileStandardInfo))),"FileStandardInfo(payload manifest readback)");
                                if(standard.EndOfFile!=manifestBytes.LongLength || !String.Equals(TransferAndHash(readback,null,standard.EndOfFile,false,CancellationToken.None,deadline),manifestHash,StringComparison.Ordinal))
                                    throw new IOException("independent payload manifest readback did not match the flushed manifest");
                            }
                        }
                        long stdoutBytes,stderrBytes;
                        string stdoutHash=HashEvidenceFile(Path.Combine(payloadEvidencePath,"stdout.log"),payloadStdoutIdentity,deadline,out stdoutBytes);
                        string stderrHash=HashEvidenceFile(Path.Combine(payloadEvidencePath,"stderr.log"),payloadStderrIdentity,deadline,out stderrBytes);
                        if(checked(stdoutBytes+stderrBytes)!=payloadLogBytes) throw new IOException("payload log lengths differ from the owner-accounted output byte count");
                        if(supervision==PayloadSupervisionOutcome.TransitionFailed) throw new InvalidOperationException("failed transition cannot produce successful evidence");
                        EnsureFinalizationBudget(deadline,"before payload evidence journal record");
                        string record="EVIDENCE|"+invocationId.ToString("N")+"|"+FormatIdentity(RuntimeIdentity)+"|proof=EXACT|exit="+(payloadExitCode.HasValue?payloadExitCode.Value.ToString("X8"):"NONE")+
                            "|supervision="+supervision.ToString()+"|evidence_identity="+FormatIdentity(payloadEvidenceIdentity)+"|manifest="+manifestHash+"|stdout="+stdoutHash+"|stderr="+stderrHash+"|runtime_bytes="+sourceBytes.ToString()+"|logs_bytes="+payloadLogBytes.ToString()+"|deadline="+deadline.ToString();
                        journal.Append(record);
                        EnsureFinalizationBudget(deadline,"after payload evidence journal flush");
                        totalBytes=checked(totalBytes+manifestBytes.LongLength);
                        evidenceCaptureComplete=true;
                        payloadEvidenceReceipt=PayloadEvidenceReceipt.FromVerifiedOwner(this,proof,manifestHash,totalBytes,payloadExitCode,supervision,deadline);
                        return payloadEvidenceReceipt;
                    }
                }
            }
        }

        // This diagnostic record is deliberately independent of a closure
        // proof. It preserves transition/cleanup failures in the external
        // journal when possible, but never authorizes evidence or removal.
        internal void RecordLifecycleDiagnostics(Exception operationFailure, Exception cleanupFailure,
            LeaseMonitor.ExactJobClosureProof closureProof, ulong deadline)
        {
            lock(this)
            {
                string operation=BoundDiagnostic(operationFailure);
                string cleanup=BoundDiagnostic(cleanupFailure);
                bool closureConfirmed=closureProof!=null && closureProof.Authorizes(this,RuntimeIdentity) && cleanupFailure==null;
                if(lifecycleDiagnosticsFlushed)
                {
                    if(lifecycleDiagnosticsDeadline!=deadline || lifecycleOperationDiagnostic!=operation || lifecycleCleanupDiagnostic!=cleanup ||
                        !Object.ReferenceEquals(lifecycleClosureProof,closureConfirmed ? closureProof : null))
                        throw new InvalidOperationException("lifecycle diagnostic record is already bound to different failures, closure evidence, or deadline");
                    return;
                }
                if(disposed || State!=AllocationState.IdentityRecorded || RuntimeIdentity==null || journal==null || journal.IsFaulted)
                    throw new InvalidOperationException("lifecycle diagnostics require the live external allocation journal");
                if(closureProof!=null && !closureProof.Authorizes(this,RuntimeIdentity))
                    throw new InvalidOperationException("lifecycle closure confirmation belongs to another allocation or identity");
                EnsureFinalizationBudget(deadline,"before lifecycle diagnostics append");
                lifecycleDiagnosticsDeadline=deadline;
                string record="LIFECYCLE|"+invocationId.ToString("N")+"|"+FormatIdentity(RuntimeIdentity)+
                    "|deadline="+deadline.ToString()+"|operation="+operation+"|cleanup="+cleanup+"|cleanup_confirmed="+(closureConfirmed ? "1" : "0");
                journal.Append(record);
                lifecycleDiagnosticsFlushed=true;
                lifecycleOperationFailed=operationFailure!=null;
                lifecycleCleanupFailed=cleanupFailure!=null;
                lifecycleClosureProof=closureConfirmed ? closureProof : null;
                lifecycleOperationDiagnostic=operation; lifecycleCleanupDiagnostic=cleanup;
                EnsureFinalizationBudget(deadline,"after lifecycle diagnostics flush");
            }
        }

        private static string BoundDiagnostic(Exception error)
        {
            if(error==null) return "NONE";
            string value=error.GetType().Name+":"+error.Message;
            var result=new StringBuilder(Math.Min(value.Length,384));
            for(int i=0;i<value.Length && result.Length<384;i++)
            {
                char c=value[i];
                result.Append(c>=0x20 && c<=0x7e && c!='|' ? c : '_');
            }
            return result.ToString();
        }

        internal bool TryRemoveRuntimeAfterOutcomeMetadata(OutcomeMetadataReceipt receipt, CancellationToken cancellationToken)
        {
            if(receipt==null || !receipt.AuthorizesMetadata(this,RuntimeIdentity))
            {
                Failure=AllocationDiagnostic("runtime disposition lacks this allocation's exact outcome metadata receipt",RuntimePath,JournalPath);
                DispositionState=RuntimeDispositionState.Blocked;
                return false;
            }
            if(receipt.Deadline!=outcomeFinalizationDeadline || receipt.Deadline==0)
            {
                Failure=AllocationDiagnostic("runtime disposition receipt has no shared local finalization deadline",RuntimePath,JournalPath);
                DispositionState=RuntimeDispositionState.Blocked;
                return false;
            }
            if(!receipt.PayloadEvidenceSaved || !receipt.AuthorizesMetadata(this,RuntimeIdentity))
            {
                Failure=AllocationDiagnostic("runtime disposition remains blocked until bounded payload logs, results, and manifest are saved and read back outside the runtime",RuntimePath,JournalPath);
                DispositionState=RuntimeDispositionState.Blocked;
                return false;
            }
            return RemoveRuntimeCore(receipt,cancellationToken,DispositionFailurePoint.None,MaximumInventoryEntries,MaximumSourceDepth,receipt.Deadline);
        }

        internal bool RemoveRuntime()
        {
            Failure = AllocationDiagnostic("runtime disposition is unavailable until the monitor proves its exact job empty and releases owned process/thread references", RuntimePath, JournalPath);
            DispositionState = RuntimeDispositionState.Blocked;
            return false;
        }

        private bool RemoveRuntimeCore(object authorization, CancellationToken cancellationToken,
            DispositionFailurePoint failurePoint, int entryLimit, int depthLimit, ulong deadline)
        {
            if (disposed || State != AllocationState.IdentityRecorded || RuntimeIdentity == null || runtimeHandle == null ||
                runtimeHandle.IsInvalid || runtimeHandle.IsClosed)
            {
                Failure = AllocationDiagnostic("runtime identity is unrecorded or exact runtime ownership is no longer held; data retained", RuntimePath, JournalPath);
                DispositionState = RuntimeDispositionState.Blocked;
                return false;
            }
            if (!HasFilesystemFixtureAuthorization(authorization))
            {
                Failure = AllocationDiagnostic("runtime disposition authorization is unavailable", RuntimePath, JournalPath);
                DispositionState = RuntimeDispositionState.Blocked;
                return false;
            }

            DispositionState = RuntimeDispositionState.Removing;
            bool rootDispositionMarked = false;
            try
            {
                cancellationToken.ThrowIfCancellationRequested();
                EnsureRemovalBudget(cancellationToken,deadline,"before exact runtime disposition");
#if SCOPED_RUNNER_TESTING
                if (failurePoint == DispositionFailurePoint.IdentityMismatch || !ReadIdentity(runtimeHandle).SameAs(RuntimeIdentity))
#else
                if (!ReadIdentity(runtimeHandle).SameAs(RuntimeIdentity))
#endif
                    throw new IOException("recorded runtime identity differs from the held runtime handle");
                if (!ReadIdentity(parent.Handle).SameAs(EvidenceIdentity))
                    throw new IOException("pinned runtime parent identity differs from the allocation evidence identity");
                if (!HasUsable128BitFileId(RuntimeIdentity.FileId) || !HasUsable128BitFileId(EvidenceIdentity.FileId))
                    throw new IOException("runtime disposition requires usable 128-bit IDs for runtime and evidence parent");
                FileAttributeTagInfo runtimeTag;
                Check(GetFileInformationByHandleEx(runtimeHandle, FileAttributeTagInfoClass, out runtimeTag,
                    (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(runtime disposition)");
                if ((runtimeTag.Attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != FILE_ATTRIBUTE_DIRECTORY)
                    throw new IOException("held runtime is not a plain directory");
                SecurityIdentifier user;
                using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
                if (user == null) throw new IOException("current user SID unavailable during runtime disposition");
                VerifyProtectedDacl(runtimeHandle, user, AceFlags.ContainerInherit | AceFlags.ObjectInherit, "runtime disposition root");

                // Release the staged executable and every parent pin independently.
                // A failed release stops before the durable intent and first mutation.
                SafeCloseStagedExecutable();
                if (!ReadIdentity(runtimeHandle).SameAs(RuntimeIdentity))
                    throw new IOException("runtime identity changed while releasing staged executable pins");
                journal.Append("REMOVE_INTENT|" + invocationId.ToString("N") + "|" + FormatIdentity(RuntimeIdentity) + "|" + FormatIdentity(EvidenceIdentity));
                EnsureRemovalBudget(cancellationToken,deadline,"after removal intent flush");

                dispositionEntries = 0;
                dispositionCount = 0;
                var seen = new HashSet<string>(StringComparer.Ordinal);
                AddUniqueIdentity(seen, RuntimeIdentity, "runtime root");
                RemoveRuntimeDirectoryContents(RuntimePath, runtimeHandle, String.Empty, 0, seen, user,
                    cancellationToken, entryLimit, depthLimit, failurePoint,deadline);

                cancellationToken.ThrowIfCancellationRequested();
                EnsureRemovalBudget(cancellationToken,deadline,"before runtime root disposition");
                MarkForDisposition(runtimeHandle, "runtime root");
                rootDispositionMarked = true;
                runtimeHandle.Dispose();
                runtimeHandle = null;
#if SCOPED_RUNNER_TESTING
                if (failurePoint == DispositionFailurePoint.Readback)
                {
                    DispositionState = RuntimeDispositionState.Unknown;
                    throw new IOException("fixture forced independent runtime absence readback failure");
                }
#endif
                if (DirectoryEntryExists(parent.Handle, parent.Path, System.IO.Path.GetFileName(RuntimePath), MaximumInventoryEntries))
                    throw new IOException("runtime remains visible during independent pinned-parent absence readback");
                EnsureRemovalBudget(cancellationToken,deadline,"after runtime absence readback");
                if (!ReadIdentity(parent.Handle).SameAs(EvidenceIdentity))
                    throw new IOException("pinned runtime parent identity changed before removal receipt");

                journal.Append("REMOVED|" + invocationId.ToString("N") + "|" + FormatIdentity(RuntimeIdentity) + "|" + FormatIdentity(EvidenceIdentity));
                EnsureRemovalBudget(cancellationToken,deadline,"after removal receipt flush");
                DispositionState = RuntimeDispositionState.Removed;
                Failure = null;
                return true;
            }
            catch (Exception error)
            {
                if (DispositionState != RuntimeDispositionState.Unknown)
                    DispositionState = rootDispositionMarked ? RuntimeDispositionState.Unknown : RuntimeDispositionState.PartialRetained;
                Failure = AllocationDiagnostic("runtime disposition " + (rootDispositionMarked ? "readback or receipt is uncertain" : "stopped; runtime retained or partially removed") +
                    ": " + error.GetType().Name + ": " + error.Message, RuntimePath, JournalPath);
                return false;
            }
        }

        private static bool HasFilesystemFixtureAuthorization(object authorization)
        {
#if SCOPED_RUNNER_TESTING
            return authorization is NoPayloadAuthorization || authorization is OutcomeMetadataReceipt;
#else
            return authorization is OutcomeMetadataReceipt;
#endif
        }

        private void RemoveRuntimeDirectoryContents(string directoryPath, SafeFileHandle directoryHandle, string relativeDirectory,
            int depth, HashSet<string> seen, SecurityIdentifier user, CancellationToken cancellationToken,
            int entryLimit, int depthLimit, DispositionFailurePoint failurePoint, ulong deadline)
        {
            EnsureRemovalBudget(cancellationToken,deadline,"during runtime inventory");
            if (depth > depthLimit) throw new IOException("runtime depth exceeds the fixture limit (production bound is fixed)");
            FileIdentity parentIdentity = ReadIdentity(directoryHandle);
            List<DirectoryEntrySnapshot> entries = ReadDirectoryEntries(directoryHandle, directoryPath, entryLimit, ref dispositionEntries);
            for (int i = 0; i < entries.Count; i++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                EnsureRemovalBudget(cancellationToken,deadline,"before runtime entry disposition");
                DirectoryEntrySnapshot listed = entries[i];
                ValidateSourceComponent(listed.Name);
                string relative = relativeDirectory.Length == 0 ? listed.Name : relativeDirectory + "\\" + listed.Name;
                if (relative.Length > MaximumPathLength) throw new IOException("runtime entry path exceeds the fixed path bound: " + relative);
                string path = System.IO.Path.Combine(directoryPath, listed.Name);
                if (path.Length > MaximumPathLength) throw new IOException("runtime entry path exceeds the fixed path bound: " + path);
                SafeFileHandle entry = OpenDispositionEntry(path);
                bool dispositionRequested = false;
                try
                {
                    FileAttributeTagInfo tag;
                    Check(GetFileInformationByHandleEx(entry, FileAttributeTagInfoClass, out tag,
                        (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(runtime entry)");
                    if ((tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0)
                        throw new IOException("runtime reparse point is refused and retained: " + relative);
                    FileIdentity identity = ReadIdentity(entry);
                    if (!HasUsable128BitFileId(listed.FileId) || !HasUsable128BitFileId(identity.FileId) ||
                        identity.VolumeSerial != parentIdentity.VolumeSerial || identity.FileId != listed.FileId)
                        throw new IOException("runtime entry identity changed between pinned-parent enumeration and no-follow open: " + relative);
                    AddUniqueIdentity(seen, identity, "runtime entry " + relative);
                    bool isDirectory = (tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
                    if (isDirectory != ((listed.Attributes & FILE_ATTRIBUTE_DIRECTORY) != 0))
                        throw new IOException("runtime entry type changed after enumeration: " + relative);
                    if ((tag.Attributes & FILE_ATTRIBUTE_READONLY) != 0)
                        throw new IOException("read-only runtime entry is refused without changing attributes: " + relative);
                    VerifyRuntimeEntryDacl(entry, user, isDirectory ? AceFlags.ContainerInherit | AceFlags.ObjectInherit : AceFlags.None,
                        isDirectory ? "runtime directory entry" : "runtime file entry");
                    FileStandardInfo standard;
                    Check(GetFileInformationByHandleEx(entry, FileStandardInfoClass, out standard,
                        (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(runtime entry)");
                    if (standard.DeletePending || standard.Directory != isDirectory || (!isDirectory && standard.NumberOfLinks != 1))
                        throw new IOException("runtime entry has an unexpected type, pending disposition, or hard link: " + relative);
                    if (isDirectory)
                        RemoveRuntimeDirectoryContents(path, entry, relative, depth + 1, seen, user,
                            cancellationToken, entryLimit, depthLimit, failurePoint,deadline);

                    cancellationToken.ThrowIfCancellationRequested();
                    EnsureRemovalBudget(cancellationToken,deadline,"before runtime entry disposition");
                    MarkForDisposition(entry, relative);
                    dispositionRequested = true;
                    entry.Dispose();
                    entry = null;
                    dispositionCount++;
#if SCOPED_RUNNER_TESTING
                    if (failurePoint == DispositionFailurePoint.AfterFirstDisposition && dispositionCount == 1)
                        throw new IOException("fixture injected a partial runtime removal after the first disposition");
#endif
                }
                finally
                {
                    if (entry != null) entry.Dispose();
                }
                // Each directory's final handle-based readback below proves all
                // child names absent after their disposition handles closed.
                if (!dispositionRequested) throw new IOException("runtime entry was not dispositioned: " + relative);
            }
            cancellationToken.ThrowIfCancellationRequested();
            EnsureRemovalBudget(cancellationToken,deadline,"after runtime directory readback");
            List<DirectoryEntrySnapshot> residual = ReadDirectoryEntries(directoryHandle, directoryPath, entryLimit, ref dispositionEntries, false);
            if (residual.Count != 0) throw new IOException("runtime directory acquired or retained entries during bottom-up removal: " + directoryPath);
            if (!ReadIdentity(directoryHandle).SameAs(parentIdentity))
                throw new IOException("pinned runtime directory identity changed during child removal: " + directoryPath);
        }

        internal RuntimeAllocation(PinnedDirectory ownedParent, Guid id
#if SCOPED_RUNNER_TESTING
            , bool failIdentity
#endif
            )
        {
            parent = ownedParent ?? throw new ArgumentNullException("ownedParent");
            invocationId = id;
#if SCOPED_RUNNER_TESTING
            injectIdentityFailure = failIdentity;
#endif
            DurableJournal created = null;
            string path = null;
            RuntimePath = System.IO.Path.Combine(parent.Path, "scoped-" + id.ToString("N"));
            try
            {
                using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
                {
                    if (identity == null || identity.User == null) throw new IOException("current user has no SID");
                    userSid = identity.User.Value;
                }
                if (RuntimePath.Length > MaximumPathLength) throw new IOException("generated runtime path exceeds the fixed path bound");
                created = CreateJournal(parent, out path);
                journal = created;
                JournalPath = path;
                EvidenceIdentity = parent.Identity;
                JournalIdentity = created.Identity;
                string intent = "INTENT|" + id.ToString("N") + "|" + RuntimePath + "|" + JournalPath + "|" + FormatIdentity(EvidenceIdentity) + "|" + FormatIdentity(JournalIdentity);
                if (!journal.TryAppend(intent)) throw new IOException("allocation intent journal record was rejected");
                State = AllocationState.IntentFlushed;
            }
            catch (Exception error)
            {
                if (created != null) { try { created.Dispose(); } catch { } }
                string status = String.IsNullOrEmpty(path) ? "journal not created" : "intent framing may be incomplete; runtime was not created or opened";
                throw new IOException(AllocationDiagnostic("allocation intent setup failed: " + error.Message + "; " + status, RuntimePath, path), error);
            }
        }

        internal bool CreateRuntime()
        {
            if (disposed || State != AllocationState.IntentFlushed) return false;
            IntPtr descriptor = IntPtr.Zero;
            bool directoryCreated = false;
            try
            {
                string sddl = "D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;" + userSid + ")";
                uint size;
                if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, out descriptor, out size))
                    throw new IOException("unable to build protected runtime DACL", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
                var security = new SecurityAttributes { Length = Marshal.SizeOf(typeof(SecurityAttributes)), SecurityDescriptor = descriptor, InheritHandle = 0 };
                if (!CreateDirectoryW(RuntimePath, ref security))
                {
                    State = AllocationState.FailedBeforeCreation;
                    Failure = AllocationDiagnostic("CreateDirectoryW failed; path was not opened or adopted; Win32Error=" + Marshal.GetLastWin32Error(), RuntimePath, JournalPath);
                    return false; // Includes collisions: never open or adopt the existing name.
                }
                directoryCreated = true;
                State = AllocationState.Created;
                runtimeHandle = OpenDirectory(RuntimePath, true);
                VerifyProtectedDacl(runtimeHandle, new SecurityIdentifier(userSid), AceFlags.ContainerInherit | AceFlags.ObjectInherit, "runtime directory");
                IsAclVerified = true;
                RuntimeIdentity = ReadIdentity(runtimeHandle);
                State = AllocationState.Verified;
#if SCOPED_RUNNER_TESTING
                if (injectIdentityFailure) throw new IOException("fixture injected failure before identity journal append");
#endif
                string record = "IDENTITY|" + invocationId.ToString("N") + "|" + FormatIdentity(RuntimeIdentity) + "|" + FormatIdentity(EvidenceIdentity) + "|" + FormatIdentity(JournalIdentity);
                if (!journal.TryAppend(record)) throw new IOException("runtime identity journal record was rejected");
                State = AllocationState.IdentityRecorded;
                return true;
            }
            catch (Exception error)
            {
                State = directoryCreated ? AllocationState.FailedRetained : AllocationState.FailedBeforeCreation;
                Failure = AllocationDiagnostic(error.Message + "; " + (directoryCreated ? "runtime retained with uncertain identity/journal status" : "runtime not created by this attempt"), RuntimePath, JournalPath);
                return false;
            }
            finally { if (descriptor != IntPtr.Zero) LocalFree(descriptor); }
        }

        internal bool StageSourceTree(string sourceRoot, string executableRelativePath, CancellationToken cancellationToken)
        {
            // Syntax is a pure string check and intentionally precedes all I/O.
            string[] executableComponents = ParseExecutableRelativePath(executableRelativePath);
            if (disposed || State != AllocationState.IdentityRecorded || StageStatus != StagingState.NotStarted)
                throw new InvalidOperationException("source staging requires one live identity-recorded allocation");
            StageStatus = StagingState.Copying;
            var initial = new List<StagedEntry>();
            var identities = new HashSet<string>(StringComparer.Ordinal);
            var sourceFilePins = new List<SafeFileHandle>();
            var sourceDirectoryPins = new List<PinnedDirectory>();
            PinnedDirectory sourceAncestors = null;
            PinnedDirectory sourceRootPin = null;
            long totalBytes = 0;
            string phase = "source pin";
            try
            {
                sourceAncestors = PinDirectory(sourceRoot);
                sourceRootPin = PinSingleDirectory(sourceAncestors.Path, OpenDirectory(sourceAncestors.Path));
                {
                    PinnedDirectory source = sourceRootPin;
                    if (!source.Identity.SameAs(sourceAncestors.Identity))
                        throw new IOException("source root identity changed between ancestor and mutation-denying pins");
                    // The root pin proves the leaf is still the same object;
                    // use the complete checked ancestor chain for alias tests.
                    EnsureSourceDoesNotOverlapAllocation(sourceAncestors, parent, runtimeHandle, RuntimePath);
                    phase = "tree copy";
                    AddUniqueIdentity(identities, source.Identity, "source root");
                    StagedEntry sourceRootEntry = ReadDirectoryEntry(source, String.Empty);
                    initial.Add(sourceRootEntry);
#if SCOPED_RUNNER_TESTING
                    string failAt = fixtureFailAtRelativePath;
#else
                    string failAt = null;
#endif
                    CopyDirectoryTree(source, String.Empty, RuntimePath, 0, sourceRootEntry,
                        initial, identities, ref totalBytes, cancellationToken, sourceFilePins, sourceDirectoryPins
#if SCOPED_RUNNER_TESTING
                        , failAt
#endif
                        );
                    cancellationToken.ThrowIfCancellationRequested();
#if SCOPED_RUNNER_TESTING
                    Action<string> hook = fixtureMutationHook;
                    if (hook != null) hook(source.Path);
#endif
                    StageStatus = StagingState.Verifying;
                    phase = "source consistency scan";
                    var final = new List<StagedEntry>();
                    var finalIdentities = new HashSet<string>(StringComparer.Ordinal);
                    long finalBytes = 0;
                    AddUniqueIdentity(finalIdentities, source.Identity, "source root");
                    final.Add(ReadDirectoryEntry(source, String.Empty));
                    ScanSourceTree(source, String.Empty, 0, final, finalIdentities, ref finalBytes, cancellationToken);
                    if (finalBytes != totalBytes) throw new IOException("source total byte count changed during the consistency scan");
                    CompareManifests(initial, final);
                    phase = "staged tree verification";
                    Dictionary<string, FileIdentity> destinationIdentities;
                    ValidateDestinationTree(RuntimePath, runtimeHandle, initial, cancellationToken, out destinationIdentities);
                    phase = "staged executable pin";
                    string requestedExecutable = String.Join("\\", executableComponents);
                    StagedEntry executableEntry = FindExecutableEntry(initial, requestedExecutable);
                    FileIdentity destinationExecutableIdentity;
                    if (!destinationIdentities.TryGetValue(requestedExecutable, out destinationExecutableIdentity))
                        throw new IOException("staged executable disappeared from the destination readback");
                    stagedExecutableHandle = PinStagedExecutable(RuntimePath, executableComponents, destinationExecutableIdentity,
                        out stagedExecutableIdentity, stagedExecutableParentPins);
                    stagedExecutableRelativePath = String.Join("\\", executableComponents);
                    phase = "staged receipt";
                    string digest = ManifestDigest(initial);
                    string receipt = "STAGED|" + invocationId.ToString("N") + "|" + initial.Count.ToString() + "|" +
                        totalBytes.ToString() + "|" + digest + "|" + HashText(stagedExecutableRelativePath) + "|" + FormatIdentity(stagedExecutableIdentity);
                    journal.Append(receipt);
                    stagedSourceBytes=totalBytes;
                    StageStatus = StagingState.Staged;
                    return true;
                }
            }
            catch (Exception error)
            {
                StageStatus = StagingState.FailedRetained;
                string detail = AllocationDiagnostic("staging " + phase + " failed: " + error.GetType().Name + ": " + error.Message, RuntimePath, JournalPath) +
                    "; source=" + BoundPath(sourceRoot);
                Failure = detail;
                try
                {
                    string reason = error.GetType().Name + ":" + error.Message;
                    reason = ToAsciiBounded(reason, 256);
                    journal.TryAppend("STAGE_FAILED|" + invocationId.ToString("N") + "|" + phase.Replace(' ', '_') + "|" + reason);
                }
                catch { /* preserve the original uncertain staging result */ }
                try { SafeCloseStagedExecutable(); } catch { }
                return false;
            }
            finally
            {
                // Keep mutation-denying source handles through the final
                // manifest comparison and durable STAGED receipt, then close
                // every owned handle independently in reverse traversal order.
                for (int i = sourceFilePins.Count - 1; i >= 0; i--) try { sourceFilePins[i].Dispose(); } catch { }
                for (int i = sourceDirectoryPins.Count - 1; i >= 0; i--) try { sourceDirectoryPins[i].DisposeOwned(); } catch { }
                if (sourceRootPin != null) try { sourceRootPin.DisposeOwned(); } catch { }
                if (sourceAncestors != null) try { sourceAncestors.DisposeOwned(); } catch { }
            }
        }

#if SCOPED_RUNNER_TESTING
        private Action<string> fixtureMutationHook;
        internal bool StageSourceTreeForFixture(string sourceRoot, string executableRelativePath, CancellationToken cancellationToken,
            Action<string> beforeFinalRescan, string failAtRelativePath)
        {
            fixtureMutationHook = beforeFinalRescan;
            fixtureFailAtRelativePath = failAtRelativePath;
            try { return StageSourceTree(sourceRoot, executableRelativePath, cancellationToken); }
            finally { fixtureMutationHook = null; fixtureFailAtRelativePath = null; }
        }
        private string fixtureFailAtRelativePath;
#endif

        private void SafeCloseStagedExecutable()
        {
            SafeFileHandle executable = stagedExecutableHandle;
            stagedExecutableHandle = null;
            stagedExecutableIdentity = null;
            Exception failure = null;
            if (executable != null) try { executable.Dispose(); } catch (Exception error) { failure = error; }
            for (int i = stagedExecutableParentPins.Count - 1; i >= 0; i--)
            {
                try { stagedExecutableParentPins[i].Dispose(); }
                catch (Exception error) { if (failure == null) failure = error; }
            }
            stagedExecutableParentPins.Clear();
            if (failure != null) throw failure;
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            if (State == AllocationState.IntentFlushed)
            {
                State = AllocationState.FailedBeforeCreation;
                Failure = AllocationDiagnostic("allocation owner disposed before runtime creation; candidate was not created by this attempt", RuntimePath, JournalPath);
            }
            else if (State == AllocationState.Created || State == AllocationState.Verified)
            {
                State = AllocationState.FailedRetained;
                Failure = AllocationDiagnostic("allocation owner disposed before identity receipt; runtime retained", RuntimePath, JournalPath);
            }
            Exception failure = null;
            try { SafeCloseStagedExecutable(); } catch (Exception e) { failure = e; }
            try { if (runtimeHandle != null) runtimeHandle.Dispose(); } catch (Exception e) { if (failure == null) failure = e; }
            try { journal.Dispose(); } catch (Exception e) { if (failure == null) failure = e; }
            try { parent.DisposeOwned(); } catch (Exception e) { if (failure == null) failure = e; }
            if (failure != null) throw new IOException(AllocationDiagnostic("one or more allocation handles failed to close; runtime retained", RuntimePath, JournalPath), failure);
        }
    }

    internal static RuntimeAllocation BeginAuthorizedAllocation()
    {
        return BeginAllocation(PinAuthorizedRoot(), Guid.NewGuid()
#if SCOPED_RUNNER_TESTING
            , false
#endif
            );
    }

#if SCOPED_RUNNER_TESTING
    internal static RuntimeAllocation BeginAllocationForFixture(PinnedDirectory ownedParent, Guid id, bool injectIdentityFailure)
    {
        return BeginAllocation(ownedParent, id, injectIdentityFailure);
    }
#endif

    private static RuntimeAllocation BeginAllocation(PinnedDirectory ownedParent, Guid id
#if SCOPED_RUNNER_TESTING
        , bool injectIdentityFailure
#endif
        )
    {
        bool tookOwnership = false;
        try
        {
            if (ownedParent == null) throw new ArgumentNullException("ownedParent");
            ownedParent.TransferOwnership();
            tookOwnership = true;
            if (id == Guid.Empty) throw new ArgumentException("invocation identity must be nonempty", "id");
            return new RuntimeAllocation(ownedParent, id
#if SCOPED_RUNNER_TESTING
                , injectIdentityFailure
#endif
                );
        }
        catch
        {
            if (tookOwnership) { try { ownedParent.DisposeOwned(); } catch { } }
            throw;
        }
    }

    private static string FormatIdentity(FileIdentity identity)
    {
        return identity.VolumeSerial.ToString("X16") + ":" + identity.FileId.ToString("N");
    }

    private static string AllocationDiagnostic(string error, string runtimePath, string journalPath)
    {
        // Bound only free-form error text. Parent paths are bounded at pin time;
        // the generated child suffixes are fixed, so the complete diagnostic is
        // bounded by 2 * MaximumPathLength plus this format/error allowance.
        if (String.IsNullOrEmpty(error)) error = "allocation failed";
        error = error.Replace('\r', ' ').Replace('\n', ' ');
        if (error.Length > 384) error = error.Substring(0, 384);
        return "error=" + error + "; runtime=" + (runtimePath ?? "<unavailable>") + "; journal=" + (journalPath ?? "<not-created>");
    }

    internal static DurableJournal CreateJournal(PinnedDirectory evidenceRoot, out string journalPath)
    {
        if (evidenceRoot == null) throw new ArgumentNullException("evidenceRoot");
        SecurityIdentifier user;
        using (WindowsIdentity identity = WindowsIdentity.GetCurrent()) user = identity == null ? null : identity.User;
        if (user == null) throw new IOException("current user has no SID");
        string sddl = "D:P(A;;FA;;;SY)(A;;FA;;;" + user.Value + ")";
        IntPtr descriptor;
        uint descriptorSize;
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, out descriptor, out descriptorSize))
            throw new IOException("unable to build protected journal DACL", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        string fileName = ".scoped-run-" + Guid.NewGuid().ToString("N") + ".journal";
        journalPath = System.IO.Path.Combine(evidenceRoot.Path, fileName);
        try
        {
            var security = new SecurityAttributes { Length = Marshal.SizeOf(typeof(SecurityAttributes)), SecurityDescriptor = descriptor, InheritHandle = 0 };
            if (journalPath.Length > MaximumPathLength) throw new IOException("generated journal path exceeds the fixed path bound: " + journalPath);
            SafeFileHandle handle = CreateFileW(journalPath, GENERIC_WRITE | READ_CONTROL | FILE_READ_ATTRIBUTES, 0, ref security, CREATE_NEW,
                FILE_FLAG_WRITE_THROUGH, IntPtr.Zero);
            if (handle == null || handle.IsInvalid) throw new IOException("exclusive journal creation failed",
                new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            try { VerifyProtectedDacl(handle, user, AceFlags.None, "journal"); return new DurableJournal(journalPath, handle); }
            catch { handle.Dispose(); throw; }
        }
        finally { LocalFree(descriptor); }
    }

    private static void VerifyProtectedDacl(SafeFileHandle handle, SecurityIdentifier user, AceFlags expectedFlags, string objectName)
    { VerifyPrivateDacl(handle, user, expectedFlags, objectName, false); }

    // Ordinary payload files inherit the same two private principals from their
    // verified runtime parent. Only closed-scope descendant disposition accepts
    // that exact inherited form; roots, staged inputs and evidence stay protected.
    private static void VerifyRuntimeEntryDacl(SafeFileHandle handle, SecurityIdentifier user, AceFlags expectedFlags, string objectName)
    { VerifyPrivateDacl(handle, user, expectedFlags, objectName, true); }

    private static void VerifyPrivateDacl(SafeFileHandle handle, SecurityIdentifier user, AceFlags expectedFlags,
        string objectName, bool allowInherited)
    {
        IntPtr owner, group, dacl, sacl, descriptor;
        uint error = GetSecurityInfo(handle, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
            out owner, out group, out dacl, out sacl, out descriptor);
        if (error != 0) throw new IOException("GetSecurityInfo(" + objectName + ") failed", new System.ComponentModel.Win32Exception((int)error));
        try
        {
            uint length = GetSecurityDescriptorLength(descriptor);
            if (length == 0 || length > 65536) throw new IOException(objectName + " security descriptor size is invalid");
            byte[] bytes = new byte[(int)length];
            Marshal.Copy(descriptor, bytes, 0, (int)length);
            var raw = new RawSecurityDescriptor(bytes, 0);
            bool isProtected = (raw.ControlFlags & ControlFlags.DiscretionaryAclProtected) != 0;
            if ((!isProtected && !allowInherited) || raw.DiscretionaryAcl == null || raw.DiscretionaryAcl.Count != 2)
                throw new IOException(objectName + " DACL is not the expected " + (allowInherited ? "private" : "protected") + " two-entry ACL");
            AceFlags exactFlags = expectedFlags | (isProtected ? AceFlags.None : AceFlags.Inherited);
            bool system = false, currentUser = false;
            foreach (GenericAce ace in raw.DiscretionaryAcl)
            {
                CommonAce common = ace as CommonAce;
                if (common == null || common.IsCallback || common.OpaqueLength != 0 ||
                    common.AceQualifier != AceQualifier.AccessAllowed || common.AceFlags != exactFlags ||
                    common.AccessMask != (int)FileSystemRights.FullControl)
                    throw new IOException(objectName + " DACL contains an unexpected ACE");
                SecurityIdentifier sid = common.SecurityIdentifier;
                if (sid.Equals(new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null))) system = true;
                else if (sid.Equals(user)) currentUser = true;
                else throw new IOException(objectName + " DACL grants access to an unexpected SID");
            }
            if (!system || !currentUser) throw new IOException(objectName + " DACL is missing a required principal");
        }
        finally { LocalFree(descriptor); }
    }

    internal static IntPtr CreateProtectedPipeSecurityDescriptor()
    {
        SecurityIdentifier user;
        using(WindowsIdentity current=WindowsIdentity.GetCurrent()) user=current==null ? null : current.User;
        if(user==null) throw new IOException("current user SID unavailable for payload pipe DACL");
        IntPtr descriptor; uint size;
        if(!ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;FA;;;SY)(A;;FA;;;"+user.Value+")",1,out descriptor,out size))
            throw new IOException("unable to build protected payload pipe DACL",new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        return descriptor;
    }

    internal static void VerifyProtectedPipeDacl(SafeFileHandle handle)
    {
        SecurityIdentifier user;
        using(WindowsIdentity current=WindowsIdentity.GetCurrent()) user=current==null ? null : current.User;
        if(user==null) throw new IOException("current user SID unavailable while verifying payload pipe DACL");
        VerifyProtectedDacl(handle,user,AceFlags.None,"payload output pipe");
    }

    private static SafeFileHandle OpenSourceFile(string path)
    {
        SafeFileHandle handle = CreateFileW(path, GENERIC_READ | READ_CONTROL | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ, IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN, IntPtr.Zero);
        if (handle == null || handle.IsInvalid) throw new IOException("CreateFileW(open source file) failed: " + path,
            new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        return handle;
    }

    // Duplicate the exact existing file object instead of reopening its path.
    // The original DELETE-access runtime pin intentionally omits delete sharing;
    // a second independent open cannot coexist with that custody handle.
    private static SafeFileHandle DuplicatePinnedHandle(SafeFileHandle source)
    {
        SafeFileHandle duplicate;
        if(!DuplicateHandle(new IntPtr(-1),source,new IntPtr(-1),out duplicate,0,false,2))
        {
            int error=Marshal.GetLastWin32Error();
            if(duplicate!=null) duplicate.Dispose();
            throw new IOException("DuplicateHandle(exact runtime pin) failed",new System.ComponentModel.Win32Exception(error));
        }
        if(duplicate==null || duplicate.IsInvalid)
        {
            if(duplicate!=null) duplicate.Dispose();
            throw new IOException("DuplicateHandle(exact runtime pin) returned an invalid handle");
        }
        return duplicate;
    }

    private static PinnedDirectory PinSingleDirectory(string path, SafeFileHandle handle)
    {
        try { return new PinnedDirectory(path, new List<SafeFileHandle> { handle }); }
        catch { try { handle.Dispose(); } catch { } throw; }
    }

    private static StagedEntry ReadDirectoryEntry(PinnedDirectory directory, string relativePath)
    {
        FileAttributeTagInfo tag;
        Check(GetFileInformationByHandleEx(directory.Handle, FileAttributeTagInfoClass, out tag,
            (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(source directory)");
        FileBasicInfo basic;
        Check(GetFileInformationByHandleEx(directory.Handle, FileBasicInfoClass, out basic,
            (uint)Marshal.SizeOf(typeof(FileBasicInfo))), "FileBasicInfo(source directory)");
        if ((tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0 || (tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) == 0)
            throw new IOException("source component is not a plain directory: " + directory.Path);
        return new StagedEntry(relativePath, true, directory.Identity, 0, basic.LastWriteTime, tag.Attributes, String.Empty);
    }

    private static void CopyDirectoryTree(PinnedDirectory sourceDirectory, string relativeDirectory, string destinationDirectory,
        int depth, StagedEntry expectedDirectory, List<StagedEntry> manifest, HashSet<string> identities,
        ref long totalBytes, CancellationToken cancellationToken, List<SafeFileHandle> sourceFilePins,
        List<PinnedDirectory> sourceDirectoryPins
#if SCOPED_RUNNER_TESTING
        , string failAtRelativePath
#endif
        , ulong deadline=0
        )
    {
        EnsureFinalizationBudgetIfSet(deadline,"during bounded evidence copy");
        if (depth > MaximumSourceDepth) throw new IOException("source directory depth exceeds the fixed bound");
        StagedEntry actualDirectory = ReadDirectoryEntry(sourceDirectory, relativeDirectory);
        if (!actualDirectory.SameAs(expectedDirectory)) throw new IOException("source directory identity or metadata changed before traversal");
        foreach (string sourceChildPath in EnumerateBoundedEntries(sourceDirectory.Path, manifest.Count))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (manifest.Count >= MaximumInventoryEntries) throw new IOException("source inventory exceeds the fixed entry bound");
            string name = Path.GetFileName(sourceChildPath);
            ValidateSourceComponent(name);
            string relative = relativeDirectory.Length == 0 ? name : relativeDirectory + "\\" + name;
            if (relative.Length > MaximumPathLength) throw new IOException("source relative path exceeds the fixed bound: " + relative);
            string destinationPath = Path.Combine(destinationDirectory, name);
            SafeFileHandle entry = OpenEntryForInspection(sourceChildPath);
            bool retainEntry = false;
            try
            {
                FileAttributeTagInfo tag;
                Check(GetFileInformationByHandleEx(entry, FileAttributeTagInfoClass, out tag,
                    (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(source entry)");
                if ((tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0)
                    throw new IOException("source reparse point is refused: " + sourceChildPath);
                FileIdentity identity = ReadIdentity(entry);
                AddUniqueIdentity(identities, identity, "source entry " + relative);
                if ((tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) != 0)
                {
                    var childPin = PinSingleDirectory(sourceChildPath, OpenDirectory(sourceChildPath));
                    try { sourceDirectoryPins.Add(childPin); }
                    catch { childPin.DisposeOwned(); throw; }
                    bool destinationCreated = false;
                    try
                    {
                        StagedEntry childEntry = ReadDirectoryEntry(childPin, relative);
                        if (!childEntry.Identity.SameAs(identity)) throw new IOException("source directory identity changed while opening: " + sourceChildPath);
                        manifest.Add(childEntry);
                        if (manifest.Count > MaximumInventoryEntries) throw new IOException("source inventory exceeds the fixed entry bound");
                        CreateDestinationDirectory(destinationPath);
                        destinationCreated = true;
                        using (PinnedDirectory destinationPin = PinSingleDirectory(destinationPath, OpenDirectory(destinationPath)))
                        {
                            SecurityIdentifier user;
                            using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
                            if (user == null) throw new IOException("current user SID unavailable while verifying staged directory");
                            VerifyProtectedDacl(destinationPin.Handle, user, AceFlags.ContainerInherit | AceFlags.ObjectInherit, "staged directory");
                            CopyDirectoryTree(childPin, relative, destinationPin.Path, depth + 1, childEntry,
                                manifest, identities, ref totalBytes, cancellationToken
                                , sourceFilePins, sourceDirectoryPins
#if SCOPED_RUNNER_TESTING
                                , failAtRelativePath
#endif
                                , deadline
                                );
                        }
                    }
                    catch
                    {
                        // A newly-created path stays in the retained runtime; no path cleanup is attempted.
                        if (!destinationCreated) { }
                        throw;
                    }
                    finally { /* source pin remains owned through receipt */ }
                }
                else
                {
#if SCOPED_RUNNER_TESTING
                    if (String.Equals(failAtRelativePath, relative, StringComparison.OrdinalIgnoreCase))
                        throw new IOException("fixture injected failure after a partial source-tree copy");
#endif
                    StagedEntry copied = CopySourceFile(entry, identity, sourceChildPath, destinationPath, relative,
                        tag.Attributes, ref totalBytes, cancellationToken,deadline);
                    sourceFilePins.Add(entry);
                    retainEntry = true;
                    manifest.Add(copied);
                    if (manifest.Count > MaximumInventoryEntries) throw new IOException("source inventory exceeds the fixed entry bound");
                }
            }
            finally { if (!retainEntry) entry.Dispose(); }
        }
    }

    private static void ScanSourceTree(PinnedDirectory sourceDirectory, string relativeDirectory, int depth,
        List<StagedEntry> manifest, HashSet<string> identities, ref long totalBytes, CancellationToken cancellationToken,ulong deadline=0)
    {
        EnsureFinalizationBudgetIfSet(deadline,"during bounded evidence scan");
        if (depth > MaximumSourceDepth) throw new IOException("source directory depth exceeds the fixed bound during verification");
        foreach (string childPath in EnumerateBoundedEntries(sourceDirectory.Path, manifest.Count))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (manifest.Count >= MaximumInventoryEntries) throw new IOException("source inventory exceeds the fixed entry bound during verification");
            string name = Path.GetFileName(childPath);
            ValidateSourceComponent(name);
            string relative = relativeDirectory.Length == 0 ? name : relativeDirectory + "\\" + name;
            using (SafeFileHandle entry = OpenEntryForInspection(childPath))
            {
                FileAttributeTagInfo tag;
                Check(GetFileInformationByHandleEx(entry, FileAttributeTagInfoClass, out tag,
                    (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(source verification)");
                if ((tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0)
                    throw new IOException("source reparse point appeared during verification: " + childPath);
                FileIdentity identity = ReadIdentity(entry);
                AddUniqueIdentity(identities, identity, "source verification entry " + relative);
                if ((tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) != 0)
                {
                    var childPin = PinSingleDirectory(childPath, OpenDirectory(childPath));
                    try
                    {
                        StagedEntry dir = ReadDirectoryEntry(childPin, relative);
                        if (!dir.Identity.SameAs(identity)) throw new IOException("source directory identity changed during verification: " + childPath);
                        manifest.Add(dir);
                        ScanSourceTree(childPin, relative, depth + 1, manifest, identities, ref totalBytes, cancellationToken,deadline);
                    }
                    finally { childPin.DisposeOwned(); }
                }
                else
                {
                    StagedEntry file = ScanSourceFile(entry, identity, childPath, relative, tag.Attributes, ref totalBytes, cancellationToken,deadline);
                    manifest.Add(file);
                }
            }
        }
    }

    private static StagedEntry CopySourceFile(SafeFileHandle source, FileIdentity identity, string sourcePath,
        string destinationPath, string relativePath, uint attributes, ref long totalBytes, CancellationToken cancellationToken,ulong deadline=0)
    {
        FileStandardInfo before;
        Check(GetFileInformationByHandleEx(source, FileStandardInfoClass, out before,
            (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(source file)");
        FileBasicInfo basicBefore;
        Check(GetFileInformationByHandleEx(source, FileBasicInfoClass, out basicBefore,
            (uint)Marshal.SizeOf(typeof(FileBasicInfo))), "FileBasicInfo(source file)");
        if (before.Directory || before.DeletePending || before.NumberOfLinks != 1 || before.EndOfFile < 0 || before.EndOfFile > MaximumSingleStagedFileBytes)
            throw new IOException("source file size or type is outside the fixed bound: " + sourcePath);
        if (before.EndOfFile > MaximumTotalStagedBytes - totalBytes)
            throw new IOException("source tree exceeds the fixed total byte bound");
        SafeFileHandle destination = CreateDestinationFile(destinationPath);
        try
        {
            SecurityIdentifier user;
            using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
            if (user == null) throw new IOException("current user SID unavailable while verifying staged file");
            VerifyProtectedDacl(destination, user, AceFlags.None, "staged file");
            string copiedDigest = TransferAndHash(source, destination, before.EndOfFile, true, cancellationToken,deadline);
            if (!FlushFileBuffers(destination)) throw new IOException("FlushFileBuffers(staged file) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            string sourceDigest = TransferAndHash(source, null, before.EndOfFile, false, cancellationToken,deadline);
            if (!String.Equals(copiedDigest, sourceDigest, StringComparison.Ordinal))
                throw new IOException("source content changed while the staged copy was being made: " + sourcePath);
            FileStandardInfo after;
            Check(GetFileInformationByHandleEx(source, FileStandardInfoClass, out after,
                (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(source after copy)");
            FileBasicInfo basicAfter;
            Check(GetFileInformationByHandleEx(source, FileBasicInfoClass, out basicAfter,
                (uint)Marshal.SizeOf(typeof(FileBasicInfo))), "FileBasicInfo(source after copy)");
            if (after.NumberOfLinks != 1 || after.EndOfFile != before.EndOfFile || basicAfter.LastWriteTime != basicBefore.LastWriteTime ||
                (basicAfter.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0 || !ReadIdentity(source).SameAs(identity))
                throw new IOException("source metadata or identity changed while staging: " + sourcePath);
            FileStandardInfo destinationInfo;
            Check(GetFileInformationByHandleEx(destination, FileStandardInfoClass, out destinationInfo,
                (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(staged file)");
            if (destinationInfo.Directory || destinationInfo.EndOfFile != before.EndOfFile || destinationInfo.DeletePending)
                throw new IOException("staged file size or type differs from its source: " + destinationPath);
            string destinationDigest = TransferAndHash(destination, null, destinationInfo.EndOfFile, false, cancellationToken,deadline);
            if (!String.Equals(copiedDigest, destinationDigest, StringComparison.Ordinal))
                throw new IOException("independent destination handle readback did not match the source: " + destinationPath);
            totalBytes = checked(totalBytes + before.EndOfFile);
            return new StagedEntry(relativePath, false, identity, before.EndOfFile, basicBefore.LastWriteTime, attributes, copiedDigest);
        }
        finally { destination.Dispose(); }
    }

    private static StagedEntry ScanSourceFile(SafeFileHandle source, FileIdentity identity, string path,
        string relativePath, uint attributes, ref long totalBytes, CancellationToken cancellationToken,ulong deadline=0)
    {
        FileStandardInfo standard;
        Check(GetFileInformationByHandleEx(source, FileStandardInfoClass, out standard,
            (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(source verification)");
        FileBasicInfo basic;
        Check(GetFileInformationByHandleEx(source, FileBasicInfoClass, out basic,
            (uint)Marshal.SizeOf(typeof(FileBasicInfo))), "FileBasicInfo(source verification)");
        if (standard.Directory || standard.DeletePending || standard.NumberOfLinks != 1 || standard.EndOfFile < 0 || standard.EndOfFile > MaximumSingleStagedFileBytes ||
            standard.EndOfFile > MaximumTotalStagedBytes - totalBytes)
            throw new IOException("source file violates the fixed staging bounds during verification: " + path);
        string digest = TransferAndHash(source, null, standard.EndOfFile, false, cancellationToken,deadline);
        FileBasicInfo after;
        Check(GetFileInformationByHandleEx(source, FileBasicInfoClass, out after,
            (uint)Marshal.SizeOf(typeof(FileBasicInfo))), "FileBasicInfo(source verification after read)");
        if (after.LastWriteTime != basic.LastWriteTime || !ReadIdentity(source).SameAs(identity))
            throw new IOException("source metadata or identity changed during verification: " + path);
        totalBytes = checked(totalBytes + standard.EndOfFile);
        return new StagedEntry(relativePath, false, identity, standard.EndOfFile, basic.LastWriteTime, attributes, digest);
    }

    private static string TransferAndHash(SafeFileHandle source, SafeFileHandle destination, long expectedLength,
        bool copy, CancellationToken cancellationToken,ulong deadline=0)
    {
        long position;
        Check(SetFilePointerEx(source, 0, out position, FILE_BEGIN), "SetFilePointerEx(source)");
        byte[] managed = new byte[TransferBufferBytes];
        IntPtr buffer = Marshal.AllocHGlobal(TransferBufferBytes);
        try
        {
            using (SHA256 hash = SHA256.Create())
            {
                long total = 0;
                while (total < expectedLength)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    EnsureFinalizationBudgetIfSet(deadline,"during bounded file transfer");
                    uint request = (uint)Math.Min(TransferBufferBytes, expectedLength - total);
                    uint read;
                    if (!ReadFile(source, buffer, request, out read, IntPtr.Zero))
                        throw new IOException("ReadFile(source staging) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
                    if (read == 0 || read > request) throw new IOException("ReadFile(source staging) ended before the recorded file length");
                    Marshal.Copy(buffer, managed, 0, (int)read);
                    hash.TransformBlock(managed, 0, (int)read, managed, 0);
                    if (copy) WriteAllHandle(destination, buffer, read);
                    total = checked(total + read);
                }
                if (total != expectedLength) throw new IOException("staging transfer length changed");
                hash.TransformFinalBlock(new byte[0], 0, 0);
                return Hex(hash.Hash);
            }
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private static void WriteAllHandle(SafeFileHandle handle, IntPtr buffer, uint length)
    {
        uint offset = 0;
        while (offset < length)
        {
            uint written;
            if (!WriteFile(handle, IntPtr.Add(buffer, (int)offset), length - offset, out written, IntPtr.Zero))
                throw new IOException("WriteFile(staged content) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            if (written == 0 || written > length - offset) throw new IOException("WriteFile(staged content) made invalid progress");
            offset += written;
        }
    }

    private static SafeFileHandle OpenEntryForInspection(string path)
    {
        SafeFileHandle handle = CreateFileW(path, GENERIC_READ | READ_CONTROL | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ, IntPtr.Zero, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN, IntPtr.Zero);
        if (handle == null || handle.IsInvalid) throw new IOException("CreateFileW(open source entry) failed: " + path,
            new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        return handle;
    }

    private static void CreateDestinationDirectory(string path)
    {
        SecurityIdentifier user;
        using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
        if (user == null) throw new IOException("current user SID unavailable while creating staged directory");
        IntPtr descriptor;
        uint descriptorSize;
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;" + user.Value + ")", 1, out descriptor, out descriptorSize))
            throw new IOException("unable to build staged directory DACL", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        try
        {
            var security = new SecurityAttributes { Length = Marshal.SizeOf(typeof(SecurityAttributes)), SecurityDescriptor = descriptor, InheritHandle = 0 };
            if (!CreateDirectoryW(path, ref security)) throw new IOException("exclusive staged directory creation failed: " + path,
                new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        }
        finally { LocalFree(descriptor); }
    }

    private static SafeFileHandle CreateDestinationFile(string path)
    {
        SecurityIdentifier user;
        using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
        if (user == null) throw new IOException("current user SID unavailable while creating staged file");
        IntPtr descriptor;
        uint descriptorSize;
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;FA;;;SY)(A;;FA;;;" + user.Value + ")", 1, out descriptor, out descriptorSize))
            throw new IOException("unable to build staged file DACL", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
        try
        {
            var security = new SecurityAttributes { Length = Marshal.SizeOf(typeof(SecurityAttributes)), SecurityDescriptor = descriptor, InheritHandle = 0 };
            SafeFileHandle handle = CreateFileW(path, GENERIC_READ | GENERIC_WRITE | READ_CONTROL | FILE_READ_ATTRIBUTES, FILE_SHARE_READ,
                ref security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, IntPtr.Zero);
            if (handle == null || handle.IsInvalid) throw new IOException("exclusive staged file creation failed: " + path,
                new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
            return handle;
        }
        finally { LocalFree(descriptor); }
    }

    private static SafeFileHandle PinStagedExecutable(string runtimePath, string[] components, FileIdentity expectedIdentity,
        out FileIdentity identity, List<SafeFileHandle> retainedParents)
    {
        string current = runtimePath;
        SecurityIdentifier user;
        using (WindowsIdentity currentIdentity = WindowsIdentity.GetCurrent()) user = currentIdentity == null ? null : currentIdentity.User;
        if (user == null) throw new IOException("current user SID unavailable while pinning staged executable");
        try
        {
            for (int i = 0; i < components.Length - 1; i++)
            {
                current = Path.Combine(current, components[i]);
                SafeFileHandle parent = OpenDirectory(current);
                retainedParents.Add(parent);
                VerifyProtectedDacl(parent, user, AceFlags.ContainerInherit | AceFlags.ObjectInherit, "staged executable parent");
            }
            string executablePath = Path.Combine(current, components[components.Length - 1]);
            SafeFileHandle executable = OpenSourceFile(executablePath);
            try
            {
            FileAttributeTagInfo tag;
            Check(GetFileInformationByHandleEx(executable, FileAttributeTagInfoClass, out tag,
                (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(staged executable)");
            FileStandardInfo standard;
            Check(GetFileInformationByHandleEx(executable, FileStandardInfoClass, out standard,
                (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(staged executable)");
            if ((tag.Attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0 || standard.Directory || standard.DeletePending)
                throw new IOException("staged executable is not a plain file: " + executablePath);
            VerifyProtectedDacl(executable, user, AceFlags.None, "staged executable");
            identity = ReadIdentity(executable);
            if (!identity.SameAs(expectedIdentity)) throw new IOException("staged executable identity changed after tree verification");
            return executable;
            }
            catch { executable.Dispose(); throw; }
        }
        finally
        {
            // Parent pins remain owned by RuntimeAllocation until its eventual
            // custody transfer or disposal; the executable handle alone is not
            // sufficient to keep its path components stable.
        }
    }

    private static StagedEntry FindExecutableEntry(List<StagedEntry> manifest, string relativePath)
    {
        for (int i = 0; i < manifest.Count; i++)
            if (String.Equals(manifest[i].RelativePath, relativePath, StringComparison.OrdinalIgnoreCase))
            {
                if (manifest[i].IsDirectory) throw new IOException("requested staged executable is a directory");
                // The manifest spelling is the only accepted spelling; this
                // also refuses short-name or other path aliases.
                if (!String.Equals(manifest[i].RelativePath, relativePath, StringComparison.Ordinal))
                    throw new IOException("requested staged executable uses a path alias or noncanonical spelling");
                return manifest[i];
            }
        throw new IOException("requested executable is absent from the staged source manifest");
    }

    private static void CompareManifests(List<StagedEntry> before, List<StagedEntry> after)
    {
        if (before.Count != after.Count) throw new IOException("source inventory changed during staging");
        before.Sort(delegate(StagedEntry a, StagedEntry b) { return StringComparer.OrdinalIgnoreCase.Compare(a.RelativePath, b.RelativePath); });
        after.Sort(delegate(StagedEntry a, StagedEntry b) { return StringComparer.OrdinalIgnoreCase.Compare(a.RelativePath, b.RelativePath); });
        for (int i = 0; i < before.Count; i++)
            if (!before[i].SameAs(after[i])) throw new IOException("source manifest changed during staging at: " + before[i].RelativePath);
    }

    private static void ValidateDestinationTree(string destinationRoot, SafeFileHandle runtimeHandle,
        List<StagedEntry> sourceManifest, CancellationToken cancellationToken,
        out Dictionary<string, FileIdentity> identitiesByPath,ulong deadline=0)
    {
        var expected = new Dictionary<string, StagedEntry>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < sourceManifest.Count; i++) expected.Add(sourceManifest[i].RelativePath, sourceManifest[i]);
        var observed = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var destinationIdentities = new HashSet<string>(StringComparer.Ordinal);
        int count = 0;
        long total = 0;
        FileIdentity runtimeIdentity = ReadIdentity(runtimeHandle);
        FileAttributeTagInfo runtimeTag;
        Check(GetFileInformationByHandleEx(runtimeHandle, FileAttributeTagInfoClass, out runtimeTag,
            (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(held runtime root)");
        if ((runtimeTag.Attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != FILE_ATTRIBUTE_DIRECTORY)
            throw new IOException("held runtime handle is not a plain directory");
        SecurityIdentifier user;
        using (WindowsIdentity current = WindowsIdentity.GetCurrent()) user = current == null ? null : current.User;
        if (user == null) throw new IOException("current user SID unavailable while verifying staged tree");
        VerifyProtectedDacl(runtimeHandle, user, AceFlags.ContainerInherit | AceFlags.ObjectInherit, "staged runtime root");
        AddUniqueIdentity(destinationIdentities, runtimeIdentity, "staged runtime root");
        identitiesByPath = new Dictionary<string, FileIdentity>(StringComparer.OrdinalIgnoreCase);
        ScanDestinationDirectory(destinationRoot, runtimeHandle, String.Empty, 0, expected, observed,
            destinationIdentities, identitiesByPath, ref count, ref total, user, cancellationToken,deadline);
        if (observed.Count != expected.Count - 1)
            throw new IOException("staged destination inventory contains missing or unexpected entries");
    }

    private static void ScanDestinationDirectory(string directoryPath, SafeFileHandle directoryHandle,
        string relativeDirectory, int depth, Dictionary<string, StagedEntry> expected, HashSet<string> observed,
        HashSet<string> identities, Dictionary<string, FileIdentity> identitiesByPath,
        ref int count, ref long total, SecurityIdentifier user, CancellationToken cancellationToken,ulong deadline=0)
    {
        EnsureFinalizationBudgetIfSet(deadline,"during independent payload snapshot readback");
        if (depth > MaximumSourceDepth) throw new IOException("staged directory depth exceeds the fixed bound");
        foreach (string path in EnumerateBoundedEntries(directoryPath, count))
        {
            cancellationToken.ThrowIfCancellationRequested();
            EnsureFinalizationBudgetIfSet(deadline,"during independent payload snapshot entry readback");
            if (++count > MaximumInventoryEntries) throw new IOException("staged destination inventory exceeds the fixed entry bound");
            string name = Path.GetFileName(path);
            ValidateSourceComponent(name);
            string relative = relativeDirectory.Length == 0 ? name : relativeDirectory + "\\" + name;
            StagedEntry expectedEntry;
            if (!expected.TryGetValue(relative, out expectedEntry) || !observed.Add(relative))
                throw new IOException("staged destination has an unexpected or duplicate entry: " + relative);
            using (SafeFileHandle entry = OpenEntryForInspection(path))
            {
                FileAttributeTagInfo tag;
                Check(GetFileInformationByHandleEx(entry, FileAttributeTagInfoClass, out tag,
                    (uint)Marshal.SizeOf(typeof(FileAttributeTagInfo))), "FileAttributeTagInfo(staged entry)");
                if ((tag.Attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0)
                    throw new IOException("staged destination reparse point is refused: " + path);
                FileIdentity identity = ReadIdentity(entry);
                AddUniqueIdentity(identities, identity, "staged destination " + relative);
                identitiesByPath.Add(relative, identity);
                bool isDirectory = (tag.Attributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
                if (isDirectory != expectedEntry.IsDirectory) throw new IOException("staged destination entry type differs: " + relative);
                if (isDirectory)
                {
                    var child = PinSingleDirectory(path, OpenDirectory(path));
                    try
                    {
                        if (!child.Identity.SameAs(identity)) throw new IOException("staged directory identity changed while pinning: " + path);
                        VerifyProtectedDacl(child.Handle, user, AceFlags.ContainerInherit | AceFlags.ObjectInherit, "staged directory");
                        ScanDestinationDirectory(child.Path, child.Handle, relative, depth + 1, expected, observed, identities, identitiesByPath,
                            ref count, ref total, user, cancellationToken,deadline);
                    }
                    finally { child.DisposeOwned(); }
                }
                else
                {
                    VerifyProtectedDacl(entry, user, AceFlags.None, "staged file");
                    FileStandardInfo standard;
                    Check(GetFileInformationByHandleEx(entry, FileStandardInfoClass, out standard,
                        (uint)Marshal.SizeOf(typeof(FileStandardInfo))), "FileStandardInfo(staged verification)");
                    if (standard.Directory || standard.DeletePending || standard.NumberOfLinks != 1 || standard.EndOfFile != expectedEntry.Length ||
                        standard.EndOfFile > MaximumSingleStagedFileBytes || standard.EndOfFile > MaximumTotalStagedBytes - total)
                        throw new IOException("staged file size violates its manifest or fixed bounds: " + relative);
                    string digest = TransferAndHash(entry, null, standard.EndOfFile, false, cancellationToken,deadline);
                    if (!String.Equals(digest, expectedEntry.ContentDigest, StringComparison.Ordinal))
                        throw new IOException("staged file content differs from the source manifest: " + relative);
                    total = checked(total + standard.EndOfFile);
                }
            }
        }
    }

    private static string ManifestDigest(List<StagedEntry> entries)
    {
        return HashText(SerializeManifest(entries));
    }

    private static string SerializeManifest(List<StagedEntry> entries)
    {
        entries.Sort(delegate(StagedEntry a,StagedEntry b) { return StringComparer.OrdinalIgnoreCase.Compare(a.RelativePath,b.RelativePath); });
        var text=new StringBuilder();
        for(int i=0;i<entries.Count;i++)
        {
            StagedEntry item=entries[i];
            text.Append(item.RelativePath).Append('|').Append(item.IsDirectory?'D':'F').Append('|').Append(FormatIdentity(item.Identity)).Append('|')
                .Append(item.Length).Append('|').Append(item.LastWriteTime).Append('|').Append(item.Attributes).Append('|').Append(item.ContentDigest).Append('\n');
        }
        return text.ToString();
    }

    private static void WriteBytes(SafeFileHandle destination,byte[] bytes)
    {
        IntPtr buffer=Marshal.AllocHGlobal(bytes.Length);
        try
        {
            Marshal.Copy(bytes,0,buffer,bytes.Length); uint offset=0;
            while(offset<(uint)bytes.Length)
            {
                uint written;
                if(!WriteFile(destination,IntPtr.Add(buffer,(int)offset),(uint)bytes.Length-offset,out written,IntPtr.Zero) || written==0 || written>(uint)bytes.Length-offset)
                    throw new IOException("WriteFile(payload evidence manifest) failed or made invalid progress",new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
                offset+=written;
            }
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private static string HashEvidenceFile(string path,FileIdentity expectedIdentity,ulong deadline,out long length)
    {
        using(SafeFileHandle file=OpenEntryForInspection(path))
        {
            if(expectedIdentity==null || !ReadIdentity(file).SameAs(expectedIdentity)) throw new IOException("payload log identity changed before independent readback");
            FileStandardInfo standard;
            Check(GetFileInformationByHandleEx(file,FileStandardInfoClass,out standard,(uint)Marshal.SizeOf(typeof(FileStandardInfo))),"FileStandardInfo(payload log readback)");
            if(standard.Directory || standard.DeletePending || standard.NumberOfLinks!=1 || standard.EndOfFile<0 || standard.EndOfFile>MaximumTotalStagedBytes)
                throw new IOException("payload log readback violates its file bounds");
            length=standard.EndOfFile;
            return TransferAndHash(file,null,length,false,CancellationToken.None,deadline);
        }
    }

    private static string HashText(string value)
    {
        using (SHA256 hash = SHA256.Create()) return Hex(hash.ComputeHash(Encoding.UTF8.GetBytes(value)));
    }

    private static string Hex(byte[] bytes)
    {
        var value = new StringBuilder(bytes.Length * 2);
        for (int i = 0; i < bytes.Length; i++) value.Append(bytes[i].ToString("X2"));
        return value.ToString();
    }

    private static void AddUniqueIdentity(HashSet<string> seen, FileIdentity identity, string description)
    {
        string key = FormatIdentity(identity);
        if (!seen.Add(key)) throw new IOException("tree contains an aliased file identity: " + description);
    }

    private static void EnsureSourceDoesNotOverlapAllocation(PinnedDirectory source, PinnedDirectory evidence,
        SafeFileHandle runtime, string runtimePath)
    {
        if (source.Path.Equals(evidence.Path, StringComparison.OrdinalIgnoreCase) ||
            IsPathAncestorOrSame(source.Path, evidence.Path) || IsPathAncestorOrSame(source.Path, runtimePath) ||
            IsPathAncestorOrSame(runtimePath, source.Path))
            throw new IOException("source root contains or aliases the evidence/runtime root");
        for (int i = 0; i < evidence.AncestorIdentities.Length; i++)
            if (source.Identity.SameAs(evidence.AncestorIdentities[i]))
                throw new IOException("source root identity aliases the evidence root or one of its ancestors");
        FileIdentity runtimeIdentity = runtime == null ? null : ReadIdentity(runtime);
        for (int i = 0; i < source.AncestorIdentities.Length; i++)
        {
            if (runtimeIdentity != null && source.AncestorIdentities[i].SameAs(runtimeIdentity))
                throw new IOException("source root is beneath the generated runtime through a filesystem alias");
        }
        if (runtimeIdentity != null && source.Identity.SameAs(runtimeIdentity))
            throw new IOException("source root identity aliases the generated runtime");
    }

    private static bool IsPathAncestorOrSame(string candidate, string descendant)
    {
        string normalizedCandidate = candidate.TrimEnd('\\');
        string normalizedDescendant = descendant.TrimEnd('\\');
        return normalizedDescendant.Equals(normalizedCandidate, StringComparison.OrdinalIgnoreCase) ||
            normalizedDescendant.StartsWith(normalizedCandidate + "\\", StringComparison.OrdinalIgnoreCase);
    }

    private static string[] ParseExecutableRelativePath(string value)
    {
        if (String.IsNullOrEmpty(value) || value.Length > MaximumPathLength || value[0] == '\\' || value[0] == '/' ||
            value.IndexOf('/') >= 0 || value.IndexOf(':') >= 0 || value.StartsWith("\\\\", StringComparison.Ordinal))
            throw new ArgumentException("executable path must be a bounded relative Windows path", "value");
        string[] components = value.Split('\\');
        for (int i = 0; i < components.Length; i++) ValidatePathComponent(components[i], "executable path");
        return components;
    }

    private static void ValidateSourceComponent(string component)
    {
        try { ValidatePathComponent(component, "source entry"); }
        catch (ArgumentException error) { throw new IOException(error.Message, error); }
    }

    private static void ValidatePathComponent(string component, string description)
    {
        if (String.IsNullOrEmpty(component) || component == "." || component == ".." || component.Length > 255 ||
            component.EndsWith(".", StringComparison.Ordinal) || component.EndsWith(" ", StringComparison.Ordinal))
            throw new ArgumentException(description + " contains an empty, dot, or unsupported-length component");
        if (!component.IsNormalized(NormalizationForm.FormC))
            throw new ArgumentException(description + " contains a noncanonical Unicode component");
        for (int i = 0; i < component.Length; i++)
            if (component[i] < 0x20 || "<>:\"/\\|?*".IndexOf(component[i]) >= 0)
                throw new ArgumentException(description + " contains an illegal Windows filename character");
        string baseName = component.Split('.')[0].ToUpperInvariant();
        if (baseName == "CON" || baseName == "PRN" || baseName == "AUX" || baseName == "NUL" ||
            IsNumberedDeviceName(baseName, "COM") || IsNumberedDeviceName(baseName, "LPT"))
            throw new ArgumentException(description + " contains a reserved DOS device name");
    }

    private static List<string> EnumerateBoundedEntries(string directoryPath, int alreadyObserved)
    {
        int remaining = MaximumInventoryEntries - alreadyObserved;
        if (remaining < 0) throw new IOException("inventory exceeds the fixed entry bound: " + directoryPath);
        var entries = new List<string>(Math.Min(remaining, 64));
        foreach (string path in Directory.EnumerateFileSystemEntries(directoryPath))
        {
            if (entries.Count >= remaining)
                throw new IOException("directory contains entries beyond the fixed inventory bound: " + directoryPath);
            entries.Add(path);
        }
        entries.Sort(delegate(string left, string right)
        {
            int folded = StringComparer.OrdinalIgnoreCase.Compare(Path.GetFileName(left), Path.GetFileName(right));
            return folded != 0 ? folded : StringComparer.Ordinal.Compare(Path.GetFileName(left), Path.GetFileName(right));
        });
        return entries;
    }

    private static bool IsNumberedDeviceName(string value, string prefix)
    {
        if (!value.StartsWith(prefix, StringComparison.Ordinal) || value.Length != prefix.Length + 1) return false;
        char digit = value[value.Length - 1];
        return (digit >= '1' && digit <= '9') || digit == '\u00b9' || digit == '\u00b2' || digit == '\u00b3';
    }

    internal static void ValidateExecutableRelativePathSyntax(string value) { ParseExecutableRelativePath(value); }
#if SCOPED_RUNNER_TESTING
    internal static void ValidateExecutableRelativePathForFixture(string value) { ValidateExecutableRelativePathSyntax(value); }
#endif

    // Pure syntax validation for a launch specification. This deliberately
    // performs no path normalization, existence check, or filesystem access.
    internal static void ValidateLaunchSourceDirectorySyntax(string value)
    {
        if (String.IsNullOrEmpty(value) || value.Length > MaximumPathLength || value.Length < 4 ||
            !((value[0] >= 'A' && value[0] <= 'Z') || (value[0] >= 'a' && value[0] <= 'z')) ||
            value[1] != ':' || value[2] != '\\' || value.IndexOf('/') >= 0 || value.StartsWith("\\\\", StringComparison.Ordinal))
            throw new ArgumentException("source directory must be a bounded local drive-rooted path", "value");
        if (value.IndexOf(':', 2) >= 0) throw new ArgumentException("source directory contains unsupported colon syntax", "value");
        string[] components = value.Substring(3).Split('\\');
        for (int i = 0; i < components.Length; i++) ValidatePathComponent(components[i], "source directory");
    }

    internal static void ValidateLaunchExecutablePathSyntax(string value)
    {
        // An absolute staged executable uses the same bounded local-drive and
        // component rules as a source directory, with its final component
        // serving as the executable filename.
        ValidateLaunchSourceDirectorySyntax(value);
    }

    private static string ToAsciiBounded(string value, int maximum)
    {
        var text = new StringBuilder(Math.Min(value.Length, maximum));
        for (int i = 0; i < value.Length && text.Length < maximum; i++)
        {
            char c = value[i];
            text.Append(c >= 0x20 && c <= 0x7e ? c : '?');
        }
        return text.ToString();
    }

    private static string BoundPath(string path)
    {
        if (String.IsNullOrEmpty(path)) return "<unavailable>";
        return path.Length <= MaximumPathLength ? path : path.Substring(0, MaximumPathLength);
    }

    private static void WriteAll(SafeFileHandle handle, byte[] bytes)
    {
        IntPtr buffer = Marshal.AllocHGlobal(bytes.Length);
        try
        {
            Marshal.Copy(bytes, 0, buffer, bytes.Length);
            int offset = 0;
            while (offset < bytes.Length)
            {
                uint written;
                if (!WriteFile(handle, IntPtr.Add(buffer, offset), (uint)(bytes.Length - offset), out written, IntPtr.Zero))
                    throw new IOException("WriteFile(journal) failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
                if (written == 0) throw new IOException("WriteFile(journal) made no progress");
                offset += checked((int)written);
            }
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

#if SCOPED_RUNNER_TESTING
    internal static string[] ReadJournalForFixture(string path)
    {
        var result = new List<string>();
        if (new FileInfo(path).Length > MaximumJournalBytes) throw new IOException("fixture journal exceeds the fixed byte bound");
        byte[] file = File.ReadAllBytes(path);
        if (file.Length > MaximumJournalBytes) throw new IOException("fixture journal exceeds the fixed byte bound");
        if (file.Length == 0 || file[file.Length - 1] != (byte)'\n')
            throw new IOException("fixture observed an incomplete final journal frame");
        int start = 0;
        for (int i = 0; i < file.Length; i++)
        {
            if (file[i] == (byte)'\r') throw new IOException("fixture observed a noncanonical journal line ending");
            if (file[i] != (byte)'\n') continue;
            int lineLength = i - start;
            if (lineLength == 0) throw new IOException("fixture observed an empty journal frame");
            for (int j = start; j < i; j++)
                if (file[j] < 0x20 || file[j] > 0x7e) throw new IOException("fixture observed non-ASCII journal framing");
            string line = Encoding.ASCII.GetString(file, start, lineLength);
            int first = line.IndexOf(':'); int second = first < 0 ? -1 : line.IndexOf(':', first + 1);
            if (first != 4 || second != 13 || !IsUpperHex(line, 0, 4) || !IsUpperHex(line, 5, 8))
                throw new IOException("fixture observed malformed journal frame");
            string body = line.Substring(second + 1);
            if (result.Count >= MaximumRecords || body.Length == 0 || body.Length > MaximumRecordBytes)
                throw new IOException("fixture observed a journal record outside the fixed bounds");
            byte[] bytes = Encoding.ASCII.GetBytes(body);
            for (int j = 0; j < body.Length; j++)
                if (body[j] < 0x20 || body[j] > 0x7e) throw new IOException("fixture observed non-ASCII journal body");
            if (bytes.Length != Convert.ToInt32(line.Substring(0, first), 16) || Crc32(bytes) != Convert.ToUInt32(line.Substring(first + 1, 8), 16))
                throw new IOException("fixture observed corrupt or torn journal record");
            result.Add(body);
            start = i + 1;
        }
        return result.ToArray();
    }
#endif

    private static bool IsUpperHex(string value, int start, int length)
    {
        if (start < 0 || start + length > value.Length) return false;
        for (int i = start; i < start + length; i++)
            if (!((value[i] >= '0' && value[i] <= '9') || (value[i] >= 'A' && value[i] <= 'F'))) return false;
        return true;
    }

    private static uint Crc32(byte[] bytes)
    {
        uint crc = 0xffffffff;
        for (int i = 0; i < bytes.Length; i++)
        {
            crc ^= bytes[i];
            for (int bit = 0; bit < 8; bit++) crc = (crc & 1) != 0 ? 0xedb88320 ^ (crc >> 1) : crc >> 1;
        }
        return ~crc;
    }

    private static void Check(bool result, string operation)
    {
        if (!result) throw new IOException(operation + " failed", new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()));
    }
}
