typedef unsigned long DWORD;
typedef long LONG;
typedef int BOOL;
typedef void* HANDLE;
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD_PTR;

#define WINAPI __stdcall
#define INVALID_HANDLE_VALUE ((HANDLE)(LONG)-1)

extern "C" __declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
extern "C" __declspec(dllimport) void* WINAPI GetProcAddress(HMODULE, LPCSTR);
extern "C" __declspec(dllimport) DWORD WINAPI GetTickCount();
extern "C" __declspec(dllimport) HANDLE WINAPI CreateFileA(LPCSTR,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
extern "C" __declspec(dllimport) DWORD WINAPI SetFilePointer(HANDLE,LONG,LONG*,DWORD);
extern "C" __declspec(dllimport) BOOL WINAPI WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
extern "C" __declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);

static HMODULE g_original = 0;

static HMODULE original_module()
{
    if (!g_original)
        g_original = LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");
    return g_original;
}

static char hex_digit(DWORD value)
{
    value &= 0xFu;
    return value < 10u ? (char)('0' + value) : (char)('A' + value - 10u);
}

static void hex8(char* out, DWORD value)
{
    for (DWORD i = 0; i < 8u; ++i)
        out[i] = hex_digit(value >> (28u - i * 4u));
}

static void log_route(DWORD ordinal, DWORD target, const DWORD* args)
{
    HANDLE file = CreateFileA(
        "snd-volume-v24-diag.log",
        0x40000000u,
        0x00000003u,
        0,
        4u,
        0x00000080u,
        0);

    if (file == INVALID_HANDLE_VALUE)
        return;

    SetFilePointer(file, 0, 0, 2u);

    char line[96];
    DWORD pos = 0u;
    const char prefix[] = "volume_route_probe";

    for (DWORD i = 0; i < 18u; ++i)
        line[pos++] = prefix[i];

    DWORD values[7] = {
        ordinal,
        target,
        args ? args[0] : 0u,
        args ? args[1] : 0u,
        args ? args[2] : 0u,
        args ? args[3] : 0u,
        GetTickCount()
    };

    for (DWORD i = 0; i < 7u; ++i) {
        line[pos++] = ' ';
        hex8(line + pos, values[i]);
        pos += 8u;
    }

    line[pos++] = '\r';
    line[pos++] = '\n';

    DWORD written = 0u;
    WriteFile(file, line, pos, &written, 0);
    CloseHandle(file);
}

extern "C"
__declspec(noinline)
DWORD __cdecl v24_volume_route(DWORD ordinal, const DWORD* args)
    __asm__("_v24_volume_route");

extern "C"
__declspec(noinline)
DWORD __cdecl v24_volume_route(DWORD ordinal, const DWORD* args)
{
    HMODULE original = original_module();
    void* target = original
        ? GetProcAddress(original, (LPCSTR)(DWORD_PTR)ordinal)
        : 0;

    log_route(ordinal, (DWORD)target, args);
    return (DWORD)target;
}
