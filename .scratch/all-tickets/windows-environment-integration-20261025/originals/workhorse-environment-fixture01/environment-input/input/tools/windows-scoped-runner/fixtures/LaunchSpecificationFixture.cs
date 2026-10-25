// Pure managed protocol/model fixture source. It does not read source paths,
// allocate a runtime directory, start a monitor, or authorize a workload.
using System;
using System.Text;

internal static class LaunchSpecificationFixture
{
    private static int failures;

    public static int Main()
    {
        const string source = @"Z:\never-created\source";
        const string executable = @"bin\runner.exe";
        CheckRoundTrip("empty argument list", source, executable, new string[0]);
        var atArgumentCountBound = new string[LaunchSpecification.MaximumArguments];
        for (int i = 0; i < atArgumentCountBound.Length; i++) atArgumentCountBound[i] = String.Empty;
        CheckRoundTrip("argument count exact bound", source, executable, atArgumentCountBound);
        CheckRoundTrip("argument byte exact bound", source, executable,
            new[] { new string('x', LaunchSpecification.MaximumFieldBytes) });
        CheckRoundTrip("literal arguments and Unicode", source, executable,
            new[] { "", "literal $HOME %TEMP% `cmd` & |", "snowman ☃ and 漢字" });
        ExpectQuoted("empty argument quoting", new[] { String.Empty },
            "\"C:\\staged\\runner.exe\" \"\"");
        ExpectQuoted("embedded quote quoting", new[] { "a\"b" },
            "\"C:\\staged\\runner.exe\" \"a\\\"b\"");
        ExpectQuoted("backslash before embedded quote quoting", new[] { new string(new[] { 'a', '\\', '\"', 'b' }) },
            "\"C:\\staged\\runner.exe\" \"a" + new string('\\', 3) + "\"b\"");
        ExpectQuoted("trailing backslash quoting", new[] { "trail\\" },
            "\"C:\\staged\\runner.exe\" \"trail" + new string('\\', 2) + "\"");
        ExpectQuoted("shell-looking input remains literal", new[] { "literal $HOME %TEMP% `cmd` & |" },
            "\"C:\\staged\\runner.exe\" \"literal $HOME %TEMP% `cmd` & |\"");

        var original = new[] { "before" };
        LaunchSpecification snapshot = LaunchSpecification.Create(source, executable, original);
        original[0] = "after";
        string[] returned = snapshot.Arguments;
        returned[0] = "also-after";
        Expect("caller argument mutation does not alter accepted snapshot", snapshot.Arguments[0] == "before");
        byte[] wire = snapshot.ToWire();
        byte[] returnedWire = snapshot.ToWire();
        returnedWire[0] ^= 0xff;
        Expect("returned wire bytes are a defensive copy", snapshot.ToWire()[0] == wire[0]);
        LaunchSpecification parsedSnapshot = LaunchSpecification.Parse(wire);
        wire[0] ^= 0xff;
        Expect("parser accepts a syntactically valid nonexistent source without filesystem access",
            parsedSnapshot.SourceDirectory == source);
        Expect("caller byte mutation does not alter parsed snapshot", parsedSnapshot.RelativeExecutable == executable && parsedSnapshot.Arguments[0] == "before");
        Expect("accepted model exposes only source, relative executable, and literal arguments",
            snapshot.SourceDirectory == source && snapshot.RelativeExecutable == executable && Equal(snapshot.Arguments, new[] { "before" }));

        ExpectError("wrong version", MakeWire("RHAI-LAUNCH/2", source, executable, new string[0]), LaunchSpecification.ErrorCode.WrongVersion);
        ExpectError("truncated record", Encoding.UTF8.GetBytes("RHAI-LAUNCH/1\nsource="), LaunchSpecification.ErrorCode.Truncated);
        ExpectError("malformed UTF-8", new byte[] { 0xff, 0xfe }, LaunchSpecification.ErrorCode.InvalidUtf8);
        ExpectError("duplicate source field", AddLine(MakeWire("RHAI-LAUNCH/1", source, executable, new string[0]), "source=WA=="), LaunchSpecification.ErrorCode.DuplicateField);
        ExpectError("unknown cleanup path field", AddLine(MakeWire("RHAI-LAUNCH/1", source, executable, new string[0]), "cleanup-path=Qzpc"), LaunchSpecification.ErrorCode.UnknownField);
        ExpectError("unknown policy override field", AddLine(MakeWire("RHAI-LAUNCH/1", source, executable, new string[0]), "lease-ms=999999"), LaunchSpecification.ErrorCode.UnknownField);
        ExpectError("trailing bytes", AppendAfterFinalNewline(MakeWire("RHAI-LAUNCH/1", source, executable, new string[0]), "x"), LaunchSpecification.ErrorCode.TrailingData);
        ExpectError("empty required source", MakeWire("RHAI-LAUNCH/1", "", executable, new string[0]), LaunchSpecification.ErrorCode.InvalidSourcePath);
        ExpectError("empty required executable", MakeWire("RHAI-LAUNCH/1", source, "", new string[0]), LaunchSpecification.ErrorCode.InvalidExecutablePath);
        ExpectError("invalid source path form", MakeWire("RHAI-LAUNCH/1", @"\\server\share", executable, new string[0]), LaunchSpecification.ErrorCode.InvalidSourcePath);
        ExpectError("invalid executable traversal", MakeWire("RHAI-LAUNCH/1", source, @"..\runner.exe", new string[0]), LaunchSpecification.ErrorCode.InvalidExecutablePath);
        ExpectError("control character rejected", MakeWire("RHAI-LAUNCH/1", source, executable, new[] { "bad\narg" }), LaunchSpecification.ErrorCode.InvalidCharacters);
        ExpectError("NUL character rejected", MakeWire("RHAI-LAUNCH/1", source, executable, new[] { "bad\0arg" }), LaunchSpecification.ErrorCode.InvalidCharacters);
        ExpectError("argument count overflow rejected", MakeRawWire("RHAI-LAUNCH/1\nsource=\nexecutable=\nargument-count=999999999999999999999999999999\n"), LaunchSpecification.ErrorCode.Overflow);
        ExpectError("missing argument record rejected", MakeRawWire("RHAI-LAUNCH/1\nsource=" + B64(source) + "\nexecutable=" + B64(executable) + "\nargument-count=1\n"), LaunchSpecification.ErrorCode.Truncated);
        ExpectError("duplicate argument index rejected", MakeRawWire("RHAI-LAUNCH/1\nsource=" + B64(source) + "\nexecutable=" + B64(executable) + "\nargument-count=1\nargument-0=\nargument-0=\n"), LaunchSpecification.ErrorCode.DuplicateField);

        string[] tooMany = new string[LaunchSpecification.MaximumArguments + 1];
        for (int i = 0; i < tooMany.Length; i++) tooMany[i] = "x";
        ExpectCreateError("argument count bound", source, executable, tooMany, LaunchSpecification.ErrorCode.ArgumentCount);
        ExpectCreateError("argument UTF-8 byte bound", source, executable, new[] { new string('漢', (LaunchSpecification.MaximumFieldBytes / 2) + 1) }, LaunchSpecification.ErrorCode.FieldTooLarge);
        ExpectCreateError("oversized UTF-16 input rejected before scanning", source, executable,
            new[] { new string('x', LaunchSpecification.MaximumFieldBytes + 1) }, LaunchSpecification.ErrorCode.FieldTooLarge);
        ExpectCreateError("oversized executable field rejected", source, new string('x', LaunchSpecification.MaximumFieldBytes + 1),
            new string[0], LaunchSpecification.ErrorCode.FieldTooLarge);
        ExpectCreateError("decoded command line bound", source, executable,
            new[] { new string('x', 900), new string('y', 900), new string('z', 900), new string('q', 900), new string('r', 900) },
            LaunchSpecification.ErrorCode.CommandLineTooLong);
        string[] exactCommand = { new string('x', 958), new string('y', 958), new string('z', 958), new string('q', 960) };
        LaunchSpecification commandAtBound = LaunchSpecification.Create(source, executable, exactCommand);
        Expect("decoded command line exact bound is accepted", commandAtBound.CommandLineChars == LaunchSpecification.MaximumCommandLineChars);
        ExpectCreateError("decoded command line one character over bound", source, executable,
            new[] { exactCommand[0], exactCommand[1], exactCommand[2], exactCommand[3] + "x" },
            LaunchSpecification.ErrorCode.CommandLineTooLong);
        ExpectCommandPathError("staged executable path length bound", new string('a', WindowsCustodyBackend.MaximumPathLengthForSpecification + 1), LaunchSpecification.ErrorCode.InvalidExecutablePath);
        ExpectCommandPathError("staged executable must be absolute", @"runner.exe", LaunchSpecification.ErrorCode.InvalidExecutablePath);
        ExpectCommandPathError("staged executable rejects reserved device component", @"C:\staged\CON\runner.exe", LaunchSpecification.ErrorCode.InvalidExecutablePath);
        ExpectError("encoded input byte bound", new byte[LaunchSpecification.MaximumWireBytes + 1], LaunchSpecification.ErrorCode.InputTooLarge);

        byte[] exactBound = FindWireAtExactInputLimit(source, executable);
        Expect("valid representation can reach exact encoded input bound", exactBound != null, true);
        if (exactBound != null) Expect("exact input bound parses", LaunchSpecification.Parse(exactBound) != null, true);

        return failures == 0 ? 0 : 1;
    }

    private static void CheckRoundTrip(string name, string source, string executable, string[] args)
    {
        LaunchSpecification first = LaunchSpecification.Create(source, executable, args);
        LaunchSpecification second = LaunchSpecification.Parse(first.ToWire());
        Expect(name + " round-trips exactly", second.SourceDirectory == source && second.RelativeExecutable == executable && Equal(args, second.Arguments));
    }

    private static void ExpectQuoted(string name, string[] args, string expected)
    {
        string actual = LaunchSpecification.Create(@"Z:\never-created\source", @"bin\runner.exe", args)
            .BuildQuotedCommandLine(@"C:\staged\runner.exe");
        Expect(name, String.Equals(actual, expected, StringComparison.Ordinal));
    }

    private static void ExpectCommandPathError(string name, string stagedPath, LaunchSpecification.ErrorCode expected)
    {
        try
        {
            LaunchSpecification.Create(@"Z:\never-created\source", @"bin\runner.exe", new string[0])
                .BuildQuotedCommandLine(stagedPath);
            failures++; Console.Error.WriteLine("FAIL " + name + ": accepted");
        }
        catch (LaunchSpecification.SpecificationException e)
        {
            if (e.Code != expected) { failures++; Console.Error.WriteLine("FAIL " + name + ": expected " + expected + ", got " + e.Code); }
            else Console.WriteLine("PASS " + name + ": " + e.Code);
        }
    }

    private static byte[] FindWireAtExactInputLimit(string source, string executable)
    {
        const int count = 10;
        var empty = new string[count];
        for (int i = 0; i < count; i++) empty[i] = String.Empty;
        int additionalBytes = LaunchSpecification.MaximumWireBytes - LaunchSpecification.Create(source, executable, empty).ToWire().Length;
        if (additionalBytes < 0 || (additionalBytes & 3) != 0) return null;
        int characters = additionalBytes / 4; // Each BMP CJK character is 3 UTF-8 bytes and 4 base64 bytes.
        int conservativeCommandChars = characters + count * 2 + (count - 1) + executable.Length + 2 +
            Math.Max(0, WindowsCustodyBackend.MaximumPathLengthForSpecification - executable.Length);
        if (characters > count * 341 || conservativeCommandChars > LaunchSpecification.MaximumCommandLineChars) return null;
        var args = new string[count];
        for (int i = 0; i < count; i++)
        {
            int take = Math.Min(341, characters);
            args[i] = new string('漢', take);
            characters -= take;
        }
        if (characters != 0) return null;
        byte[] candidate = LaunchSpecification.Create(source, executable, args).ToWire();
        return candidate.Length == LaunchSpecification.MaximumWireBytes ? candidate : null;
    }

    private static byte[] MakeWire(string header, string source, string executable, string[] args)
    {
        var b = new StringBuilder().Append(header).Append('\n').Append("source=").Append(B64(source)).Append('\n')
            .Append("executable=").Append(B64(executable)).Append('\n').Append("argument-count=").Append(args.Length).Append('\n');
        for (int i = 0; i < args.Length; i++) b.Append("argument-").Append(i).Append('=').Append(B64(args[i])).Append('\n');
        return Encoding.UTF8.GetBytes(b.ToString());
    }

    private static byte[] MakeRawWire(string text) { return Encoding.UTF8.GetBytes(text); }
    private static byte[] AddLine(byte[] bytes, string line) { return Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(bytes) + line + "\n"); }
    private static byte[] AppendAfterFinalNewline(byte[] bytes, string text) { return Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(bytes) + text); }
    private static string B64(string value) { return Convert.ToBase64String(Encoding.UTF8.GetBytes(value)); }
    private static bool Equal(string[] left, string[] right)
    {
        if (left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }

    private static void Expect(string name, bool actual) { Expect(name, actual, true); }
    private static void Expect(string name, bool actual, bool expected)
    {
        if (actual != expected) { failures++; Console.Error.WriteLine("FAIL " + name); }
        else Console.WriteLine("PASS " + name);
    }
    private static void ExpectError(string name, byte[] input, LaunchSpecification.ErrorCode expected)
    {
        try { LaunchSpecification.Parse(input); failures++; Console.Error.WriteLine("FAIL " + name + ": accepted"); }
        catch (LaunchSpecification.SpecificationException e)
        {
            if (e.Code != expected) { failures++; Console.Error.WriteLine("FAIL " + name + ": expected " + expected + ", got " + e.Code); }
            else Console.WriteLine("PASS " + name + ": " + e.Code);
        }
    }
    private static void ExpectCreateError(string name, string source, string executable, string[] args, LaunchSpecification.ErrorCode expected)
    {
        try { LaunchSpecification.Create(source, executable, args); failures++; Console.Error.WriteLine("FAIL " + name + ": accepted"); }
        catch (LaunchSpecification.SpecificationException e)
        {
            if (e.Code != expected) { failures++; Console.Error.WriteLine("FAIL " + name + ": expected " + expected + ", got " + e.Code); }
            else Console.WriteLine("PASS " + name + ": " + e.Code);
        }
    }
}
