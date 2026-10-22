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

struct TrainingOverride
{
    DWORD editor_id;
    DWORD duration_ms;
    DWORD duration_bits;
    const char* path;
};

static const TrainingOverride g_training_overrides[] =
{
    {0x00100001u, 3577u, 0x4064ED91u, "sc-tr-audio\\u000712.wav"}, // u000712
    {0x00100005u, 1255u, 0x3FA0A3D7u, "sc-tr-audio\\u000706.wav"}, // u000706
    {0x00100007u, 1616u, 0x3FCED917u, "sc-tr-audio\\u000708.wav"}, // u000708
    {0x00100008u, 1801u, 0x3FE6872Bu, "sc-tr-audio\\u000710.wav"}, // u000710
    {0x00100037u, 905u, 0x3F67AE14u, "sc-tr-audio\\u000717.wav"}, // u000717
    {0x00100039u, 1995u, 0x3FFF5C29u, "sc-tr-audio\\u000719.wav"}, // u000719
    {0x0010003Bu, 1058u, 0x3F876C8Bu, "sc-tr-audio\\u000721.wav"}, // u000721
    {0x0010003Du, 988u, 0x3F7CED91u, "sc-tr-audio\\u000723.wav"}, // u000723
    {0x0010003Fu, 2739u, 0x402F4BC7u, "sc-tr-audio\\u000714.wav"}, // u000714
    {0x00100040u, 1579u, 0x3FCA1CACu, "sc-tr-audio\\u000725.wav"}, // u000725
    {0x00100042u, 1532u, 0x3FC41893u, "sc-tr-audio\\u000727.wav"}, // u000727
    {0x003C0005u, 3056u, 0x40439581u, "sc-tr-audio\\u000047.wav"}, // u000047
    {0x003C0007u, 885u, 0x3F628F5Cu, "sc-tr-audio\\u000045.wav"}, // u000045
    {0x003C0009u, 2255u, 0x401051ECu, "sc-tr-audio\\u000043.wav"}, // u000043
    {0x003C000Bu, 2951u, 0x403CDD2Fu, "sc-tr-audio\\u000041.wav"}, // u000041
    {0x003C000Du, 1828u, 0x3FE9FBE7u, "sc-tr-audio\\u000039.wav"}, // u000039
    {0x003C0010u, 3881u, 0x4078624Eu, "sc-tr-audio\\u000036.wav"}, // u000036
    {0x003C0012u, 2222u, 0x400E353Fu, "sc-tr-audio\\u000034.wav"}, // u000034
    {0x003C0015u, 1045u, 0x3F85C28Fu, "sc-tr-audio\\u000031.wav"}, // u000031
    {0x003C0017u, 11693u, 0x413B1687u, "sc-tr-audio\\u000029.wav"}, // u000029
    {0x003C0018u, 1093u, 0x3F8BE76Du, "sc-tr-audio\\u000028.wav"}, // u000028
    {0x003C0019u, 6672u, 0x40D58106u, "sc-tr-audio\\u000027.wav"}, // u000027
    {0x003C001Au, 1619u, 0x3FCF3B64u, "sc-tr-audio\\u000026.wav"}, // u000026
    {0x003C001Bu, 3644u, 0x4069374Cu, "sc-tr-audio\\u000025.wav"}, // u000025
    {0x003C001Cu, 1674u, 0x3FD645A2u, "sc-tr-audio\\u000024.wav"}, // u000024
    {0x003C001Du, 4370u, 0x408BD70Au, "sc-tr-audio\\u000023.wav"}, // u000023
    {0x003C001Eu, 1369u, 0x3FAF3B64u, "sc-tr-audio\\u000022.wav"}, // u000022
    {0x003C001Fu, 6573u, 0x40D25604u, "sc-tr-audio\\u000021.wav"}, // u000021
    {0x003C0020u, 1828u, 0x3FE9FBE7u, "sc-tr-audio\\u000020.wav"}, // u000020
    {0x003C0021u, 4735u, 0x4097851Fu, "sc-tr-audio\\u000019.wav"}, // u000019
    {0x003C0022u, 3976u, 0x407E76C9u, "sc-tr-audio\\u000018.wav"}, // u000018
    {0x003C0025u, 3546u, 0x4062F1AAu, "sc-tr-audio\\u000017.wav"}, // u000017
    {0x003C0026u, 908u, 0x3F6872B0u, "sc-tr-audio\\u000016.wav"}, // u000016
    {0x003C0027u, 2028u, 0x4001CAC1u, "sc-tr-audio\\u000015.wav"}, // u000015
    {0x003C0028u, 2701u, 0x402CDD2Fu, "sc-tr-audio\\u000014.wav"}, // u000014
    {0x003C0029u, 3053u, 0x4043645Au, "sc-tr-audio\\u000013.wav"}, // u000013
    {0x003D0003u, 1492u, 0x3FBEF9DBu, "sc-tr-audio\\u000052.wav"}, // u000052
    {0x003D0005u, 2045u, 0x4002E148u, "sc-tr-audio\\u000054.wav"}, // u000054
    {0x003D0007u, 1761u, 0x3FE16873u, "sc-tr-audio\\u000056.wav"}, // u000056
    {0x003D0014u, 3764u, 0x4070E560u, "sc-tr-audio\\u000079.wav"}, // u000079
    {0x003D0015u, 836u, 0x3F560419u, "sc-tr-audio\\u000080.wav"}, // u000080
    {0x003D0017u, 3746u, 0x406FBE77u, "sc-tr-audio\\u000082.wav"}, // u000082
    {0x003D0018u, 1337u, 0x3FAB22D1u, "sc-tr-audio\\u000083.wav"}, // u000083
    {0x003D001Au, 7673u, 0x40F58937u, "sc-tr-audio\\u000085.wav"}, // u000085
    {0x003D001Bu, 898u, 0x3F65E354u, "sc-tr-audio\\u000086.wav"}, // u000086
    {0x003D001Du, 1833u, 0x3FEA9FBEu, "sc-tr-audio\\u000088.wav"}, // u000088
    {0x003D001Fu, 6792u, 0x40D95810u, "sc-tr-audio\\u000090.wav"}, // u000090
    {0x003D0020u, 833u, 0x3F553F7Du, "sc-tr-audio\\u000091.wav"}, // u000091
    {0x003D0021u, 7555u, 0x40F1C28Fu, "sc-tr-audio\\u000092.wav"}, // u000092
    {0x003F0009u, 1576u, 0x3FC9BA5Eu, "sc-tr-audio\\u000185.wav"}, // u000185
    {0x003F000Du, 1277u, 0x3FA374BCu, "sc-tr-audio\\u000191.wav"}, // u000191
    {0x003F000Fu, 1551u, 0x3FC6872Bu, "sc-tr-audio\\u000193.wav"}, // u000193
    {0x003F0011u, 978u, 0x3F7A5E35u, "sc-tr-audio\\u000195.wav"}, // u000195
    {0x003F0012u, 3173u, 0x404B126Fu, "sc-tr-audio\\u000169.wav"}, // u000169
    {0x003F0014u, 2746u, 0x402FBE77u, "sc-tr-audio\\u000171.wav"}, // u000171
    {0x003F0016u, 873u, 0x3F5F7CEEu, "sc-tr-audio\\u000173.wav"}, // u000173
    {0x003F0017u, 943u, 0x3F716873u, "sc-tr-audio\\u000189.wav"}, // u000189
    {0x003F0019u, 1362u, 0x3FAE5604u, "sc-tr-audio\\u000175.wav"}, // u000175
    {0x003F001Au, 1464u, 0x3FBB645Au, "sc-tr-audio\\u000187.wav"}, // u000187
    {0x003F001Eu, 863u, 0x3F5CED91u, "sc-tr-audio\\u000200.wav"}, // u000200
    {0x003F0020u, 2537u, 0x40225E35u, "sc-tr-audio\\u000177.wav"}, // u000177
    {0x003F0023u, 861u, 0x3F5C6A7Fu, "sc-tr-audio\\u000179.wav"}, // u000179
    {0x003F0025u, 2133u, 0x40088312u, "sc-tr-audio\\u000181.wav"}, // u000181
    {0x003F0026u, 1160u, 0x3F947AE1u, "sc-tr-audio\\u000183.wav"}, // u000183
    {0x003F0028u, 1250u, 0x3FA00000u, "sc-tr-audio\\u000198.wav"}, // u000198
    {0x00400036u, 1634u, 0x3FD126E9u, "sc-tr-audio\\u000271.wav"}, // u000271
    {0x00400037u, 5747u, 0x40B7E76Du, "sc-tr-audio\\u000220.wav"}, // u000220
    {0x00420001u, 923u, 0x3F6C49BAu, "sc-tr-audio\\u000510.wav"}, // u000510
    {0x00420003u, 2217u, 0x400DE354u, "sc-tr-audio\\u000512.wav"}, // u000512
    {0x0043000Fu, 1429u, 0x3FB6E979u, "sc-tr-audio\\u000629.wav"}, // u000629
    {0x00430012u, 624u, 0x3F1FBE77u, "sc-tr-audio\\u000631.wav"}, // u000631
    {0x00430014u, 1115u, 0x3F8EB852u, "sc-tr-audio\\u000633.wav"}, // u000633
    {0x0043001Au, 1210u, 0x3F9AE148u, "sc-tr-audio\\u000570.wav"}, // u000570
    {0x0043001Eu, 1739u, 0x3FDE978Du, "sc-tr-audio\\u000575.wav"}, // u000575
    {0x00430020u, 5011u, 0x40A05A1Du, "sc-tr-audio\\u000577.wav"}, // u000577
    {0x00430022u, 1938u, 0x3FF81062u, "sc-tr-audio\\u000579.wav"}, // u000579
    {0x00430044u, 1379u, 0x3FB08312u, "sc-tr-audio\\u000572.wav"}, // u000572
    {0x00430045u, 1364u, 0x3FAE978Du, "sc-tr-audio\\u000582.wav"}, // u000582
    {0x00430047u, 6363u, 0x40CB9DB2u, "sc-tr-audio\\u000584.wav"}, // u000584
    {0x00430049u, 3175u, 0x404B3333u, "sc-tr-audio\\u000586.wav"}, // u000586
    {0x0043004Cu, 5615u, 0x40B3AE14u, "sc-tr-audio\\u000588.wav"}, // u000588
    {0x0043004Eu, 3340u, 0x4055C28Fu, "sc-tr-audio\\u000590.wav"}, // u000590
    {0x0043004Fu, 9426u, 0x4116D0E5u, "sc-tr-audio\\u000592.wav"}, // u000592
    {0x00430050u, 8087u, 0x4101645Au, "sc-tr-audio\\u000594.wav"}, // u000594
    {0x00430051u, 3829u, 0x40750E56u, "sc-tr-audio\\u000596.wav"}, // u000596
    {0x0043005Eu, 1676u, 0x3FD6872Bu, "sc-tr-audio\\u000627.wav"}, // u000627
    {0x00430060u, 2140u, 0x4008F5C3u, "sc-tr-audio\\u000637.wav"}, // u000637
    {0x004D0017u, 2469u, 0x401E0419u, "sc-tr-audio\\u000791.wav"}, // u000791
    {0x004D001Cu, 2898u, 0x403978D5u, "sc-tr-audio\\u000793.wav"}, // u000793
    {0x004D001Du, 890u, 0x3F63D70Au, "sc-tr-audio\\u000795.wav"}, // u000795
    {0x004D001Eu, 1240u, 0x3F9EB852u, "sc-tr-audio\\u000797.wav"}, // u000797
    {0x004D001Fu, 1282u, 0x3FA41893u, "sc-tr-audio\\u000799.wav"}, // u000799
    {0x004F0015u, 1150u, 0x3F933333u, "sc-tr-audio\\u000926.wav"}, // u000926
    {0x004F001Cu, 4098u, 0x408322D1u, "sc-tr-audio\\u000962.wav"}, // u000962
    {0x00510005u, 1257u, 0x3FA0E560u, "sc-tr-audio\\u001017.wav"}, // u001017
    {0x00510009u, 1359u, 0x3FADF3B6u, "sc-tr-audio\\u001088.wav"}, // u001088
    {0x00510014u, 1916u, 0x3FF53F7Du, "sc-tr-audio\\u001018.wav"}, // u001018
    {0x00510018u, 3859u, 0x4076F9DBu, "sc-tr-audio\\u001019.wav"}, // u001019
    {0x0051001Au, 4358u, 0x408B74BCu, "sc-tr-audio\\u001039.wav"}, // u001039
    {0x0051001Eu, 2060u, 0x4003D70Au, "sc-tr-audio\\u001090.wav"}, // u001090
    {0x00510032u, 4180u, 0x4085C28Fu, "sc-tr-audio\\u001064.wav"}, // u001064
    {0x00510035u, 5829u, 0x40BA872Bu, "sc-tr-audio\\u001080.wav"}, // u001080
    {0x0051003Cu, 1242u, 0x3F9EF9DBu, "sc-tr-audio\\u001065.wav"}, // u001065
    {0x0051003Eu, 8877u, 0x410E0831u, "sc-tr-audio\\u001066.wav"}, // u001066
    {0x0070001Du, 1484u, 0x3FBDF3B6u, "sc-tr-audio\\u000341.wav"}, // u000341
    {0x0070001Fu, 2454u, 0x401D0E56u, "sc-tr-audio\\u000343.wav"}, // u000343
    {0x00700021u, 3689u, 0x406C1893u, "sc-tr-audio\\u000345.wav"}, // u000345
    {0x00700023u, 1018u, 0x3F824DD3u, "sc-tr-audio\\u000347.wav"}, // u000347
    {0x00700025u, 634u, 0x3F224DD3u, "sc-tr-audio\\u000349.wav"}, // u000349
    {0x00700027u, 1586u, 0x3FCB020Cu, "sc-tr-audio\\u000351.wav"}, // u000351
    {0x00700029u, 756u, 0x3F418937u, "sc-tr-audio\\u000353.wav"}, // u000353
    {0x00710035u, 1063u, 0x3F881062u, "sc-tr-audio\\u000476.wav"}, // u000476
    {0x0071003Eu, 1554u, 0x3FC6E979u, "sc-tr-audio\\u000467.wav"}, // u000467
    {0x00710043u, 1122u, 0x3F8F9DB2u, "sc-tr-audio\\u000474.wav"}, // u000474
    {0x00710053u, 781u, 0x3F47EF9Eu, "sc-tr-audio\\u000497.wav"}, // u000497
    {0x0071006Au, 1312u, 0x3FA7EF9Eu, "sc-tr-audio\\u000499.wav"}, // u000499
    {0x007A0010u, 1300u, 0x3FA66666u, "sc-tr-audio\\u000815.wav"}, // u000815
    {0x007A0012u, 2659u, 0x402A2D0Eu, "sc-tr-audio\\u000817.wav"}, // u000817
    {0x007A0015u, 1043u, 0x3F858106u, "sc-tr-audio\\u000819.wav"}, // u000819
    {0x007A0017u, 1786u, 0x3FE49BA6u, "sc-tr-audio\\u000821.wav"}, // u000821
    {0x007A0019u, 1117u, 0x3F8EF9DBu, "sc-tr-audio\\u000823.wav"}, // u000823
    {0x007A001Bu, 888u, 0x3F6353F8u, "sc-tr-audio\\u000825.wav"}, // u000825
    {0x007A001Du, 5929u, 0x40BDBA5Eu, "sc-tr-audio\\u000827.wav"}, // u000827
    {0x007A0025u, 1434u, 0x3FB78D50u, "sc-tr-audio\\u000867.wav"}, // u000867
    {0x00840005u, 1025u, 0x3F833333u, "sc-tr-audio\\u000109.wav"}, // u000109
    {0x00840007u, 823u, 0x3F52B021u, "sc-tr-audio\\u000113.wav"}, // u000113
    {0x00840008u, 1369u, 0x3FAF3B64u, "sc-tr-audio\\u000102.wav"}, // u000102
    {0x00840009u, 2676u, 0x402B4396u, "sc-tr-audio\\u000111.wav"}, // u000111
    {0x0084000Cu, 1185u, 0x3F97AE14u, "sc-tr-audio\\u000115.wav"}, // u000115
    {0x0084000Eu, 2380u, 0x401851ECu, "sc-tr-audio\\u000117.wav"}, // u000117
    {0x00880001u, 1120u, 0x3F8F5C29u, "sc-tr-audio\\u000881.wav"}, // u000881
};

static const DWORD kTrainingOverrideCount =
    sizeof(g_training_overrides) /
    sizeof(g_training_overrides[0]);

static const TrainingOverride* g_training_pending = 0;
static LONG g_training_request = -1;
static DWORD g_training_active_editor = 0xFFFFFFFFu;
static DWORD g_training_until = 0u;
static DWORD g_training_extend_logged = 0u;
static DWORD g_training_release_logged = 0u;

static const TrainingOverride*
training_override_by_editor(DWORD editor_id)
{
    for (DWORD i = 0; i < kTrainingOverrideCount; ++i) {
        if (g_training_overrides[i].editor_id == editor_id)
            return &g_training_overrides[i];
    }

    return 0;
}


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
        "snd-runtime-manifest-v15-1.log",
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

    const TrainingOverride* pending =
        g_training_pending;

    if (
        pending &&
        pending->editor_id == editor_id &&
        result != -1
    ) {
        g_training_pending = 0;
        g_training_request = result;
        g_training_active_editor = editor_id;
        g_training_until =
            GetTickCount() + pending->duration_ms;
        g_training_extend_logged = 0u;
        g_training_release_logged = 0u;

        typedef void (__cdecl *StopOriginal)(DWORD);

        StopOriginal stop_original =
            (StopOriginal)GetProcAddress(
                original_module(),
                "SND_fn_vStopSoundRequest");

        if (stop_original)
            stop_original((DWORD)result);

        DWORD values[5] = {
            editor_id,
            (DWORD)result,
            pending->duration_ms,
            g_training_until,
            GetTickCount()
        };

        write_line(
            "runtime_native_stopped",
            values,
            5);
    }

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

    if (
        g_training_request != -1 &&
        request_id == (DWORD)g_training_request
    ) {
        DWORD now = GetTickCount();
        LONG remaining =
            (LONG)(g_training_until - now);

        if (remaining > 0) {
            if (!g_training_extend_logged) {
                g_training_extend_logged = 1u;

                DWORD values[4] = {
                    g_training_active_editor,
                    request_id,
                    g_training_until,
                    now
                };

                write_line(
                    "runtime_extend_playing",
                    values,
                    4);
            }

            return TRUE;
        }

        if (!g_training_release_logged) {
            g_training_release_logged = 1u;

            DWORD values[3] = {
                g_training_active_editor,
                request_id,
                now
            };

            write_line(
                "runtime_release",
                values,
                3);
        }
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

    const TrainingOverride* training =
        training_override_by_editor(editor_id);

    if (training && sound) {
        DWORD* duration =
            (DWORD*)((char*)sound + 0x2C);

        DWORD old_duration_bits = *duration;

        *duration = training->duration_bits;

        g_training_pending = training;

        DWORD values[6] = {
            editor_id,
            old_duration_bits,
            training->duration_bits,
            training->duration_ms,
            event_handle,
            GetTickCount()
        };

        write_line(
            "runtime_trigger",
            values,
            6);

        BOOL external_play_result =
            PlaySoundA(
                training->path,
                (HMODULE)NULLPTR,
                0x00000001u |
                0x00000002u |
                0x00020000u);

        DWORD play_values[3] = {
            editor_id,
            (DWORD)external_play_result,
            GetTickCount()
        };

        write_line(
            "runtime_external_play",
            play_values,
            3);
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

    if (
        training &&
        g_training_pending == training
    ) {
        DWORD values[3] = {
            editor_id,
            (DWORD)result,
            GetTickCount()
        };

        write_line(
            "runtime_no_request",
            values,
            3);

        g_training_pending = 0;
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
