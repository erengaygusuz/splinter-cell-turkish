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

static const DWORD g_diag_editor_ids[408] =
{
    0x00660002u,
    0x00660001u,
    0x00660000u,
    0x003C002Au,
    0x00820001u,
    0x003C002Bu,
    0x003C002Cu,
    0x003C002Du,
    0x003C002Eu,
    0x003C0028u,
    0x003C0029u,
    0x003C002Fu,
    0x003C0000u,
    0x003C0001u,
    0x003C0002u,
    0x003C0003u,
    0x003C0004u,
    0x003C0007u,
    0x003C0008u,
    0x003C0009u,
    0x003C000Au,
    0x003C000Bu,
    0x003C000Cu,
    0x003C000Du,
    0x003C000Eu,
    0x003C000Fu,
    0x003C0010u,
    0x003C0011u,
    0x003C0012u,
    0x00820000u,
    0x003C0014u,
    0x003C0017u,
    0x003C0019u,
    0x003C001Cu,
    0x003C001Eu,
    0x003C0020u,
    0x003C0022u,
    0x003C0024u,
    0x003D0004u,
    0x003D0006u,
    0x003D0008u,
    0x003D0039u,
    0x003D0030u,
    0x003D0031u,
    0x003D002Fu,
    0x003D000Fu,
    0x003D0011u,
    0x003D0000u,
    0x003D0029u,
    0x003D0001u,
    0x003D003Du,
    0x003D000Du,
    0x003D002Au,
    0x003D002Bu,
    0x003D002Cu,
    0x003D000Eu,
    0x003D0014u,
    0x003D0015u,
    0x003D0017u,
    0x003D0018u,
    0x003D001Au,
    0x003D001Bu,
    0x003D001Du,
    0x003D001Fu,
    0x003D0020u,
    0x003D0021u,
    0x00840000u,
    0x00840001u,
    0x00840002u,
    0x00840003u,
    0x00840004u,
    0x00840014u,
    0x00840015u,
    0x006D0003u,
    0x006D0000u,
    0x006D0001u,
    0x00840005u,
    0x00840007u,
    0x00840009u,
    0x0084000Bu,
    0x0084000Du,
    0x003E0011u,
    0x003E0012u,
    0x003E0013u,
    0x003E0025u,
    0x003E0026u,
    0x003E0027u,
    0x003E0028u,
    0x003E0029u,
    0x003E002Au,
    0x003E002Bu,
    0x003E0014u,
    0x003F0003u,
    0x003F0004u,
    0x003F0005u,
    0x003F0006u,
    0x003F0007u,
    0x003F0008u,
    0x003F0038u,
    0x003F003Au,
    0x003F003Cu,
    0x003F0020u,
    0x003F0022u,
    0x003F0024u,
    0x003F0026u,
    0x003F0009u,
    0x003F000Bu,
    0x003F000Du,
    0x003F000Fu,
    0x003F0011u,
    0x003F0013u,
    0x003F0015u,
    0x003F0017u,
    0x003F0019u,
    0x003F001Bu,
    0x003F001Cu,
    0x003F001Eu,
    0x00400034u,
    0x006D0002u,
    0x00400000u,
    0x00400001u,
    0x00400002u,
    0x00400003u,
    0x00400004u,
    0x00400005u,
    0x00400006u,
    0x00400007u,
    0x00400008u,
    0x00400023u,
    0x00400024u,
    0x00400025u,
    0x00400040u,
    0x00400041u,
    0x00400042u,
    0x00400043u,
    0x00400044u,
    0x0040000Bu,
    0x0040000Du,
    0x0040000Fu,
    0x00400011u,
    0x00400013u,
    0x00400015u,
    0x00400017u,
    0x00400019u,
    0x0040001Au,
    0x0040001Cu,
    0x00400030u,
    0x00400031u,
    0x00400032u,
    0x00400020u,
    0x00400021u,
    0x00400022u,
    0x00410000u,
    0x00410001u,
    0x00410002u,
    0x00410003u,
    0x00410004u,
    0x00410005u,
    0x00410006u,
    0x00410007u,
    0x00410008u,
    0x00410009u,
    0x0041000Au,
    0x0041000Bu,
    0x0041000Cu,
    0x00410013u,
    0x006F0000u,
    0x006F0001u,
    0x006F0002u,
    0x006F0004u,
    0x006F0005u,
    0x006F0006u,
    0x00700001u,
    0x00700002u,
    0x00700013u,
    0x00700017u,
    0x00700018u,
    0x0070001Au,
    0x0070001Bu,
    0x0070001Cu,
    0x00700003u,
    0x0070002Du,
    0x0070001Du,
    0x0070001Fu,
    0x00700021u,
    0x00700023u,
    0x00700025u,
    0x00700027u,
    0x00700029u,
    0x00730003u,
    0x00890000u,
    0x00890001u,
    0x00890002u,
    0x00890003u,
    0x0072001Au,
    0x0072001Bu,
    0x0072001Cu,
    0x00720024u,
    0x00720025u,
    0x00720026u,
    0x00720028u,
    0x00710013u,
    0x00710015u,
    0x00710016u,
    0x00710017u,
    0x00710018u,
    0x00710019u,
    0x0071002Du,
    0x0071002Eu,
    0x0071002Fu,
    0x00710030u,
    0x00710031u,
    0x00710010u,
    0x00710011u,
    0x00710012u,
    0x0071006Eu,
    0x0071004Cu,
    0x0071004Fu,
    0x00710053u,
    0x00710055u,
    0x00710058u,
    0x0071005Au,
    0x0071005Cu,
    0x00660014u,
    0x00420001u,
    0x00420003u,
    0x00420004u,
    0x00420005u,
    0x00420006u,
    0x00420007u,
    0x00420008u,
    0x0043001Au,
    0x0043001Cu,
    0x0043001Fu,
    0x00430021u,
    0x00430023u,
    0x00430044u,
    0x00430046u,
    0x00430048u,
    0x0043004Au,
    0x0043004Cu,
    0x0043004Eu,
    0x00430050u,
    0x00430052u,
    0x00430009u,
    0x0043000Bu,
    0x0043000Cu,
    0x0043000Du,
    0x00430016u,
    0x00430017u,
    0x00430018u,
    0x00430019u,
    0x00430000u,
    0x00430002u,
    0x00430025u,
    0x00430026u,
    0x00430027u,
    0x00430028u,
    0x00430029u,
    0x0043005Au,
    0x0043005Bu,
    0x0043005Cu,
    0x00430057u,
    0x00430058u,
    0x00430059u,
    0x0043000Eu,
    0x00430010u,
    0x00430012u,
    0x00430014u,
    0x0043005Eu,
    0x0043005Fu,
    0x00100032u,
    0x00100033u,
    0x00100034u,
    0x0010002Fu,
    0x00100030u,
    0x00100031u,
    0x00100002u,
    0x00100004u,
    0x00100006u,
    0x00100008u,
    0x00100035u,
    0x00100038u,
    0x0010003Au,
    0x0010003Cu,
    0x0010003Eu,
    0x00100040u,
    0x00100042u,
    0x004C000Au,
    0x004C000Bu,
    0x004C000Cu,
    0x004C000Du,
    0x004C000Eu,
    0x004C000Fu,
    0x004C0010u,
    0x004C0011u,
    0x004C0024u,
    0x004C0025u,
    0x004C0026u,
    0x004C0027u,
    0x004C0028u,
    0x004C0029u,
    0x004C002Au,
    0x004C002Eu,
    0x004C0023u,
    0x004C0006u,
    0x004C0007u,
    0x004C0008u,
    0x004D0002u,
    0x004D0003u,
    0x004D0004u,
    0x004D000Au,
    0x004D0015u,
    0x004D0027u,
    0x004D0028u,
    0x004D0029u,
    0x004D0017u,
    0x004D0019u,
    0x004D001Bu,
    0x004D001Du,
    0x004D001Fu,
    0x007A0010u,
    0x007A0012u,
    0x007A0014u,
    0x007A0016u,
    0x007A0018u,
    0x007A001Au,
    0x007A001Cu,
    0x007A0033u,
    0x007A0034u,
    0x007A0035u,
    0x007A0036u,
    0x007A0037u,
    0x007B0000u,
    0x007A0043u,
    0x007A0044u,
    0x007A0045u,
    0x007A0049u,
    0x007A004Au,
    0x007A004Bu,
    0x007A004Cu,
    0x007A0025u,
    0x00880001u,
    0x00880003u,
    0x00880004u,
    0x00880005u,
    0x0088000Cu,
    0x004E001Cu,
    0x004E001Eu,
    0x004E0029u,
    0x004E002Au,
    0x004E002Bu,
    0x004E001Bu,
    0x007C0001u,
    0x007C0000u,
    0x004E000Fu,
    0x004E0011u,
    0x004F0014u,
    0x004F0002u,
    0x004F000Au,
    0x004F000Bu,
    0x004F000Cu,
    0x004F002Du,
    0x004F002Eu,
    0x004F002Fu,
    0x004F0031u,
    0x004F0022u,
    0x004F0024u,
    0x004F0026u,
    0x004F0027u,
    0x004F0029u,
    0x00500000u,
    0x00500001u,
    0x00500002u,
    0x00500016u,
    0x00500017u,
    0x00500018u,
    0x00500019u,
    0x0050001Au,
    0x0050001Bu,
    0x0050001Cu,
    0x0050001Du,
    0x0050001Eu,
    0x0050001Fu,
    0x00500020u,
    0x00500021u,
    0x00500008u,
    0x00500009u,
    0x0050000Au,
    0x0050000Bu,
    0x00510029u,
    0x0051002Au,
    0x0051002Bu,
    0x007D0000u,
    0x00510065u,
    0x00510066u,
    0x00510067u,
    0x00510027u,
    0x00510069u,
    0x00510047u,
    0x00510048u,
    0x00510049u,
    0x00510046u,
    0x0051000Au,
    0x0051000Cu,
    0x0051000Eu,
    0x00510010u,
    0x00510012u
};

struct DiagRequestEntry
{
    DWORD valid;
    DWORD request_id;
    DWORD editor_id;
    DWORD polls;
    DWORD last_result;
};

static DiagRequestEntry g_diag_requests[1024];
static DWORD g_diag_request_next = 0;

static BOOL
is_dub_editor(DWORD editor_id)
{
    for (DWORD i = 0; i < 408u; ++i) {
        if (g_diag_editor_ids[i] == editor_id)
            return TRUE;
    }

    return 0;
}

static void
diag_track_request(
    DWORD request_id,
    DWORD editor_id)
{
    for (DWORD i = 0; i < 1024u; ++i) {
        if (
            g_diag_requests[i].valid &&
            g_diag_requests[i].request_id == request_id
        ) {
            g_diag_requests[i].editor_id = editor_id;
            g_diag_requests[i].polls = 0;
            g_diag_requests[i].last_result = 0xFFFFFFFFu;
            return;
        }
    }

    DiagRequestEntry* e =
        &g_diag_requests[g_diag_request_next];

    e->valid = 1;
    e->request_id = request_id;
    e->editor_id = editor_id;
    e->polls = 0;
    e->last_result = 0xFFFFFFFFu;

    ++g_diag_request_next;

    if (g_diag_request_next >= 1024u)
        g_diag_request_next = 0;
}

static DiagRequestEntry*
diag_request_entry(DWORD request_id)
{
    for (DWORD i = 0; i < 1024u; ++i) {
        if (
            g_diag_requests[i].valid &&
            g_diag_requests[i].request_id == request_id
        )
            return &g_diag_requests[i];
    }

    return (DiagRequestEntry*)NULLPTR;
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

static void write_line(
    const char* label,
    const DWORD* values,
    DWORD count)
{
    HANDLE file = CreateFileA(
        "snd-dare-play-diag-v11.log",
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

static void install_dare_play_hook();

extern "C"
__declspec(noinline)
DWORD __stdcall probe_get_handle(DWORD editor_id)
    __asm__("_probe_get_handle@4");

extern "C"
__declspec(noinline)
DWORD __stdcall probe_get_handle(DWORD editor_id) {
    install_dare_play_hook();
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

    BOOL diag_target =
        is_dub_editor(editor_id);

    if (diag_target) {
        DWORD values[6] = {
            editor_id,
            a1,
            a2,
            a3,
            a4,
            GetTickCount()
        };

        write_line(
            "diag_send",
            values,
            6);
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

    if (diag_target) {
        DWORD values[4] = {
            editor_id,
            (DWORD)result,
            GetTickCount(),
            a2
        };

        write_line(
            "diag_return",
            values,
            4);

        if (result != -1)
            diag_track_request(
                (DWORD)result,
                editor_id);
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

    DiagRequestEntry* entry =
        diag_request_entry(request_id);

    if (entry) {
        DWORD state = result ? 1u : 0u;

        // Avoid flooding the log:
        // first two polls + every state transition.
        if (
            entry->polls < 2u ||
            entry->last_result != state
        ) {
            DWORD values[5] = {
                entry->editor_id,
                request_id,
                state,
                entry->polls,
                GetTickCount()
            };

            write_line(
                "diag_is_playing",
                values,
                5);
        }

        ++entry->polls;
        entry->last_result = state;
    }

    return result;
}


typedef BOOL (__thiscall *DarePlaySoundW)(
    void*,
    void*,
    void*,
    unsigned char);

static DarePlaySoundW g_dare_play_original = 0;
static DWORD g_dare_hook_installed = 0;

static BOOL __fastcall
dare_play_hook(
    void* self,
    void*,
    void* actor,
    void* sound,
    unsigned char sound_type)
{
    DWORD editor_id = 0xFFFFFFFFu;
    DWORD event_handle = 0u;

    if (sound) {
        editor_id =
            *(DWORD*)((char*)sound + 0x30);

        event_handle =
            *(DWORD*)((char*)sound + 0x34);
    }

    if (is_dub_editor(editor_id)) {
        DWORD values[6] = {
            editor_id,
            (DWORD)actor,
            (DWORD)sound,
            event_handle,
            (DWORD)sound_type,
            GetTickCount()
        };

        write_line(
            "dare_play",
            values,
            6);
    }

    BOOL result = g_dare_play_original
        ? g_dare_play_original(
            self,
            actor,
            sound,
            sound_type)
        : 0;

    if (is_dub_editor(editor_id)) {
        DWORD values[3] = {
            editor_id,
            (DWORD)result,
            GetTickCount()
        };

        write_line(
            "dare_play_ret",
            values,
            3);
    }

    return result;
}

static void
install_dare_play_hook()
{
    if (g_dare_hook_installed)
        return;

    HMODULE dare =
        LoadLibraryA("DareAudio.dll");

    if (!dare) {
        DWORD zero = 0;
        write_line(
            "dare_hook_no_module",
            &zero,
            1);
        return;
    }

    // DareAudio image base + vtable RVA 0x9240
    // PlaySoundW slot = +0x7C
    DWORD* slot =
        (DWORD*)(
            (char*)dare +
            0x9240u +
            0x7Cu);

    DWORD original = *slot;

    typedef BOOL (__stdcall *VirtualProtectFn)(
        void*,
        DWORD,
        DWORD,
        DWORD*);

    HMODULE kernel =
        LoadLibraryA("kernel32.dll");

    VirtualProtectFn virtual_protect =
        kernel
        ? (VirtualProtectFn)GetProcAddress(
            kernel,
            "VirtualProtect")
        : 0;

    if (!virtual_protect) {
        DWORD values[2] = {
            (DWORD)dare,
            original
        };

        write_line(
            "dare_hook_no_vprotect",
            values,
            2);
        return;
    }

    DWORD old_protect = 0;

    if (!virtual_protect(
            slot,
            4u,
            0x40u, // PAGE_EXECUTE_READWRITE
            &old_protect)) {
        DWORD values[2] = {
            (DWORD)slot,
            original
        };

        write_line(
            "dare_hook_vprotect_failed",
            values,
            2);
        return;
    }

    g_dare_play_original =
        (DarePlaySoundW)original;

    *slot = (DWORD)&dare_play_hook;

    DWORD ignored = 0;

    virtual_protect(
        slot,
        4u,
        old_protect,
        &ignored);

    g_dare_hook_installed = 1;

    DWORD values[4] = {
        (DWORD)dare,
        (DWORD)slot,
        original,
        (DWORD)&dare_play_hook
    };

    write_line(
        "dare_hook_installed",
        values,
        4);
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
