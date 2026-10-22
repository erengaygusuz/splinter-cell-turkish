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

__declspec(dllimport) BOOL WINAPI PlaySoundA(
    LPCSTR, HMODULE, DWORD);

__declspec(dllimport) DWORD WINAPI GetTickCount();

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

static DWORD g_raw_base = 0;
static DWORD g_raw_channel = 0;
static DWORD g_raw_channel_fade = 0;
static DWORD g_raw_fade = 0;
static DWORD g_external_played = 0;
static DWORD g_external_pending = 0;
static LONG g_external_request = -1;
static DWORD g_external_until = 0;
static DWORD g_external_extended_logged = 0;
static DWORD g_external_release_logged = 0;

static void append_text(char* out, DWORD* pos, const char* text) {
    for (DWORD i = 0; text[i]; ++i)
        out[(*pos)++] = text[i];
}

static void append_hex(char* out, DWORD* pos, DWORD value) {
    static const char digits[] = "0123456789ABCDEF";

    for (int shift = 28; shift >= 0; shift -= 4)
        out[(*pos)++] = digits[(value >> shift) & 15u];
}

static void write_line(
    const char* label,
    const DWORD* values,
    DWORD count)
{
    HANDLE file = CreateFileA(
        "snd-external-probe-v6.log",
        0x40000000u,
        0x00000001u | 0x00000002u,
        NULLPTR,
        4u,
        0x00000080u,
        (HANDLE)NULLPTR);

    if (file == (HANDLE)(LONG)-1)
        return;

    SetFilePointer(file, 0, (LONG*)NULLPTR, 2u);

    char line[256];
    DWORD pos = 0;

    append_text(line, &pos, label);

    for (DWORD i = 0; i < count; ++i) {
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

static DWORD editor_id_from_handle(DWORD handle) {
    if (!handle)
        return 0xFFFFFFFFu;

    typedef DWORD (__cdecl *Original)(DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_ulGetEditorIdFromSoundEventHandle");

    return original
        ? original(handle)
        : 0xFFFFFFFFu;
}

static Target* target_by_editor(DWORD editor_id) {
    for (DWORD i = 0; i < kTargetCount; ++i)
        if (g_targets[i].editor_id == editor_id)
            return &g_targets[i];

    return (Target*)NULLPTR;
}

static Target* target_in_args(
    const DWORD* args,
    DWORD count)
{
    for (DWORD t = 0; t < kTargetCount; ++t) {
        if (!g_targets[t].handle)
            continue;

        for (DWORD a = 0; a < count; ++a) {
            if (args[a] == g_targets[t].handle)
                return &g_targets[t];
        }
    }

    return (Target*)NULLPTR;
}

static void observe(
    const char* raw_label,
    const char* target_label,
    DWORD* raw_counter,
    const DWORD* args,
    DWORD count)
{
    // İlk 24 çağrıyı ham olarak gör.
    if (*raw_counter < 24u) {
        write_line(raw_label, args, count);
        ++(*raw_counter);
    }

    // Hedef handle görülürse çağrı sayısı sınırı olmadan kaydet.
    Target* target = target_in_args(args, count);

    if (target) {
        write_line(target_label, &target->editor_id, 1);
        write_line("target_args", args, count);
    }
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

    Target* target = target_by_editor(editor_id);

    if (target) {
        target->handle = handle;

        DWORD values[2] = {
            editor_id,
            handle
        };

        write_line("target_map", values, 2);
    }

    return handle;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
    __asm__("_probe_send_request");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
{
    DWORD args[4] = {a1, a2, a3, a4};

    observe(
        "raw_base",
        "target_base",
        &g_raw_base,
        args,
        4);

    DWORD editor_id = editor_id_from_handle(a3);

    if (g_raw_base <= 24u) {
        write_line("resolved_handle", &a3, 1);
        write_line("resolved_editor", &editor_id, 1);
    }

    Target* resolved_target = target_by_editor(editor_id);

    // u000011 / 0x003C0029:
    // "We'll let you do your thing here..."
    //
    // Original length: ~5.823 sec.
    // External WAV: 9 sec, with audible tail after 6 sec.
    if (editor_id == 0x003C0029u && !g_external_played) {
        g_external_played = 1;
        g_external_pending = 1;
        g_external_extended_logged = 0;
        g_external_release_logged = 0;

        write_line(
            "external_trigger",
            &editor_id,
            1);

        PlaySoundA(
            "sc-external-v5.wav",
            (HMODULE)NULLPTR,
            0x00000001u |  // SND_ASYNC
            0x00000002u |  // SND_NODEFAULT
            0x00020000u);  // SND_FILENAME
    }

    if (resolved_target) {
        write_line(
            "target_resolved_editor",
            &editor_id,
            1);

        write_line(
            "target_resolved_handle",
            &a3,
            1);
    }

    typedef LONG (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_lSendSoundRequest");

    LONG result = original
        ? original(a1, a2, a3, a4)
        : -1;

    if (g_external_pending) {
        g_external_pending = 0;
        g_external_request = result;
        g_external_until = GetTickCount() + 9000u;

        write_line(
            "external_request",
            (DWORD*)&g_external_request,
            1);

        write_line(
            "external_until",
            &g_external_until,
            1);
    }

    return result;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_on_channel(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5)
    __asm__("_probe_send_on_channel");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_on_channel(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5)
{
    DWORD args[5] = {a1, a2, a3, a4, a5};

    observe(
        "raw_channel",
        "target_channel",
        &g_raw_channel,
        args,
        5);

    typedef LONG (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_lSendSoundRequestOnChannel");

    return original
        ? original(a1, a2, a3, a4, a5)
        : -1;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_on_channel_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4,
    DWORD a5, DWORD a6, DWORD a7)
    __asm__("_probe_send_on_channel_fade");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_on_channel_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4,
    DWORD a5, DWORD a6, DWORD a7)
{
    DWORD args[7] = {
        a1, a2, a3, a4, a5, a6, a7
    };

    observe(
        "raw_channel_fade",
        "target_channel_fade",
        &g_raw_channel_fade,
        args,
        7);

    typedef LONG (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD,
        DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_lSendSoundRequestOnChannelWithFadeIn");

    return original
        ? original(a1, a2, a3, a4, a5, a6, a7)
        : -1;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_with_fade(
    DWORD a1, DWORD a2, DWORD a3,
    DWORD a4, DWORD a5, DWORD a6)
    __asm__("_probe_send_with_fade");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_with_fade(
    DWORD a1, DWORD a2, DWORD a3,
    DWORD a4, DWORD a5, DWORD a6)
{
    DWORD args[6] = {
        a1, a2, a3, a4, a5, a6
    };

    observe(
        "raw_fade",
        "target_fade",
        &g_raw_fade,
        args,
        6);

    typedef LONG (__cdecl *Original)(
        DWORD, DWORD, DWORD,
        DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_lSendSoundRequestWithFadeIn");

    return original
        ? original(a1, a2, a3, a4, a5, a6)
        : -1;
}

extern "C"
__declspec(noinline)
BOOL __cdecl probe_is_playing(DWORD request_id)
    __asm__("_probe_is_playing");

extern "C"
__declspec(noinline)
BOOL __cdecl probe_is_playing(DWORD request_id)
{
    typedef BOOL (__cdecl *Original)(DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_bIsSoundRequestPlaying");

    BOOL result = original
        ? original(request_id)
        : 0;

    if (
        g_external_request != -1 &&
        request_id == (DWORD)g_external_request
    ) {
        DWORD now = GetTickCount();
        LONG remaining =
            (LONG)(g_external_until - now);

        if (remaining > 0) {
            if (!result && !g_external_extended_logged) {
                g_external_extended_logged = 1;

                write_line(
                    "external_extend_playing",
                    &request_id,
                    1);
            }

            return TRUE;
        }

        if (!g_external_release_logged) {
            g_external_release_logged = 1;

            write_line(
                "external_release",
                &request_id,
                1);
        }
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
