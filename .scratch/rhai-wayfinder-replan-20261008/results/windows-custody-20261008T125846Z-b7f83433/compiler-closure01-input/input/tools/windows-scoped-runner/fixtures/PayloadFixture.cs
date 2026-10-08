using System;
using System.IO;

internal static class PayloadFixture
{
    private static int Main(string[] args)
    {
        if (args.Length != 1) return 64;
        File.WriteAllText(args[0], "payload-started\r\n");
        return 0;
    }
}
