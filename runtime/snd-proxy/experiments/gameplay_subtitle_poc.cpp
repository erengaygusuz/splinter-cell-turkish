// Splinter Cell gameplay subtitle proof of concept.
//
// This DLL proxies SNDDSound3DDLL_VBR.dll.  All exports except the two below
// are forwarded by the generated .def file.  The hooks preserve the original
// calls and only observe the editor-id -> runtime-handle relationship.

extern "C" {

typedef void* HANDLE;
typedef void* HINSTANCE;
typedef void* HMODULE;
typedef void* HWND;
typedef void* HDC;
typedef void* HGDIOBJ;
typedef void* HFONT;
typedef void* HBRUSH;
typedef void* HMENU;
typedef const char* LPCSTR;
typedef const wchar_t* LPCWSTR;
typedef unsigned long DWORD;
typedef long LONG;
typedef unsigned int UINT;
typedef unsigned long ULONG_PTR;
typedef ULONG_PTR WPARAM;
typedef long LPARAM;
typedef long LRESULT;
typedef int BOOL;
typedef unsigned short ATOM;
typedef void* LPVOID;

#define WINAPI __stdcall
#define CALLBACK __stdcall
#define TRUE 1
#define FALSE 0
#define NULLPTR ((void*)0)

struct RECT { LONG left, top, right, bottom; };
struct POINT { LONG x, y; };
struct MSG {
    HWND hwnd;
    UINT message;
    WPARAM wParam;
    LPARAM lParam;
    DWORD time;
    POINT pt;
};
struct PAINTSTRUCT {
    HDC hdc;
    BOOL fErase;
    RECT rcPaint;
    BOOL fRestore;
    BOOL fIncUpdate;
    unsigned char rgbReserved[32];
};
typedef LRESULT (CALLBACK *WNDPROC)(HWND, UINT, WPARAM, LPARAM);
struct WNDCLASSW {
    UINT style;
    WNDPROC lpfnWndProc;
    int cbClsExtra;
    int cbWndExtra;
    HINSTANCE hInstance;
    void* hIcon;
    void* hCursor;
    HBRUSH hbrBackground;
    LPCWSTR lpszMenuName;
    LPCWSTR lpszClassName;
};

__declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
__declspec(dllimport) HMODULE WINAPI GetModuleHandleW(LPCWSTR);
__declspec(dllimport) void* WINAPI GetProcAddress(HMODULE, LPCSTR);
__declspec(dllimport) BOOL WINAPI DisableThreadLibraryCalls(HMODULE);
__declspec(dllimport) HANDLE WINAPI CreateThread(void*, ULONG_PTR, DWORD (WINAPI*)(LPVOID), LPVOID, DWORD, DWORD*);
__declspec(dllimport) DWORD WINAPI GetTickCount(void);
__declspec(dllimport) void WINAPI Sleep(DWORD);
__declspec(dllimport) DWORD WINAPI GetCurrentProcessId(void);
__declspec(dllimport) HANDLE WINAPI CreateFileA(LPCSTR, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI WriteFile(HANDLE, const void*, DWORD, DWORD*, void*);
__declspec(dllimport) DWORD WINAPI SetFilePointer(HANDLE, LONG, LONG*, DWORD);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);

__declspec(dllimport) ATOM WINAPI RegisterClassW(const WNDCLASSW*);
__declspec(dllimport) HWND WINAPI CreateWindowExW(DWORD, LPCWSTR, LPCWSTR, DWORD, int, int, int, int, HWND, HMENU, HINSTANCE, LPVOID);
__declspec(dllimport) LRESULT WINAPI DefWindowProcW(HWND, UINT, WPARAM, LPARAM);
__declspec(dllimport) BOOL WINAPI GetMessageW(MSG*, HWND, UINT, UINT);
__declspec(dllimport) BOOL WINAPI TranslateMessage(const MSG*);
__declspec(dllimport) LRESULT WINAPI DispatchMessageW(const MSG*);
__declspec(dllimport) HWND WINAPI FindWindowW(LPCWSTR, LPCWSTR);
__declspec(dllimport) HWND WINAPI GetForegroundWindow(void);
__declspec(dllimport) DWORD WINAPI GetWindowThreadProcessId(HWND, DWORD*);
__declspec(dllimport) BOOL WINAPI GetWindowRect(HWND, RECT*);
__declspec(dllimport) BOOL WINAPI GetClientRect(HWND, RECT*);
__declspec(dllimport) BOOL WINAPI SetWindowPos(HWND, HWND, int, int, int, int, UINT);
__declspec(dllimport) BOOL WINAPI ShowWindow(HWND, int);
__declspec(dllimport) BOOL WINAPI SetLayeredWindowAttributes(HWND, DWORD, unsigned char, DWORD);
__declspec(dllimport) ULONG_PTR WINAPI SetTimer(HWND, ULONG_PTR, UINT, void*);
__declspec(dllimport) BOOL WINAPI InvalidateRect(HWND, const RECT*, BOOL);
__declspec(dllimport) HDC WINAPI BeginPaint(HWND, PAINTSTRUCT*);
__declspec(dllimport) BOOL WINAPI EndPaint(HWND, const PAINTSTRUCT*);
__declspec(dllimport) int WINAPI FillRect(HDC, const RECT*, HBRUSH);
__declspec(dllimport) int WINAPI DrawTextW(HDC, LPCWSTR, int, RECT*, UINT);
__declspec(dllimport) int WINAPI SetBkMode(HDC, int);
__declspec(dllimport) DWORD WINAPI SetTextColor(HDC, DWORD);
__declspec(dllimport) BOOL WINAPI PostMessageW(HWND, UINT, WPARAM, LPARAM);
__declspec(dllimport) HDC WINAPI GetDC(HWND);
__declspec(dllimport) int WINAPI ReleaseDC(HWND, HDC);

__declspec(dllimport) HBRUSH WINAPI CreateSolidBrush(DWORD);
__declspec(dllimport) HFONT WINAPI CreateFontW(int, int, int, int, int, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, LPCWSTR);
__declspec(dllimport) HGDIOBJ WINAPI SelectObject(HDC, HGDIOBJ);
__declspec(dllimport) BOOL WINAPI DeleteObject(HGDIOBJ);

}

static const wchar_t kWindowClass[] = L"SCGameplaySubtitlePoc";

struct SubtitleEntry {
    DWORD editor_id;
    DWORD duration_ms;
    DWORD handle;
    const wchar_t* text;
};

// The first face-to-face Lambert/Fisher exchange before the training course.
static SubtitleEntry g_subtitles[] = {
    {0x003c0000u, 3400u, 0u,
        L"LAMBERT: Sam Fisher.\nBenden önce gelmene inanamıyorum."},
    {0x003c0001u, 2400u, 0u,
        L"FISHER: Erken gelmeyi severim.\nMerhaba Albay."},
    {0x003c0002u, 2200u, 0u,
        L"LAMBERT: Adımı kullanabilirsin.\nOda güvenli."},
    {0x003c0003u, 1100u, 0u,
        L"FISHER: Lambert."},
    {0x003c0004u, 4200u, 0u,
        L"LAMBERT: Seni tekrar görmek güzel.\nNSA eğitimi nasıl gidiyor?"},
};
static const DWORD kSubtitleCount = sizeof(g_subtitles) / sizeof(g_subtitles[0]);

static HINSTANCE g_instance = (HINSTANCE)NULLPTR;
static HWND g_overlay = (HWND)NULLPTR;
static HWND g_game_parent = (HWND)NULLPTR;
static volatile DWORD g_expires_at = 0;
static volatile LONG g_thread_started = 0;
static volatile LONG g_fallback_started = 0;
static HMODULE g_original = (HMODULE)NULLPTR;
static const wchar_t* volatile g_active_text = g_subtitles[0].text;

static DWORD rgb(unsigned char r, unsigned char g, unsigned char b) {
    return ((DWORD)r) | ((DWORD)g << 8) | ((DWORD)b << 16);
}

static DWORD text_length(const char* text) {
    DWORD length = 0;
    while (text[length]) ++length;
    return length;
}

static void append_hex(char* output, DWORD* offset, DWORD value) {
    static const char digits[] = "0123456789ABCDEF";
    for (int shift = 28; shift >= 0; shift -= 4) {
        output[(*offset)++] = digits[(value >> shift) & 15u];
    }
}

static void write_log_pair(const char* label, DWORD first, DWORD second) {
    HANDLE file = CreateFileA("gameplay-subtitle-poc.log", 0x40000000u,
        0x00000001u | 0x00000002u, (void*)NULLPTR, 4u, 0x00000080u,
        (HANDLE)NULLPTR);
    if (file == (HANDLE)(LONG)-1) return;
    SetFilePointer(file, 0, (LONG*)NULLPTR, 2u); // FILE_END
    char line[96];
    DWORD at = 0;
    for (DWORD i = 0; label[i]; ++i) line[at++] = label[i];
    line[at++] = ' ';
    append_hex(line, &at, first);
    line[at++] = ' ';
    append_hex(line, &at, second);
    line[at++] = '\r';
    line[at++] = '\n';
    DWORD written = 0;
    WriteFile(file, line, at, &written, (void*)NULLPTR);
    CloseHandle(file);
}

static HMODULE original_module() {
    if (!g_original) {
        g_original = LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");
    }
    return g_original;
}

static HWND game_window() {
    HWND window = FindWindowW((LPCWSTR)NULLPTR, L"Tom Clancy's Splinter Cell");
    if (window) return window;
    window = GetForegroundWindow();
    DWORD process_id = 0;
    if (window) GetWindowThreadProcessId(window, &process_id);
    return process_id == GetCurrentProcessId() ? window : (HWND)NULLPTR;
}

static void position_overlay(HWND overlay) {
    HWND game = g_game_parent ? g_game_parent : game_window();
    RECT bounds;
    if (!game || !GetClientRect(game, &bounds)) return;
    int width = (int)(bounds.right - bounds.left);
    int height = (int)(bounds.bottom - bounds.top);
    // A child overlay stays inside the game and cannot minimize/deactivate it.
    SetWindowPos(overlay, (HWND)NULLPTR, 0, 0, width, height,
        0x0010u | 0x0040u);
}

static void draw_subtitle_text(HDC dc, const RECT* source) {
    RECT client = *source;
    int height = (int)(client.bottom - client.top);
    int font_height = height / 30;
    if (font_height < 24) font_height = 24;
    if (font_height > 38) font_height = 38;
    HFONT font = CreateFontW(-font_height, 0, 0, 0, 700, FALSE, FALSE,
        FALSE, 1u, 0u, 0u, 5u, 0u, L"Tahoma");
    HGDIOBJ old_font = SelectObject(dc, font);
    SetBkMode(dc, 1);

    RECT text_rect = client;
    int width = (int)(client.right - client.left);
    text_rect.left += width / 12;
    text_rect.right -= width / 12;
    text_rect.top = client.top + (height * 62 / 100);
    text_rect.bottom = client.top + (height * 82 / 100);
    const UINT format = 0x00000001u | 0x00000010u | 0x00000800u;
    SetTextColor(dc, rgb(0, 0, 0));
    const int offsets[8][2] = {
        {-2, 0}, {2, 0}, {0, -2}, {0, 2},
        {-2, -2}, {2, -2}, {-2, 2}, {2, 2}
    };
    for (int i = 0; i < 8; ++i) {
        RECT outline = text_rect;
        outline.left += offsets[i][0]; outline.right += offsets[i][0];
        outline.top += offsets[i][1]; outline.bottom += offsets[i][1];
        DrawTextW(dc, g_active_text, -1, &outline, format);
    }
    SetTextColor(dc, rgb(255, 255, 255));
    DrawTextW(dc, g_active_text, -1, &text_rect, format);
    SelectObject(dc, old_font);
    DeleteObject(font);
}

static LRESULT CALLBACK overlay_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    (void)wparam;
    (void)lparam;
    if (message == 0x000Fu) { // WM_PAINT
        PAINTSTRUCT paint;
        HDC dc = BeginPaint(window, &paint);
        RECT client;
        GetClientRect(window, &client);
        HBRUSH transparent_key = CreateSolidBrush(rgb(255, 0, 255));
        FillRect(dc, &client, transparent_key);
        DeleteObject(transparent_key);

        draw_subtitle_text(dc, &client);
        EndPaint(window, &paint);
        return 0;
    }
    if (message == 0x0113u) { // WM_TIMER
        position_overlay(window);
        DWORD expires = g_expires_at;
        if (expires && (LONG)(GetTickCount() - expires) >= 0) {
            g_expires_at = 0;
            ShowWindow(window, 0);
        } else if (expires) {
            ShowWindow(window, 4);
            InvalidateRect(window, (const RECT*)NULLPTR, TRUE);
            // Also paint directly onto the game client.  This avoids the
            // Direct3D surface covering a conventional child window.
            RECT game_client;
            if (g_game_parent && GetClientRect(g_game_parent, &game_client)) {
                HDC game_dc = GetDC(g_game_parent);
                if (game_dc) {
                    draw_subtitle_text(game_dc, &game_client);
                    ReleaseDC(g_game_parent, game_dc);
                }
            }
        }
        return 0;
    }
    if (message == 0x8001u) { // WM_APP + 1
        position_overlay(window);
        ShowWindow(window, 4);
        InvalidateRect(window, (const RECT*)NULLPTR, TRUE);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

static DWORD WINAPI overlay_thread(LPVOID) {
    g_game_parent = game_window();
    if (!g_game_parent) {
        write_log_pair("game_window_not_found", 0, 0);
        return 0;
    }
    WNDCLASSW wc;
    wc.style = 0;
    wc.lpfnWndProc = overlay_proc;
    wc.cbClsExtra = 0;
    wc.cbWndExtra = 0;
    wc.hInstance = g_instance;
    wc.hIcon = NULLPTR;
    wc.hCursor = NULLPTR;
    wc.hbrBackground = (HBRUSH)NULLPTR;
    wc.lpszMenuName = (LPCWSTR)NULLPTR;
    wc.lpszClassName = kWindowClass;
    RegisterClassW(&wc);

    g_overlay = CreateWindowExW(
        0x00080000u | 0x00000020u | 0x08000000u,
        kWindowClass, L"", 0x40000000u, 0, 0, 1, 1,
        g_game_parent, (HMENU)NULLPTR, g_instance, NULLPTR);
    if (!g_overlay) {
        write_log_pair("overlay_create_failed", 0, 0);
        return 0;
    }
    write_log_pair("overlay_ready", 1, 0);
    SetLayeredWindowAttributes(g_overlay, rgb(255, 0, 255), 255, 1u);
    SetTimer(g_overlay, 1u, 100u, NULLPTR);
    if (g_expires_at) PostMessageW(g_overlay, 0x8001u, 0, 0);

    MSG message;
    while (GetMessageW(&message, (HWND)NULLPTR, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    return 0;
}

static void trigger_subtitle(const SubtitleEntry* subtitle) {
    g_active_text = subtitle->text;
    g_expires_at = GetTickCount() + subtitle->duration_ms;
    if (!g_thread_started) {
        g_thread_started = 1;
        DWORD thread_id = 0;
        HANDLE thread = CreateThread(NULLPTR, 0, overlay_thread, NULLPTR, 0, &thread_id);
        if (thread) CloseHandle(thread);
    }
    if (g_overlay) PostMessageW(g_overlay, 0x8001u, 0, 0);
}

static DWORD WINAPI fallback_first_line(LPVOID) {
    Sleep(1500u);
    g_subtitles[0].duration_ms = 8000u;
    write_log_pair("fallback_trigger", g_subtitles[0].editor_id,
        g_subtitles[0].handle);
    trigger_subtitle(&g_subtitles[0]);
    return 0;
}

static void observe_play(DWORD a1, DWORD a2, DWORD a3, DWORD a4,
    DWORD a5, DWORD a6, DWORD a7) {
    const DWORD arguments[7] = {a1, a2, a3, a4, a5, a6, a7};
    for (DWORD i = 0; i < kSubtitleCount; ++i) {
        if (!g_subtitles[i].handle) continue;
        for (DWORD argument = 0; argument < 7; ++argument) {
            if (arguments[argument] == g_subtitles[i].handle) {
                write_log_pair("target_play", g_subtitles[i].editor_id,
                    g_subtitles[i].handle);
                trigger_subtitle(&g_subtitles[i]);
                return;
            }
        }
    }
}

extern "C" __declspec(noinline) DWORD __stdcall poc_get_handle(DWORD editor_id)
    __asm__("_poc_get_handle@4");
extern "C" __declspec(noinline) DWORD __stdcall poc_get_handle(DWORD editor_id) {
    typedef DWORD (__stdcall *Original)(DWORD);
    Original original = (Original)GetProcAddress(original_module(),
        "_SND_fn_hGetSoundEventHandleFromEditorId@4");
    DWORD handle = original ? original(editor_id) : 0;
    for (DWORD i = 0; i < kSubtitleCount; ++i) {
        if (g_subtitles[i].editor_id == editor_id) {
            g_subtitles[i].handle = handle;
            write_log_pair("target_map", editor_id, handle);
            if (i == 0 && !g_fallback_started) {
                g_fallback_started = 1;
                DWORD thread_id = 0;
                HANDLE thread = CreateThread(NULLPTR, 0, fallback_first_line,
                    NULLPTR, 0, &thread_id);
                if (thread) CloseHandle(thread);
            }
            break;
        }
    }
    return handle;
}

extern "C" __declspec(noinline) LONG __cdecl poc_send_request(
    DWORD first, DWORD second, DWORD event_handle, DWORD fourth)
    __asm__("_poc_send_request");
extern "C" __declspec(noinline) LONG __cdecl poc_send_request(
    DWORD first, DWORD second, DWORD event_handle, DWORD fourth) {
    typedef LONG (__cdecl *Original)(DWORD, DWORD, DWORD, DWORD);
    Original original = (Original)GetProcAddress(original_module(),
        "SND_fn_lSendSoundRequest");
    LONG result = original ? original(first, second, event_handle, fourth) : -1;
    observe_play(first, second, event_handle, fourth, 0, 0, 0);
    return result;
}

extern "C" __declspec(noinline) LONG __cdecl poc_send_on_channel(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5)
    __asm__("_poc_send_on_channel");
extern "C" __declspec(noinline) LONG __cdecl poc_send_on_channel(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5) {
    typedef LONG (__cdecl *Original)(DWORD, DWORD, DWORD, DWORD, DWORD);
    Original original = (Original)GetProcAddress(original_module(),
        "SND_fn_lSendSoundRequestOnChannel");
    LONG result = original ? original(a1, a2, a3, a4, a5) : -1;
    observe_play(a1, a2, a3, a4, a5, 0, 0);
    return result;
}

extern "C" __declspec(noinline) LONG __cdecl poc_send_on_channel_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5, DWORD a6, DWORD a7)
    __asm__("_poc_send_on_channel_fade");
extern "C" __declspec(noinline) LONG __cdecl poc_send_on_channel_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5, DWORD a6, DWORD a7) {
    typedef LONG (__cdecl *Original)(DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD);
    Original original = (Original)GetProcAddress(original_module(),
        "SND_fn_lSendSoundRequestOnChannelWithFadeIn");
    LONG result = original ? original(a1, a2, a3, a4, a5, a6, a7) : -1;
    observe_play(a1, a2, a3, a4, a5, a6, a7);
    return result;
}

extern "C" __declspec(noinline) LONG __cdecl poc_send_with_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5, DWORD a6)
    __asm__("_poc_send_with_fade");
extern "C" __declspec(noinline) LONG __cdecl poc_send_with_fade(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4, DWORD a5, DWORD a6) {
    typedef LONG (__cdecl *Original)(DWORD, DWORD, DWORD, DWORD, DWORD, DWORD);
    Original original = (Original)GetProcAddress(original_module(),
        "SND_fn_lSendSoundRequestWithFadeIn");
    LONG result = original ? original(a1, a2, a3, a4, a5, a6) : -1;
    observe_play(a1, a2, a3, a4, a5, a6, 0);
    return result;
}

extern "C" BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == 1u) {
        g_instance = instance;
        DisableThreadLibraryCalls(instance);
    }
    return TRUE;
}
