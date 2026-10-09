using System;
using System.IO;
using System.Diagnostics;
using System.Threading;

internal static class PayloadFixture
{
    private static int Main(string[] args)
    {
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
}
