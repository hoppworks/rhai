__declspec(dllimport) void __stdcall ExitProcess(unsigned int);
void mainCRTStartup(void) { ExitProcess(0); }
