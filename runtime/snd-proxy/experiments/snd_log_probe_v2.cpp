// Splinter Cell SND log probe v2.
// No overlay, no fallback thread, no audio replacement.
// Hooks only:
//   GetSoundEventHandleFromEditorId
//   SendSoundRequest

extern "C" {

typedef void* HANDLE;
typedef void* HINSTANCE;
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD;
typedef long LONG;
typedef int BOOL;
typedef void* LPVOID;

#define WINAPI __stdcall
#define TRUE 1
#define NULLPTR ((void*)0)

__declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
__declspec(dllimport) void* WINAPI GetProcAddress(HMODULE, LPCSTR);
__declspec(dllimport) BOOL WINAPI DisableThreadLibraryCalls(HMODULE);

__declspec(dllimport) HANDLE WINAPI CreateFileA(
    LPCSTR, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI WriteFile(
    HANDLE, const void*, DWORD, DWORD*, void*);
__declspec(dllimport) DWORD WINAPI SetFilePointer(
    HANDLE, LONG, LONG*, DWORD);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);

}

struct Target {
    DWORD editor_id;
    DWORD handle;
};

static Target g_targets[] = {
    {0x003c0000u, 0u},
    {0x003c0001u, 0u},
    {0x003c0002u, 0u},
    {0x003c0003u, 0u},
    {0x003c0004u, 0u},
};

static const DWORD kTargetCount =
    sizeof(g_targets) / sizeof(g_targets[0]);

static HMODULE g_original = (HMODULE)NULLPTR;

static DWORD text_length(const char* text) {
    DWORD n = 0;
    while (text[n]) ++n;
    return n;
}

static void append_text(char* out, DWORD* pos, const char* text) {
    for (DWORD i = 0; text[i]; ++i)
        out[(*pos)++] = text[i];
}

static void append_hex(char* out, DWORD* pos, DWORD value) {
    static const char digits[] = "0123456789ABCDEF";
    for (int shift = 28; shift >= 0; shift -= 4)
        out[(*pos)++] = digits[(value >> shift) & 15u];
}

static void write_values(
    const char* label,
    DWORD a,
    DWORD b,
    DWORD c,
    DWORD d,
    DWORD e)
{
    HANDLE file = CreateFileA(
        "snd-log-probe-v2.log",
        0x40000000u,                 // GENERIC_WRITE
        0x00000001u | 0x00000002u, // FILE_SHARE_READ | WRITE
        NULLPTR,
        4u,                         // OPEN_ALWAYS
        0x00000080u,                // FILE_ATTRIBUTE_NORMAL
        (HANDLE)NULLPTR);

    if (file == (HANDLE)(LONG)-1)
        return;

    SetFilePointer(file, 0, (LONG*)NULLPTR, 2u); // FILE_END

    char line[192];
    DWORD pos = 0;

    append_text(line, &pos, label);

    DWORD values[5] = {a, b, c, d, e};

    for (DWORD i = 0; i < 5; ++i) {
        line[pos++] = ' ';
        append_hex(line, &pos, values[i]);
    }

    line[pos++] = '\r';
    line[pos++] = '\n';

    DWORD written = 0;
    WriteFile(file, line, pos, &written, NULLPTR);
    CloseHandle(file);
}

static HMODULE original_module() {
    if (!g_original)
        g_original = LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");

    return g_original;
}

static Target* target_by_editor_id(DWORD editor_id) {
    for (DWORD i = 0; i < kTargetCount; ++i)
        if (g_targets[i].editor_id == editor_id)
            return &g_targets[i];

    return (Target*)NULLPTR;
}

static Target* target_by_handle(DWORD handle) {
    if (!handle)
        return (Target*)NULLPTR;

    for (DWORD i = 0; i < kTargetCount; ++i)
        if (g_targets[i].handle == handle)
            return &g_targets[i];

    return (Target*)NULLPTR;
}

extern "C"
__declspec(noinline)
DWORD __stdcall probe_get_handle(DWORD editor_id)
    __asm__("_probe_get_handle@4");

extern "C"
__declspec(noinline)
DWORD __stdcall probe_get_handle(DWORD editor_id) {
    typedef DWORD (__stdcall *Original)(DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "_SND_fn_hGetSoundEventHandleFromEditorId@4");

    DWORD handle = original ? original(editor_id) : 0;

    Target* target = target_by_editor_id(editor_id);

    if (target) {
        target->handle = handle;
        write_values(
            "target_map",
            editor_id,
            handle,
            0,
            0,
            0);
    }

    return handle;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request(
    DWORD first,
    DWORD second,
    DWORD event_handle,
    DWORD fourth)
    __asm__("_probe_send_request");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request(
    DWORD first,
    DWORD second,
    DWORD event_handle,
    DWORD fourth)
{
    typedef LONG (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Target* target = target_by_handle(event_handle);

    if (target) {
        write_values(
            "target_send",
            target->editor_id,
            first,
            second,
            event_handle,
            fourth);
    }

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_lSendSoundRequest");

    LONG result = original
        ? original(first, second, event_handle, fourth)
        : -1;

    if (target) {
        write_values(
            "target_return",
            target->editor_id,
            event_handle,
            (DWORD)result,
            0,
            0);
    }

    return result;
}

extern "C"
BOOL WINAPI DllMain(
    HINSTANCE instance,
    DWORD reason,
    LPVOID)
{
    if (reason == 1u)
        DisableThreadLibraryCalls((HMODULE)instance);

    return TRUE;
}
