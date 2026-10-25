using System;
using System.IO;
using System.Diagnostics;
using System.Threading;

internal static class PayloadFixture
{
    private static int Main(string[] args)
    {
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
