extern "C" {
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD;
#define WINAPI __stdcall
__declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
__declspec(dllimport) void* WINAPI GetProcAddress(HMODULE, LPCSTR);
__declspec(dllimport) int WINAPI FreeLibrary(HMODULE);
__declspec(dllimport) void WINAPI ExitProcess(DWORD);
}

extern "C" void __cdecl start() {
    HMODULE proxy = LoadLibraryA("SNDDSound3DDLL_VBR_poc.dll");
    if (!proxy) ExitProcess(10);
    if (!GetProcAddress(proxy, "_SND_fn_hGetSoundEventHandleFromEditorId@4"))
        ExitProcess(11);
    if (!GetProcAddress(proxy, "SND_fn_lSendSoundRequest")) ExitProcess(12);
    HMODULE original = LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");
    if (!original) ExitProcess(13);
    if (!GetProcAddress(original, "SND_fn_bAreWavPresent")) ExitProcess(14);
    // Resolving this forwarded export forces the renamed original DLL to load.
    if (!GetProcAddress(proxy, "SND_fn_bAreWavPresent")) ExitProcess(15);
    // Do not unload the legacy audio engine in the harness: its detach path
    // waits on driver state that only exists during a real game shutdown.
    ExitProcess(0);
}
