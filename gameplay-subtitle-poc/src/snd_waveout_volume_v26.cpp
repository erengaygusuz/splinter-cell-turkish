typedef unsigned long DWORD;
typedef long LONG;
typedef int BOOL;
typedef void* HANDLE;
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD_PTR;
typedef unsigned long MMRESULT;
typedef void* HWAVEOUT;

#define WINAPI __stdcall
#define INVALID_HANDLE_VALUE ((HANDLE)(LONG)-1)

extern "C" __declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
extern "C" __declspec(dllimport) void* WINAPI GetProcAddress(HMODULE, LPCSTR);
extern "C" __declspec(dllimport) DWORD WINAPI GetTickCount();
extern "C" __declspec(dllimport) HANDLE WINAPI CreateFileA(
    LPCSTR, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
extern "C" __declspec(dllimport) DWORD WINAPI SetFilePointer(
    HANDLE, LONG, LONG*, DWORD);
extern "C" __declspec(dllimport) BOOL WINAPI WriteFile(
    HANDLE, const void*, DWORD, DWORD*, void*);
extern "C" __declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);

struct SCWaveHeader
{
    char* data;
    DWORD buffer_length;
    DWORD bytes_recorded;
    DWORD_PTR user;
    DWORD flags;
    DWORD loops;
    SCWaveHeader* next;
    DWORD_PTR reserved;
};

struct ExternalVoiceSlot
{
    DWORD active;
    DWORD editor_id;
    DWORD request_id;
    DWORD paused;
    DWORD pause_started;
    DWORD expected_end;
    HWAVEOUT wave;
    void* file_memory;
    SCWaveHeader header;
};

typedef char V26AssertVoiceSlotSize[
    sizeof(ExternalVoiceSlot) == 64 ? 1 : -1
];

extern "C" {
extern ExternalVoiceSlot g_voice_slots[8]
    __asm__("_g_voice_slots");

LONG __cdecl probe_send_request(
    DWORD, DWORD, DWORD, DWORD)
    __asm__("_probe_send_request");
}

typedef MMRESULT (WINAPI *WaveOutSetVolumeFn)(
    HWAVEOUT, DWORD);

static HMODULE g_v26_original = 0;
static WaveOutSetVolumeFn g_v26_wave_out_set_volume = 0;

static DWORD g_v26_volume_seen = 0u;
static DWORD g_v26_volume_qdb = 0u;
static DWORD g_v26_volume_word = 0xFFFFFFFFu;

static const unsigned short g_v26_gain_table[384] = {
    65535u, 63676u, 61869u, 60114u, 58408u, 56751u, 55141u, 53576u, 52056u, 50579u, 49144u, 47750u,
    46395u, 45079u, 43800u, 42557u, 41350u, 40177u, 39037u, 37929u, 36853u, 35807u, 34792u, 33804u,
    32845u, 31913u, 31008u, 30128u, 29273u, 28443u, 27636u, 26852u, 26090u, 25350u, 24631u, 23932u,
    23253u, 22593u, 21952u, 21329u, 20724u, 20136u, 19565u, 19010u, 18470u, 17946u, 17437u, 16942u,
    16462u, 15995u, 15541u, 15100u, 14671u, 14255u, 13851u, 13458u, 13076u, 12705u, 12344u, 11994u,
    11654u, 11323u, 11002u, 10690u, 10387u, 10092u, 9806u, 9527u, 9257u, 8994u, 8739u, 8491u,
    8250u, 8016u, 7789u, 7568u, 7353u, 7145u, 6942u, 6745u, 6554u, 6368u, 6187u, 6011u,
    5841u, 5675u, 5514u, 5358u, 5206u, 5058u, 4914u, 4775u, 4640u, 4508u, 4380u, 4256u,
    4135u, 4018u, 3904u, 3793u, 3685u, 3581u, 3479u, 3380u, 3285u, 3191u, 3101u, 3013u,
    2927u, 2844u, 2764u, 2685u, 2609u, 2535u, 2463u, 2393u, 2325u, 2259u, 2195u, 2133u,
    2072u, 2014u, 1956u, 1901u, 1847u, 1795u, 1744u, 1694u, 1646u, 1599u, 1554u, 1510u,
    1467u, 1426u, 1385u, 1346u, 1308u, 1270u, 1234u, 1199u, 1165u, 1132u, 1100u, 1069u,
    1039u, 1009u, 981u, 953u, 926u, 899u, 874u, 849u, 825u, 802u, 779u, 757u,
    735u, 714u, 694u, 674u, 655u, 637u, 619u, 601u, 584u, 568u, 551u, 536u,
    521u, 506u, 491u, 477u, 464u, 451u, 438u, 426u, 413u, 402u, 390u, 379u,
    369u, 358u, 348u, 338u, 328u, 319u, 310u, 301u, 293u, 284u, 276u, 269u,
    261u, 253u, 246u, 239u, 233u, 226u, 220u, 213u, 207u, 201u, 196u, 190u,
    185u, 179u, 174u, 169u, 165u, 160u, 155u, 151u, 147u, 143u, 139u, 135u,
    131u, 127u, 123u, 120u, 117u, 113u, 110u, 107u, 104u, 101u, 98u, 95u,
    93u, 90u, 87u, 85u, 83u, 80u, 78u, 76u, 74u, 71u, 69u, 67u,
    66u, 64u, 62u, 60u, 58u, 57u, 55u, 54u, 52u, 51u, 49u, 48u,
    46u, 45u, 44u, 43u, 41u, 40u, 39u, 38u, 37u, 36u, 35u, 34u,
    33u, 32u, 31u, 30u, 29u, 28u, 28u, 27u, 26u, 25u, 25u, 24u,
    23u, 23u, 22u, 21u, 21u, 20u, 20u, 19u, 18u, 18u, 17u, 17u,
    16u, 16u, 16u, 15u, 15u, 14u, 14u, 13u, 13u, 13u, 12u, 12u,
    12u, 11u, 11u, 11u, 10u, 10u, 10u, 10u, 9u, 9u, 9u, 8u,
    8u, 8u, 8u, 8u, 7u, 7u, 7u, 7u, 7u, 6u, 6u, 6u,
    6u, 6u, 6u, 5u, 5u, 5u, 5u, 5u, 5u, 5u, 4u, 4u,
    4u, 4u, 4u, 4u, 4u, 4u, 3u, 3u, 3u, 3u, 3u, 3u,
    3u, 3u, 3u, 3u, 3u, 3u, 2u, 2u, 2u, 2u, 2u, 2u,
    2u, 2u, 2u, 2u, 2u, 2u, 2u, 2u, 2u, 2u, 2u, 2u,
    1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u,
};

static HMODULE
v26_original_module()
{
    if (!g_v26_original)
        g_v26_original =
            LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");

    return g_v26_original;
}

static WaveOutSetVolumeFn
v26_wave_out_set_volume()
{
    if (g_v26_wave_out_set_volume)
        return g_v26_wave_out_set_volume;

    HMODULE winmm = LoadLibraryA("winmm.dll");

    if (!winmm)
        return 0;

    g_v26_wave_out_set_volume =
        (WaveOutSetVolumeFn)GetProcAddress(
            winmm,
            "waveOutSetVolume");

    return g_v26_wave_out_set_volume;
}

static char
v26_hex_digit(DWORD value)
{
    value &= 0xFu;

    return value < 10u
        ? (char)('0' + value)
        : (char)('A' + value - 10u);
}

static void
v26_hex8(char* out, DWORD value)
{
    for (DWORD i = 0u; i < 8u; ++i) {
        DWORD shift = 28u - (i * 4u);
        out[i] = v26_hex_digit(value >> shift);
    }
}

static void
v26_log(
    const char* label,
    DWORD label_len,
    const DWORD* values,
    DWORD count)
{
    HANDLE file = CreateFileA(
        "snd-waveout-volume-v26.log",
        0x40000000u,
        0x00000003u,
        0,
        4u,
        0x00000080u,
        0);

    if (file == INVALID_HANDLE_VALUE)
        return;

    SetFilePointer(file, 0, 0, 2u);

    char line[192];
    DWORD pos = 0u;

    for (
        DWORD i = 0u;
        i < label_len && pos < 180u;
        ++i
    ) {
        line[pos++] = label[i];
    }

    for (
        DWORD i = 0u;
        i < count && pos + 9u < 180u;
        ++i
    ) {
        line[pos++] = ' ';
        v26_hex8(line + pos, values[i]);
        pos += 8u;
    }

    line[pos++] = '\r';
    line[pos++] = '\n';

    DWORD written = 0u;
    WriteFile(file, line, pos, &written, 0);
    CloseHandle(file);
}

static BOOL
v26_db_bits_to_qdb(
    DWORD raw_bits,
    DWORD* out_qdb)
{
    if (!out_qdb)
        return 0;

    DWORD magnitude =
        raw_bits & 0x7FFFFFFFu;

    DWORD exponent =
        (magnitude >> 23u) & 0xFFu;

    if (exponent == 0xFFu)
        return 0;

    // Positive/zero volume values mean no attenuation for the
    // speech-volume bridge. The observed game speech line is <= 0 dB.
    if (
        !(raw_bits & 0x80000000u) ||
        magnitude == 0u
    ) {
        *out_qdb = 0u;
        return 1;
    }

    if (exponent == 0u) {
        *out_qdb = 0u;
        return 1;
    }

    LONG e =
        (LONG)exponent - 127;

    DWORD significand =
        0x00800000u |
        (magnitude & 0x007FFFFFu);

    // qdb = round(abs(dB) * 4).
    // float magnitude = significand * 2^(e - 23).
    // Therefore qdb = significand * 2^(e - 21).
    if (e >= 9) {
        *out_qdb = 384u;
        return 1;
    }

    LONG shift =
        21 - e;

    DWORD qdb = 0u;

    if (shift <= 0) {
        if (-shift >= 9)
            qdb = 384u;
        else
            qdb = significand << (DWORD)(-shift);
    }
    else if (shift >= 32) {
        qdb = 0u;
    }
    else {
        DWORD round =
            1u << (DWORD)(shift - 1);

        qdb =
            (significand + round) >>
            (DWORD)shift;
    }

    if (qdb > 384u)
        qdb = 384u;

    *out_qdb = qdb;
    return 1;
}

static DWORD
v26_volume_word_from_qdb(DWORD qdb)
{
    if (qdb >= 384u)
        return 0u;

    DWORD mono =
        (DWORD)g_v26_gain_table[qdb];

    return
        mono |
        (mono << 16u);
}

static void
v26_apply_volume(
    DWORD* active_out,
    DWORD* applied_out,
    DWORD* failures_out)
{
    DWORD active = 0u;
    DWORD applied = 0u;
    DWORD failures = 0u;

    WaveOutSetVolumeFn set_volume =
        v26_wave_out_set_volume();

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            !slot->active ||
            !slot->wave
        )
            continue;

        ++active;

        if (!set_volume) {
            ++failures;
            continue;
        }

        MMRESULT result =
            set_volume(
                slot->wave,
                g_v26_volume_word);

        if (result == 0u)
            ++applied;
        else
            ++failures;
    }

    if (active_out)
        *active_out = active;

    if (applied_out)
        *applied_out = applied;

    if (failures_out)
        *failures_out = failures;
}

extern "C"
__declspec(noinline)
DWORD __cdecl v26_volume_route(
    DWORD ordinal,
    const DWORD* args)
    __asm__("_v26_volume_route");

extern "C"
__declspec(noinline)
DWORD __cdecl v26_volume_route(
    DWORD ordinal,
    const DWORD* args)
{
    HMODULE original =
        v26_original_module();

    void* target = original
        ? GetProcAddress(
            original,
            (LPCSTR)(DWORD_PTR)ordinal)
        : 0;

    if (
        ordinal == 240u &&
        args &&
        args[3] == 2u
    ) {
        DWORD qdb = 0u;

        if (
            v26_db_bits_to_qdb(
                args[1],
                &qdb) &&
            (
                !g_v26_volume_seen ||
                qdb != g_v26_volume_qdb
            )
        ) {
            g_v26_volume_seen = 1u;
            g_v26_volume_qdb = qdb;
            g_v26_volume_word =
                v26_volume_word_from_qdb(qdb);

            DWORD active = 0u;
            DWORD applied = 0u;
            DWORD failures = 0u;

            v26_apply_volume(
                &active,
                &applied,
                &failures);

            DWORD values[7] = {
                args[1],
                qdb,
                g_v26_volume_word,
                active,
                applied,
                failures,
                GetTickCount()
            };

            v26_log(
                "v26_speech_volume",
                17u,
                values,
                7u);
        }
    }

    return (DWORD)target;
}

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request_v26(
    DWORD a1,
    DWORD a2,
    DWORD a3,
    DWORD a4)
    __asm__("_probe_send_request_v26");

extern "C"
__declspec(noinline)
LONG __cdecl probe_send_request_v26(
    DWORD a1,
    DWORD a2,
    DWORD a3,
    DWORD a4)
{
    LONG result =
        probe_send_request(
            a1,
            a2,
            a3,
            a4);

    if (g_v26_volume_seen) {
        DWORD active = 0u;
        DWORD applied = 0u;
        DWORD failures = 0u;

        v26_apply_volume(
            &active,
            &applied,
            &failures);

        if (active) {
            DWORD values[6] = {
                (DWORD)result,
                g_v26_volume_qdb,
                g_v26_volume_word,
                active,
                applied,
                failures
            };

            v26_log(
                "v26_voice_apply",
                15u,
                values,
                6u);
        }
    }

    return result;
}
