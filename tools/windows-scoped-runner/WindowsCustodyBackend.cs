// Bounded Windows filesystem-custody foundation. This source is not wired to
// workload launch; callers must not infer runtime allocation or deletion safety.
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

internal static class WindowsCustodyBackend
{
    internal const string AuthorizedRoot = @"C:\RhaiQuality\runs";
    internal const int MaximumRecordBytes = 4096;
    private const int MaximumRecords = 64;
    private const int MaximumJournalBytes = MaximumRecords * (MaximumRecordBytes + 15);
    private const int MaximumPathLength = 248;
    private const uint FILE_READ_ATTRIBUTES = 0x0080;
    private const uint DELETE_ACCESS = 0x00010000;
    private const uint READ_CONTROL = 0x00020000;
    private const uint GENERIC_WRITE = 0x40000000;
    private const uint FILE_SHARE_READ = 0x00000001;
    private const uint FILE_SHARE_WRITE = 0x00000002;
    private const uint OPEN_EXISTING = 3;
    private const uint CREATE_NEW = 1;
    private const uint FILE_FLAG_WRITE_THROUGH = 0x80000000;
    private const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;
    private const uint FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000;
    private const uint FILE_ATTRIBUTE_DIRECTORY = 0x10;
    private const uint FILE_ATTRIBUTE_REPARSE_POINT = 0x400;
    private const int FileAttributeTagInfoClass = 9;
    private const int FileIdInfoClass = 18;
    private const int SE_FILE_OBJECT = 1;
    private const uint DACL_SECURITY_INFORMATION = 0x00000004;

    [StructLayout(LayoutKind.Sequential)] private struct FileAttributeTagInfo { internal uint Attributes, ReparseTag; }
    [StructLayout(LayoutKind.Sequential)] private struct FileIdInfo { internal ulong VolumeSerialNumber, FileIdLow, FileIdHigh; }
    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { internal int Length; internal IntPtr SecurityDescriptor; internal int InheritHandle; }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share, ref SecurityAttributes security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateDirectoryW")]
    private static extern bool CreateDirectoryW(string path, ref SecurityAttributes security);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileAttributeTagInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int infoClass, out FileIdInfo info, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool WriteFile(SafeFileHandle file, IntPtr buffer, uint bytesToWrite, out uint bytesWritten, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FlushFileBuffers(SafeFileHandle file);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern uint GetDriveTypeW(string rootPath);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string sddl, uint revision, out IntPtr descriptor, out uint size);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr LocalFree(IntPtr memory);
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
        string[] rawComponents = path.Substring(3).Split(new[] { '\\' }, StringSplitOptions.RemoveEmptyEntries);
        for (int i = 0; i < rawComponents.Length; i++)
            if (rawComponents[i] == "." || rawComponents[i] == ".." || rawComponents[i].IndexOfAny(new[] { ':', '\0' }) >= 0 ||
                rawComponents[i].EndsWith(".", StringComparison.Ordinal) || rawComponents[i].EndsWith(" ", StringComparison.Ordinal))
                throw new IOException("custody path contains an unsupported component");
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
            handles.Add(OpenDirectory(current));
            string[] components = full.Substring(3).Split(new[] { '\\' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < components.Length; i++)
            {
                if (components[i] == "." || components[i] == ".." || components[i].IndexOfAny(new[] { ':', '\0' }) >= 0 ||
                    components[i].EndsWith(".", StringComparison.Ordinal) || components[i].EndsWith(" ", StringComparison.Ordinal))
                    throw new IOException("custody path contains an unsupported component");
                current = System.IO.Path.Combine(current, components[i]);
                handles.Add(OpenDirectory(current));
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

    private static SafeFileHandle OpenDirectory(string path, bool includeDeleteAccess = false)
    {
        uint access = FILE_READ_ATTRIBUTES | READ_CONTROL | (includeDeleteAccess ? DELETE_ACCESS : 0);
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

    internal enum AllocationState { IntentFlushed, Created, Verified, IdentityRecorded, FailedBeforeCreation, FailedRetained }

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
#endif
        private SafeFileHandle runtimeHandle;
        private bool disposed;
        internal readonly string RuntimePath;
        internal readonly string JournalPath;
        internal readonly FileIdentity EvidenceIdentity;
        internal readonly FileIdentity JournalIdentity;
        internal FileIdentity RuntimeIdentity { get; private set; }
        internal AllocationState State { get; private set; }
        internal string Failure { get; private set; }
        internal bool IsAclVerified { get; private set; }
        internal bool IsIdentityRecorded { get { return State == AllocationState.IdentityRecorded; } }

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
            try { if (runtimeHandle != null) runtimeHandle.Dispose(); } catch (Exception e) { failure = e; }
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
            if ((raw.ControlFlags & ControlFlags.DiscretionaryAclProtected) == 0 || raw.DiscretionaryAcl == null || raw.DiscretionaryAcl.Count != 2)
                throw new IOException(objectName + " DACL is not the expected protected two-entry ACL");
            bool system = false, currentUser = false;
            foreach (GenericAce ace in raw.DiscretionaryAcl)
            {
                CommonAce common = ace as CommonAce;
                if (common == null || common.AceQualifier != AceQualifier.AccessAllowed || common.AceFlags != expectedFlags ||
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
