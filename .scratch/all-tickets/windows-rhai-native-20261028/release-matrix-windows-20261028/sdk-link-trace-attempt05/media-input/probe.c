__declspec(dllimport) void *__stdcall GetStdHandle(unsigned int);
__declspec(dllimport) int __stdcall WriteFile(void *, const void *, unsigned long,
                                             unsigned long *, void *);
__declspec(dllimport) void __stdcall ExitProcess(unsigned int);

void mainCRTStartup(void) {
    static const char marker[] = "RHAI_NATIVE_LINK_PROBE_EXECUTED\n";
    unsigned long written = 0;
    void *output = GetStdHandle((unsigned int)-11);
    if (!WriteFile(output, marker, sizeof(marker) - 1, &written, 0) ||
        written != sizeof(marker) - 1)
        ExitProcess(72);
    ExitProcess(0);
}
