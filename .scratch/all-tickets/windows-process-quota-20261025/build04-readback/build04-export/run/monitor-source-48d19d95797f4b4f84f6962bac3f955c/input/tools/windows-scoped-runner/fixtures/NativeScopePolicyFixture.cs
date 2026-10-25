// Pure policy checks run as an owned native child, before any public payload.
// Environment changes are confined to this process; no directory is created.
using System;
using System.IO;

internal static class NativeScopePolicyFixture
{
    private static void Check(bool condition, string message)
    { if (!condition) throw new InvalidOperationException(message); }

    private static void Rejected(string value, string name)
    {
        Environment.SetEnvironmentVariable("AGENT_RUNTIME_DIR", value);
        bool rejected = false;
        try { string root = WindowsCustodyBackend.AuthorizedRoot; }
        catch (IOException) { rejected = true; }
        Check(rejected, "private scope must reject " + name);
    }

    public static int Main()
    {
        try
        {
            string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string prefix = Path.Combine(profile, @".local\share\agent-builds\rhai");
            string valid = Path.Combine(prefix, @"scope-policy-fixture\run");
            Environment.SetEnvironmentVariable("AGENT_RUNTIME_DIR", valid);
            Check(WindowsCustodyBackend.AuthorizedRoot == valid,
                "native custody root must equal the explicitly selected current-user private scope");
            Rejected(null, "missing scope");
            Rejected(@"C:\RhaiQuality\runs", "legacy shared root");
            Rejected(Path.Combine(prefix, @"scope-policy-fixture\run\extra"), "extra depth");
            Rejected(Path.Combine(prefix, @"scope-policy-fixture\..\other\run"), "traversal");
            Rejected(Path.Combine(prefix, @"scope-policy-fixture.\run"), "ambiguous trailing dot");
            Rejected(Path.Combine(prefix, @"scope-policy-fixture\RUN"), "noncanonical run component");
            Rejected(valid.Replace('\\', '/'), "noncanonical separators");
            Rejected(@"\\server\share\run", "UNC root");
            Rejected(Path.Combine(prefix, new string('a', 97) + @"\run"), "overlong session");
            Environment.SetEnvironmentVariable("AGENT_RUNTIME_DIR", valid);
            Check(WindowsCustodyBackend.AuthorizedRoot == valid, "valid root after negative controls");
            Console.WriteLine("PASS_NATIVE_PRIVATE_SCOPE: exact current-user root; missing/legacy/depth/traversal/dot/case/separator/UNC/length denied; no filesystem effects");
            return 0;
        }
        catch (Exception error)
        { Console.Error.WriteLine("NATIVE_PRIVATE_SCOPE_ASSERTION: " + error); return 1; }
    }
}
