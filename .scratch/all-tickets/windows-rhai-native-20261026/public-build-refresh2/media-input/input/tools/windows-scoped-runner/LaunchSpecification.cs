// Immutable, bounded launch specification codec. Parsing validates syntax
// only; it performs no filesystem I/O, runtime-directory allocation, process
// launch, or authority check. The monitor remains the only source of
// runtime/evidence identities.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

internal sealed class LaunchSpecification
{
    internal const int MaximumWireBytes = 8192;
    internal const int MaximumArguments = 32;
    internal const int MaximumFieldBytes = 1024;
    internal const int MaximumCommandLineChars = 4096;
    private const string Header = "RHAI-LAUNCH/1";
    private static readonly UTF8Encoding StrictUtf8 = new UTF8Encoding(false, true);

    internal enum ErrorCode
    {
        InputTooLarge, InvalidUtf8, WrongVersion, Truncated, TrailingData,
        MalformedField, DuplicateField, UnknownField, Overflow, ArgumentCount,
        FieldTooLarge, InvalidSourcePath, InvalidExecutablePath, InvalidCharacters,
        InvalidField, CommandLineTooLong
    }

    internal sealed class SpecificationException : FormatException
    {
        internal readonly ErrorCode Code;
        internal SpecificationException(ErrorCode code, string message) : base(message) { Code = code; }
        internal SpecificationException(ErrorCode code, string message, Exception inner) : base(message, inner) { Code = code; }
    }

    private readonly string sourceDirectory;
    private readonly string relativeExecutable;
    private readonly string[] arguments;
    private readonly int commandLineChars;

    internal string SourceDirectory { get { return sourceDirectory; } }
    internal string RelativeExecutable { get { return relativeExecutable; } }
    internal string[] Arguments { get { return (string[])arguments.Clone(); } }
    internal int CommandLineChars { get { return commandLineChars; } }

    private LaunchSpecification(string source, string executable, string[] args, int commandChars)
    {
        sourceDirectory = source;
        relativeExecutable = executable;
        arguments = (string[])args.Clone();
        commandLineChars = commandChars;
    }

    internal static LaunchSpecification Create(string source, string executable, string[] args)
    {
        if (args == null) throw Failure(ErrorCode.ArgumentCount, "argument array is required");
        if (args.Length > MaximumArguments) throw Failure(ErrorCode.ArgumentCount, "argument count exceeds the fixed bound");
        string[] copied;
        try { copied = (string[])args.Clone(); }
        catch (Exception e) { throw new SpecificationException(ErrorCode.ArgumentCount, "unable to snapshot arguments", e); }
        ValidateText(source, "source directory");
        ValidateText(executable, "relative executable");
        for (int i = 0; i < copied.Length; i++) ValidateText(copied[i], "argument " + i);
        ValidateFieldSize(source, "source directory");
        ValidateFieldSize(executable, "relative executable");
        for (int i = 0; i < copied.Length; i++) ValidateFieldSize(copied[i], "argument " + i);

        try { WindowsCustodyBackend.ValidateLaunchSourceDirectorySyntax(source); }
        catch (Exception e) { throw new SpecificationException(ErrorCode.InvalidSourcePath, "source directory path syntax is invalid", e); }
        try { WindowsCustodyBackend.ValidateExecutableRelativePathSyntax(executable); }
        catch (Exception e) { throw new SpecificationException(ErrorCode.InvalidExecutablePath, "relative executable path syntax is invalid", e); }

        int commandChars = CountCommandLineChars(executable, copied);
        // The staged executable's eventual absolute path is bounded by the
        // backend's fixed 248-character path limit. Account for that prefix
        // before accepting the specification; no caller path is trusted.
        commandChars = checked(commandChars + Math.Max(0, WindowsCustodyBackend.MaximumPathLengthForSpecification - executable.Length));
        if (commandChars > MaximumCommandLineChars)
            throw Failure(ErrorCode.CommandLineTooLong, "decoded Windows command line exceeds the fixed bound");

        var result = new LaunchSpecification(source, executable, copied, commandChars);
        if (result.ToWire().Length > MaximumWireBytes) throw Failure(ErrorCode.InputTooLarge, "encoded launch specification exceeds the fixed byte bound");
        return result;
    }

    internal static LaunchSpecification Parse(byte[] encoded)
    {
        if (encoded == null) throw Failure(ErrorCode.MalformedField, "launch specification bytes are required");
        if (encoded.Length > MaximumWireBytes) throw Failure(ErrorCode.InputTooLarge, "encoded launch specification exceeds the fixed byte bound");
        byte[] snapshot = (byte[])encoded.Clone();
        string text;
        try { text = StrictUtf8.GetString(snapshot); }
        catch (DecoderFallbackException e) { throw new SpecificationException(ErrorCode.InvalidUtf8, "launch specification is not valid UTF-8", e); }
        if (text.Length == 0) throw Failure(ErrorCode.Truncated, "launch specification is empty");
        if (text[text.Length - 1] != '\n')
        {
            if (text.EndsWith("=", StringComparison.Ordinal)) throw Failure(ErrorCode.Truncated, "launch specification ends inside a field");
            throw Failure(ErrorCode.TrailingData, "launch specification has trailing bytes or lacks its final delimiter");
        }
        string[] lines = text.Split('\n');
        if (lines.Length < 2 || lines[lines.Length - 1].Length != 0) throw Failure(ErrorCode.MalformedField, "launch specification framing is malformed");
        if (!String.Equals(lines[0], Header, StringComparison.Ordinal)) throw Failure(ErrorCode.WrongVersion, "launch specification version is unsupported");
        if (lines.Length > MaximumArguments + 5) throw Failure(ErrorCode.ArgumentCount, "launch specification contains too many fields");

        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 1; i < lines.Length - 1; i++)
        {
            string line = lines[i];
            int separator = line.IndexOf('=');
            if (separator <= 0) throw Failure(ErrorCode.MalformedField, "launch specification contains a malformed field");
            string name = line.Substring(0, separator);
            string value = line.Substring(separator + 1);
            if (name != "source" && name != "executable" && name != "argument-count" && !IsArgumentField(name))
                throw Failure(ErrorCode.UnknownField, "launch specification contains an unknown field: " + name);
            if (fields.ContainsKey(name)) throw Failure(ErrorCode.DuplicateField, "launch specification contains a duplicate field: " + name);
            fields.Add(name, value);
        }

        string sourceEncoded, executableEncoded, countEncoded;
        if (!fields.TryGetValue("source", out sourceEncoded)) throw Failure(ErrorCode.InvalidSourcePath, "source directory field is missing");
        if (!fields.TryGetValue("executable", out executableEncoded)) throw Failure(ErrorCode.InvalidExecutablePath, "relative executable field is missing");
        if (!fields.TryGetValue("argument-count", out countEncoded)) throw Failure(ErrorCode.Truncated, "argument count field is missing");
        int count = ParseCount(countEncoded);
        if (count > MaximumArguments) throw Failure(ErrorCode.ArgumentCount, "argument count exceeds the fixed bound");

        string source = DecodeValue(sourceEncoded, "source directory");
        string executable = DecodeValue(executableEncoded, "relative executable");
        var args = new string[count];
        for (int i = 0; i < count; i++)
        {
            string value;
            if (!fields.TryGetValue("argument-" + i.ToString(CultureInfo.InvariantCulture), out value))
                throw Failure(ErrorCode.Truncated, "argument record is missing at index " + i);
            args[i] = DecodeValue(value, "argument " + i);
        }
        foreach (string field in fields.Keys)
            if (IsArgumentField(field) && ParseArgumentIndex(field) >= count)
                throw Failure(ErrorCode.InvalidField, "argument record index exceeds declared argument count");

        LaunchSpecification result = Create(source, executable, args);
        if (!BytesEqual(snapshot, result.ToWire()))
            throw Failure(ErrorCode.MalformedField, "launch specification is not in canonical version-1 form");
        return result;
    }

    internal byte[] ToWire()
    {
        var text = new StringBuilder(Header).Append('\n')
            .Append("source=").Append(EncodeValue(sourceDirectory)).Append('\n')
            .Append("executable=").Append(EncodeValue(relativeExecutable)).Append('\n')
            .Append("argument-count=").Append(arguments.Length.ToString(CultureInfo.InvariantCulture)).Append('\n');
        for (int i = 0; i < arguments.Length; i++)
            text.Append("argument-").Append(i.ToString(CultureInfo.InvariantCulture)).Append('=').Append(EncodeValue(arguments[i])).Append('\n');
        byte[] result;
        try { result = StrictUtf8.GetBytes(text.ToString()); }
        catch (EncoderFallbackException e) { throw new SpecificationException(ErrorCode.InvalidCharacters, "launch specification contains invalid UTF-16", e); }
        if (result.Length > MaximumWireBytes) throw Failure(ErrorCode.InputTooLarge, "encoded launch specification exceeds the fixed byte bound");
        return result;
    }

    // The returned string uses CreateProcess/Windows argv quoting. It is not a
    // shell command and is not wired to workload execution in this source step.
    internal string BuildQuotedCommandLine(string stagedExecutablePath)
    {
        if (stagedExecutablePath == null) throw Failure(ErrorCode.InvalidExecutablePath, "staged executable path is required");
        if (stagedExecutablePath.Length > WindowsCustodyBackend.MaximumPathLengthForSpecification)
            throw Failure(ErrorCode.InvalidExecutablePath, "staged executable path exceeds the fixed path bound");
        ValidateText(stagedExecutablePath, "staged executable path");
        try { WindowsCustodyBackend.ValidateLaunchExecutablePathSyntax(stagedExecutablePath); }
        catch (Exception e) { throw new SpecificationException(ErrorCode.InvalidExecutablePath, "staged executable path syntax is invalid", e); }
        var command = new StringBuilder(Quote(stagedExecutablePath));
        for (int i = 0; i < arguments.Length; i++) command.Append(' ').Append(Quote(arguments[i]));
        if (command.Length > MaximumCommandLineChars) throw Failure(ErrorCode.CommandLineTooLong, "decoded Windows command line exceeds the fixed bound");
        return command.ToString();
    }

    private static int CountCommandLineChars(string executable, string[] args)
    {
        int count = Quote(executable).Length;
        for (int i = 0; i < args.Length; i++) count = checked(count + 1 + Quote(args[i]).Length);
        return count;
    }

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

    private static void ValidateText(string value, string description)
    {
        if (value == null) throw Failure(ErrorCode.InvalidCharacters, description + " is required");
        if (value.Length > MaximumFieldBytes) throw Failure(ErrorCode.FieldTooLarge, description + " exceeds the fixed UTF-8 byte bound");
        for (int i = 0; i < value.Length; i++)
            if (Char.IsControl(value[i])) throw Failure(ErrorCode.InvalidCharacters, description + " contains a control character");
        try { StrictUtf8.GetByteCount(value); }
        catch (EncoderFallbackException e) { throw new SpecificationException(ErrorCode.InvalidCharacters, description + " contains invalid UTF-16", e); }
    }

    private static void ValidateFieldSize(string value, string description)
    {
        int bytes;
        try { bytes = StrictUtf8.GetByteCount(value); }
        catch (EncoderFallbackException e) { throw new SpecificationException(ErrorCode.InvalidCharacters, description + " contains invalid UTF-16", e); }
        if (bytes > MaximumFieldBytes) throw Failure(ErrorCode.FieldTooLarge, description + " exceeds the fixed UTF-8 byte bound");
    }

    private static string DecodeValue(string encoded, string description)
    {
        byte[] bytes;
        try
        {
            bytes = Convert.FromBase64String(encoded);
            if (!String.Equals(Convert.ToBase64String(bytes), encoded, StringComparison.Ordinal))
                throw Failure(ErrorCode.InvalidField, description + " has noncanonical base64");
        }
        catch (FormatException e)
        {
            if (e is SpecificationException) throw;
            throw new SpecificationException(ErrorCode.InvalidField, description + " has malformed base64", e);
        }
        if (bytes.Length > MaximumFieldBytes) throw Failure(ErrorCode.FieldTooLarge, description + " exceeds the fixed UTF-8 byte bound");
        try { return StrictUtf8.GetString(bytes); }
        catch (DecoderFallbackException e) { throw new SpecificationException(ErrorCode.InvalidUtf8, description + " is not valid UTF-8", e); }
    }

    private static int ParseCount(string value)
    {
        int result;
        if (String.IsNullOrEmpty(value)) throw Failure(ErrorCode.MalformedField, "argument count is empty");
        for (int i = 0; i < value.Length; i++) if (value[i] < '0' || value[i] > '9') throw Failure(ErrorCode.MalformedField, "argument count is not unsigned decimal");
        if (!Int32.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out result))
            throw Failure(ErrorCode.Overflow, "argument count overflows the supported integer range");
        return result;
    }

    private static bool IsArgumentField(string value)
    {
        if (!value.StartsWith("argument-", StringComparison.Ordinal)) return false;
        int ignored; return Int32.TryParse(value.Substring(9), NumberStyles.None, CultureInfo.InvariantCulture, out ignored);
    }

    private static int ParseArgumentIndex(string value)
    {
        int result;
        if (!Int32.TryParse(value.Substring(9), NumberStyles.None, CultureInfo.InvariantCulture, out result))
            throw Failure(ErrorCode.Overflow, "argument record index overflows the supported integer range");
        return result;
    }

    private static string EncodeValue(string value) { return Convert.ToBase64String(StrictUtf8.GetBytes(value)); }
    private static bool BytesEqual(byte[] left, byte[] right)
    {
        if (left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static SpecificationException Failure(ErrorCode code, string message) { return new SpecificationException(code, message); }
}
