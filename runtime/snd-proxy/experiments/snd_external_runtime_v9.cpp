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
static DWORD g_external_pending = 0;
static DWORD g_external_pending_duration = 0;
static LONG g_external_request = -1;
static DWORD g_external_until = 0;
static DWORD g_external_extended_logged = 0;
static DWORD g_external_release_logged = 0;

struct ExternalAudioEntry
{
    DWORD editor_id;
    DWORD duration_ms;
    const char* path;
};

static const ExternalAudioEntry g_external_audio[] =
{
    {0x00660002u, 3781u, "sc-tr-audio\\u000001.wav"},
    {0x00660001u, 3502u, "sc-tr-audio\\u000002.wav"},
    {0x00660000u, 2360u, "sc-tr-audio\\u000003.wav"},
    {0x003C002Au, 3195u, "sc-tr-audio\\u000004.wav"},
    {0x00820001u, 838u, "sc-tr-audio\\u000005.wav"},
    {0x003C002Bu, 9566u, "sc-tr-audio\\u000006.wav"},
    {0x003C002Cu, 1966u, "sc-tr-audio\\u000007.wav"},
    {0x003C002Du, 4555u, "sc-tr-audio\\u000008.wav"},
    {0x003C002Eu, 3173u, "sc-tr-audio\\u000009.wav"},
    {0x003C0028u, 6795u, "sc-tr-audio\\u000010.wav"},
    {0x003C0029u, 6388u, "sc-tr-audio\\u000011.wav"},
    {0x003C002Fu, 5710u, "sc-tr-audio\\u000012.wav"},
    {0x003C0000u, 3053u, "sc-tr-audio\\u000013.wav"},
    {0x003C0001u, 2701u, "sc-tr-audio\\u000014.wav"},
    {0x003C0002u, 2028u, "sc-tr-audio\\u000015.wav"},
    {0x003C0003u, 908u, "sc-tr-audio\\u000016.wav"},
    {0x003C0004u, 3546u, "sc-tr-audio\\u000017.wav"},
    {0x003C0007u, 3976u, "sc-tr-audio\\u000018.wav"},
    {0x003C0008u, 4735u, "sc-tr-audio\\u000019.wav"},
    {0x003C0009u, 1828u, "sc-tr-audio\\u000020.wav"},
    {0x003C000Au, 6573u, "sc-tr-audio\\u000021.wav"},
    {0x003C000Bu, 1369u, "sc-tr-audio\\u000022.wav"},
    {0x003C000Cu, 4370u, "sc-tr-audio\\u000023.wav"},
    {0x003C000Du, 1674u, "sc-tr-audio\\u000024.wav"},
    {0x003C000Eu, 3644u, "sc-tr-audio\\u000025.wav"},
    {0x003C000Fu, 1619u, "sc-tr-audio\\u000026.wav"},
    {0x003C0010u, 6672u, "sc-tr-audio\\u000027.wav"},
    {0x003C0011u, 1093u, "sc-tr-audio\\u000028.wav"},
    {0x003C0012u, 11693u, "sc-tr-audio\\u000029.wav"},
    {0x00820000u, 8297u, "sc-tr-audio\\u000030.wav"},
    {0x003C0014u, 1045u, "sc-tr-audio\\u000031.wav"},
    {0x003C0017u, 2222u, "sc-tr-audio\\u000034.wav"},
    {0x003C0019u, 3881u, "sc-tr-audio\\u000036.wav"},
    {0x003C001Cu, 1828u, "sc-tr-audio\\u000039.wav"},
    {0x003C001Eu, 2951u, "sc-tr-audio\\u000041.wav"},
    {0x003C0020u, 2255u, "sc-tr-audio\\u000043.wav"},
    {0x003C0022u, 885u, "sc-tr-audio\\u000045.wav"},
    {0x003C0024u, 3056u, "sc-tr-audio\\u000047.wav"},
    {0x003D0004u, 1492u, "sc-tr-audio\\u000052.wav"},
    {0x003D0006u, 2045u, "sc-tr-audio\\u000054.wav"},
    {0x003D0008u, 1761u, "sc-tr-audio\\u000056.wav"},
    {0x003D0039u, 8610u, "sc-tr-audio\\u000058.wav"},
    {0x003D0030u, 4255u, "sc-tr-audio\\u000062.wav"},
    {0x003D0031u, 4425u, "sc-tr-audio\\u000063.wav"},
    {0x003D002Fu, 2941u, "sc-tr-audio\\u000066.wav"},
    {0x003D000Fu, 5597u, "sc-tr-audio\\u000067.wav"},
    {0x003D0011u, 2549u, "sc-tr-audio\\u000068.wav"},
    {0x003D0000u, 11135u, "sc-tr-audio\\u000069.wav"},
    {0x003D0029u, 4527u, "sc-tr-audio\\u000070.wav"},
    {0x003D0001u, 6812u, "sc-tr-audio\\u000071.wav"},
    {0x003D003Du, 13829u, "sc-tr-audio\\u000072.wav"},
    {0x003D000Du, 14961u, "sc-tr-audio\\u000073.wav"},
    {0x003D002Au, 3769u, "sc-tr-audio\\u000074.wav"},
    {0x003D002Bu, 4507u, "sc-tr-audio\\u000075.wav"},
    {0x003D002Cu, 3487u, "sc-tr-audio\\u000076.wav"},
    {0x003D000Eu, 5547u, "sc-tr-audio\\u000077.wav"},
    {0x003D0014u, 3764u, "sc-tr-audio\\u000079.wav"},
    {0x003D0015u, 836u, "sc-tr-audio\\u000080.wav"},
    {0x003D0017u, 3746u, "sc-tr-audio\\u000082.wav"},
    {0x003D0018u, 1337u, "sc-tr-audio\\u000083.wav"},
    {0x003D001Au, 7673u, "sc-tr-audio\\u000085.wav"},
    {0x003D001Bu, 898u, "sc-tr-audio\\u000086.wav"},
    {0x003D001Du, 1833u, "sc-tr-audio\\u000088.wav"},
    {0x003D001Fu, 6792u, "sc-tr-audio\\u000090.wav"},
    {0x003D0020u, 833u, "sc-tr-audio\\u000091.wav"},
    {0x003D0021u, 7555u, "sc-tr-audio\\u000092.wav"},
    {0x00840000u, 8805u, "sc-tr-audio\\u000093.wav"},
    {0x00840001u, 893u, "sc-tr-audio\\u000094.wav"},
    {0x00840002u, 7513u, "sc-tr-audio\\u000095.wav"},
    {0x00840003u, 3485u, "sc-tr-audio\\u000096.wav"},
    {0x00840004u, 8810u, "sc-tr-audio\\u000097.wav"},
    {0x00840014u, 1369u, "sc-tr-audio\\u000102.wav"},
    {0x00840015u, 3996u, "sc-tr-audio\\u000103.wav"},
    {0x006D0003u, 6243u, "sc-tr-audio\\u000106.wav"},
    {0x006D0000u, 5403u, "sc-tr-audio\\u000107.wav"},
    {0x006D0001u, 7782u, "sc-tr-audio\\u000108.wav"},
    {0x00840005u, 1025u, "sc-tr-audio\\u000109.wav"},
    {0x00840007u, 2676u, "sc-tr-audio\\u000111.wav"},
    {0x00840009u, 823u, "sc-tr-audio\\u000113.wav"},
    {0x0084000Bu, 1185u, "sc-tr-audio\\u000115.wav"},
    {0x0084000Du, 2380u, "sc-tr-audio\\u000117.wav"},
    {0x003E0011u, 2135u, "sc-tr-audio\\u000119.wav"},
    {0x003E0012u, 965u, "sc-tr-audio\\u000120.wav"},
    {0x003E0013u, 9828u, "sc-tr-audio\\u000121.wav"},
    {0x003E0025u, 796u, "sc-tr-audio\\u000122.wav"},
    {0x003E0026u, 816u, "sc-tr-audio\\u000123.wav"},
    {0x003E0027u, 2854u, "sc-tr-audio\\u000124.wav"},
    {0x003E0028u, 2786u, "sc-tr-audio\\u000125.wav"},
    {0x003E0029u, 741u, "sc-tr-audio\\u000126.wav"},
    {0x003E002Au, 1569u, "sc-tr-audio\\u000127.wav"},
    {0x003E002Bu, 7583u, "sc-tr-audio\\u000128.wav"},
    {0x003E0014u, 13501u, "sc-tr-audio\\u000129.wav"},
    {0x003F0003u, 2038u, "sc-tr-audio\\u000158.wav"},
    {0x003F0004u, 3467u, "sc-tr-audio\\u000159.wav"},
    {0x003F0005u, 1086u, "sc-tr-audio\\u000160.wav"},
    {0x003F0006u, 2829u, "sc-tr-audio\\u000161.wav"},
    {0x003F0007u, 1920u, "sc-tr-audio\\u000162.wav"},
    {0x003F0008u, 5595u, "sc-tr-audio\\u000163.wav"},
    {0x003F0038u, 2279u, "sc-tr-audio\\u000164.wav"},
    {0x003F003Au, 2485u, "sc-tr-audio\\u000166.wav"},
    {0x003F003Cu, 8171u, "sc-tr-audio\\u000168.wav"},
    {0x003F0020u, 3173u, "sc-tr-audio\\u000169.wav"},
    {0x003F0022u, 2746u, "sc-tr-audio\\u000171.wav"},
    {0x003F0024u, 873u, "sc-tr-audio\\u000173.wav"},
    {0x003F0026u, 1362u, "sc-tr-audio\\u000175.wav"},
    {0x003F0009u, 2537u, "sc-tr-audio\\u000177.wav"},
    {0x003F000Bu, 861u, "sc-tr-audio\\u000179.wav"},
    {0x003F000Du, 2133u, "sc-tr-audio\\u000181.wav"},
    {0x003F000Fu, 1160u, "sc-tr-audio\\u000183.wav"},
    {0x003F0011u, 1576u, "sc-tr-audio\\u000185.wav"},
    {0x003F0013u, 1464u, "sc-tr-audio\\u000187.wav"},
    {0x003F0015u, 943u, "sc-tr-audio\\u000189.wav"},
    {0x003F0017u, 1277u, "sc-tr-audio\\u000191.wav"},
    {0x003F0019u, 1551u, "sc-tr-audio\\u000193.wav"},
    {0x003F001Bu, 978u, "sc-tr-audio\\u000195.wav"},
    {0x003F001Cu, 1250u, "sc-tr-audio\\u000198.wav"},
    {0x003F001Eu, 863u, "sc-tr-audio\\u000200.wav"},
    {0x00400034u, 5747u, "sc-tr-audio\\u000220.wav"},
    {0x006D0002u, 3712u, "sc-tr-audio\\u000232.wav"},
    {0x00400000u, 5276u, "sc-tr-audio\\u000243.wav"},
    {0x00400001u, 1220u, "sc-tr-audio\\u000244.wav"},
    {0x00400002u, 1095u, "sc-tr-audio\\u000245.wav"},
    {0x00400003u, 1883u, "sc-tr-audio\\u000246.wav"},
    {0x00400004u, 4986u, "sc-tr-audio\\u000247.wav"},
    {0x00400005u, 880u, "sc-tr-audio\\u000248.wav"},
    {0x00400006u, 4891u, "sc-tr-audio\\u000249.wav"},
    {0x00400007u, 1988u, "sc-tr-audio\\u000250.wav"},
    {0x00400008u, 6695u, "sc-tr-audio\\u000251.wav"},
    {0x00400023u, 3594u, "sc-tr-audio\\u000252.wav"},
    {0x00400024u, 3530u, "sc-tr-audio\\u000253.wav"},
    {0x00400025u, 1053u, "sc-tr-audio\\u000254.wav"},
    {0x00400040u, 2128u, "sc-tr-audio\\u000255.wav"},
    {0x00400041u, 3248u, "sc-tr-audio\\u000256.wav"},
    {0x00400042u, 4522u, "sc-tr-audio\\u000257.wav"},
    {0x00400043u, 1676u, "sc-tr-audio\\u000258.wav"},
    {0x00400044u, 6994u, "sc-tr-audio\\u000259.wav"},
    {0x0040000Bu, 4258u, "sc-tr-audio\\u000261.wav"},
    {0x0040000Du, 1344u, "sc-tr-audio\\u000263.wav"},
    {0x0040000Fu, 1230u, "sc-tr-audio\\u000265.wav"},
    {0x00400011u, 1621u, "sc-tr-audio\\u000267.wav"},
    {0x00400013u, 1048u, "sc-tr-audio\\u000269.wav"},
    {0x00400015u, 1634u, "sc-tr-audio\\u000271.wav"},
    {0x00400017u, 1756u, "sc-tr-audio\\u000273.wav"},
    {0x00400019u, 776u, "sc-tr-audio\\u000275.wav"},
    {0x0040001Au, 2110u, "sc-tr-audio\\u000276.wav"},
    {0x0040001Cu, 1841u, "sc-tr-audio\\u000278.wav"},
    {0x00400030u, 8526u, "sc-tr-audio\\u000282.wav"},
    {0x00400031u, 2334u, "sc-tr-audio\\u000283.wav"},
    {0x00400032u, 1798u, "sc-tr-audio\\u000284.wav"},
    {0x00400020u, 1816u, "sc-tr-audio\\u000285.wav"},
    {0x00400021u, 1806u, "sc-tr-audio\\u000286.wav"},
    {0x00400022u, 1978u, "sc-tr-audio\\u000287.wav"},
    {0x00410000u, 1095u, "sc-tr-audio\\u000293.wav"},
    {0x00410001u, 903u, "sc-tr-audio\\u000294.wav"},
    {0x00410002u, 4048u, "sc-tr-audio\\u000295.wav"},
    {0x00410003u, 1028u, "sc-tr-audio\\u000296.wav"},
    {0x00410004u, 7999u, "sc-tr-audio\\u000297.wav"},
    {0x00410005u, 10172u, "sc-tr-audio\\u000298.wav"},
    {0x00410006u, 1841u, "sc-tr-audio\\u000299.wav"},
    {0x00410007u, 1616u, "sc-tr-audio\\u000300.wav"},
    {0x00410008u, 5440u, "sc-tr-audio\\u000301.wav"},
    {0x00410009u, 1686u, "sc-tr-audio\\u000302.wav"},
    {0x0041000Au, 1267u, "sc-tr-audio\\u000303.wav"},
    {0x0041000Bu, 950u, "sc-tr-audio\\u000304.wav"},
    {0x0041000Cu, 3932u, "sc-tr-audio\\u000305.wav"},
    {0x00410013u, 826u, "sc-tr-audio\\u000307.wav"},
    {0x006F0000u, 13113u, "sc-tr-audio\\u000311.wav"},
    {0x006F0001u, 4866u, "sc-tr-audio\\u000312.wav"},
    {0x006F0002u, 8132u, "sc-tr-audio\\u000313.wav"},
    {0x006F0004u, 2996u, "sc-tr-audio\\u000314.wav"},
    {0x006F0005u, 1287u, "sc-tr-audio\\u000315.wav"},
    {0x006F0006u, 6559u, "sc-tr-audio\\u000316.wav"},
    {0x00700001u, 5139u, "sc-tr-audio\\u000331.wav"},
    {0x00700002u, 5532u, "sc-tr-audio\\u000332.wav"},
    {0x00700013u, 4866u, "sc-tr-audio\\u000333.wav"},
    {0x00700017u, 6114u, "sc-tr-audio\\u000334.wav"},
    {0x00700018u, 1295u, "sc-tr-audio\\u000335.wav"},
    {0x0070001Au, 5211u, "sc-tr-audio\\u000336.wav"},
    {0x0070001Bu, 1691u, "sc-tr-audio\\u000337.wav"},
    {0x0070001Cu, 3632u, "sc-tr-audio\\u000338.wav"},
    {0x00700003u, 3627u, "sc-tr-audio\\u000339.wav"},
    {0x0070002Du, 2437u, "sc-tr-audio\\u000340.wav"},
    {0x0070001Du, 1484u, "sc-tr-audio\\u000341.wav"},
    {0x0070001Fu, 2454u, "sc-tr-audio\\u000343.wav"},
    {0x00700021u, 3689u, "sc-tr-audio\\u000345.wav"},
    {0x00700023u, 1018u, "sc-tr-audio\\u000347.wav"},
    {0x00700025u, 634u, "sc-tr-audio\\u000349.wav"},
    {0x00700027u, 1586u, "sc-tr-audio\\u000351.wav"},
    {0x00700029u, 756u, "sc-tr-audio\\u000353.wav"},
    {0x00730003u, 5433u, "sc-tr-audio\\u000361.wav"},
    {0x00890000u, 8975u, "sc-tr-audio\\u000362.wav"},
    {0x00890001u, 1404u, "sc-tr-audio\\u000363.wav"},
    {0x00890002u, 9059u, "sc-tr-audio\\u000364.wav"},
    {0x00890003u, 4926u, "sc-tr-audio\\u000365.wav"},
    {0x0072001Au, 5939u, "sc-tr-audio\\u000394.wav"},
    {0x0072001Bu, 979u, "sc-tr-audio\\u000395.wav"},
    {0x0072001Cu, 6508u, "sc-tr-audio\\u000396.wav"},
    {0x00720024u, 8500u, "sc-tr-audio\\u000397.wav"},
    {0x00720025u, 2498u, "sc-tr-audio\\u000398.wav"},
    {0x00720026u, 1709u, "sc-tr-audio\\u000399.wav"},
    {0x00720028u, 5642u, "sc-tr-audio\\u000401.wav"},
    {0x00710013u, 2390u, "sc-tr-audio\\u000422.wav"},
    {0x00710015u, 1165u, "sc-tr-audio\\u000424.wav"},
    {0x00710016u, 2594u, "sc-tr-audio\\u000425.wav"},
    {0x00710017u, 1644u, "sc-tr-audio\\u000426.wav"},
    {0x00710018u, 7298u, "sc-tr-audio\\u000427.wav"},
    {0x00710019u, 7166u, "sc-tr-audio\\u000428.wav"},
    {0x0071002Du, 5328u, "sc-tr-audio\\u000429.wav"},
    {0x0071002Eu, 1529u, "sc-tr-audio\\u000430.wav"},
    {0x0071002Fu, 4308u, "sc-tr-audio\\u000431.wav"},
    {0x00710030u, 1976u, "sc-tr-audio\\u000432.wav"},
    {0x00710031u, 6585u, "sc-tr-audio\\u000433.wav"},
    {0x00710010u, 4577u, "sc-tr-audio\\u000434.wav"},
    {0x00710011u, 1489u, "sc-tr-audio\\u000435.wav"},
    {0x00710012u, 3946u, "sc-tr-audio\\u000436.wav"},
    {0x0071006Eu, 4741u, "sc-tr-audio\\u000437.wav"},
    {0x0071004Cu, 1554u, "sc-tr-audio\\u000467.wav"},
    {0x0071004Fu, 980u, "sc-tr-audio\\u000470.wav"},
    {0x00710053u, 1122u, "sc-tr-audio\\u000474.wav"},
    {0x00710055u, 1063u, "sc-tr-audio\\u000476.wav"},
    {0x00710058u, 1152u, "sc-tr-audio\\u000495.wav"},
    {0x0071005Au, 781u, "sc-tr-audio\\u000497.wav"},
    {0x0071005Cu, 1312u, "sc-tr-audio\\u000499.wav"},
    {0x00660014u, 3133u, "sc-tr-audio\\u000501.wav"},
    {0x00420001u, 923u, "sc-tr-audio\\u000510.wav"},
    {0x00420003u, 2217u, "sc-tr-audio\\u000512.wav"},
    {0x00420004u, 12916u, "sc-tr-audio\\u000525.wav"},
    {0x00420005u, 943u, "sc-tr-audio\\u000526.wav"},
    {0x00420006u, 2193u, "sc-tr-audio\\u000527.wav"},
    {0x00420007u, 1878u, "sc-tr-audio\\u000528.wav"},
    {0x00420008u, 4427u, "sc-tr-audio\\u000529.wav"},
    {0x0043001Au, 1210u, "sc-tr-audio\\u000570.wav"},
    {0x0043001Cu, 1379u, "sc-tr-audio\\u000572.wav"},
    {0x0043001Fu, 1739u, "sc-tr-audio\\u000575.wav"},
    {0x00430021u, 5011u, "sc-tr-audio\\u000577.wav"},
    {0x00430023u, 1938u, "sc-tr-audio\\u000579.wav"},
    {0x00430044u, 1364u, "sc-tr-audio\\u000582.wav"},
    {0x00430046u, 6363u, "sc-tr-audio\\u000584.wav"},
    {0x00430048u, 3175u, "sc-tr-audio\\u000586.wav"},
    {0x0043004Au, 5615u, "sc-tr-audio\\u000588.wav"},
    {0x0043004Cu, 3340u, "sc-tr-audio\\u000590.wav"},
    {0x0043004Eu, 9426u, "sc-tr-audio\\u000592.wav"},
    {0x00430050u, 8087u, "sc-tr-audio\\u000594.wav"},
    {0x00430052u, 3829u, "sc-tr-audio\\u000596.wav"},
    {0x00430009u, 1990u, "sc-tr-audio\\u000601.wav"},
    {0x0043000Bu, 2614u, "sc-tr-audio\\u000603.wav"},
    {0x0043000Cu, 2442u, "sc-tr-audio\\u000604.wav"},
    {0x0043000Du, 994u, "sc-tr-audio\\u000605.wav"},
    {0x00430016u, 3565u, "sc-tr-audio\\u000606.wav"},
    {0x00430017u, 4784u, "sc-tr-audio\\u000607.wav"},
    {0x00430018u, 863u, "sc-tr-audio\\u000608.wav"},
    {0x00430019u, 1953u, "sc-tr-audio\\u000609.wav"},
    {0x00430000u, 2504u, "sc-tr-audio\\u000610.wav"},
    {0x00430002u, 4592u, "sc-tr-audio\\u000612.wav"},
    {0x00430025u, 2155u, "sc-tr-audio\\u000613.wav"},
    {0x00430026u, 6889u, "sc-tr-audio\\u000614.wav"},
    {0x00430027u, 7268u, "sc-tr-audio\\u000615.wav"},
    {0x00430028u, 1235u, "sc-tr-audio\\u000616.wav"},
    {0x00430029u, 7558u, "sc-tr-audio\\u000617.wav"},
    {0x0043005Au, 1946u, "sc-tr-audio\\u000618.wav"},
    {0x0043005Bu, 1796u, "sc-tr-audio\\u000619.wav"},
    {0x0043005Cu, 5435u, "sc-tr-audio\\u000620.wav"},
    {0x00430057u, 1788u, "sc-tr-audio\\u000621.wav"},
    {0x00430058u, 1532u, "sc-tr-audio\\u000622.wav"},
    {0x00430059u, 2741u, "sc-tr-audio\\u000623.wav"},
    {0x0043000Eu, 1676u, "sc-tr-audio\\u000627.wav"},
    {0x00430010u, 1429u, "sc-tr-audio\\u000629.wav"},
    {0x00430012u, 624u, "sc-tr-audio\\u000631.wav"},
    {0x00430014u, 1115u, "sc-tr-audio\\u000633.wav"},
    {0x0043005Eu, 763u, "sc-tr-audio\\u000636.wav"},
    {0x0043005Fu, 2140u, "sc-tr-audio\\u000637.wav"},
    {0x00100032u, 3482u, "sc-tr-audio\\u000698.wav"},
    {0x00100033u, 2336u, "sc-tr-audio\\u000699.wav"},
    {0x00100034u, 7540u, "sc-tr-audio\\u000700.wav"},
    {0x0010002Fu, 6368u, "sc-tr-audio\\u000701.wav"},
    {0x00100030u, 2789u, "sc-tr-audio\\u000702.wav"},
    {0x00100031u, 2150u, "sc-tr-audio\\u000703.wav"},
    {0x00100002u, 1255u, "sc-tr-audio\\u000706.wav"},
    {0x00100004u, 1616u, "sc-tr-audio\\u000708.wav"},
    {0x00100006u, 1801u, "sc-tr-audio\\u000710.wav"},
    {0x00100008u, 3577u, "sc-tr-audio\\u000712.wav"},
    {0x00100035u, 2739u, "sc-tr-audio\\u000714.wav"},
    {0x00100038u, 905u, "sc-tr-audio\\u000717.wav"},
    {0x0010003Au, 1995u, "sc-tr-audio\\u000719.wav"},
    {0x0010003Cu, 1058u, "sc-tr-audio\\u000721.wav"},
    {0x0010003Eu, 988u, "sc-tr-audio\\u000723.wav"},
    {0x00100040u, 1579u, "sc-tr-audio\\u000725.wav"},
    {0x00100042u, 1532u, "sc-tr-audio\\u000727.wav"},
    {0x004C000Au, 4697u, "sc-tr-audio\\u000731.wav"},
    {0x004C000Bu, 1581u, "sc-tr-audio\\u000732.wav"},
    {0x004C000Cu, 10486u, "sc-tr-audio\\u000733.wav"},
    {0x004C000Du, 3023u, "sc-tr-audio\\u000734.wav"},
    {0x004C000Eu, 1003u, "sc-tr-audio\\u000735.wav"},
    {0x004C000Fu, 5842u, "sc-tr-audio\\u000736.wav"},
    {0x004C0010u, 3637u, "sc-tr-audio\\u000737.wav"},
    {0x004C0011u, 8523u, "sc-tr-audio\\u000738.wav"},
    {0x004C0024u, 1778u, "sc-tr-audio\\u000739.wav"},
    {0x004C0025u, 1312u, "sc-tr-audio\\u000740.wav"},
    {0x004C0026u, 4577u, "sc-tr-audio\\u000741.wav"},
    {0x004C0027u, 1771u, "sc-tr-audio\\u000742.wav"},
    {0x004C0028u, 711u, "sc-tr-audio\\u000743.wav"},
    {0x004C0029u, 1749u, "sc-tr-audio\\u000744.wav"},
    {0x004C002Au, 6999u, "sc-tr-audio\\u000745.wav"},
    {0x004C002Eu, 7383u, "sc-tr-audio\\u000746.wav"},
    {0x004C0023u, 7318u, "sc-tr-audio\\u000747.wav"},
    {0x004C0006u, 4208u, "sc-tr-audio\\u000748.wav"},
    {0x004C0007u, 1863u, "sc-tr-audio\\u000749.wav"},
    {0x004C0008u, 2256u, "sc-tr-audio\\u000750.wav"},
    {0x004D0002u, 4668u, "sc-tr-audio\\u000782.wav"},
    {0x004D0003u, 2971u, "sc-tr-audio\\u000783.wav"},
    {0x004D0004u, 4048u, "sc-tr-audio\\u000784.wav"},
    {0x004D000Au, 4555u, "sc-tr-audio\\u000785.wav"},
    {0x004D0015u, 5338u, "sc-tr-audio\\u000786.wav"},
    {0x004D0027u, 2400u, "sc-tr-audio\\u000787.wav"},
    {0x004D0028u, 2931u, "sc-tr-audio\\u000788.wav"},
    {0x004D0029u, 4116u, "sc-tr-audio\\u000789.wav"},
    {0x004D0017u, 2469u, "sc-tr-audio\\u000791.wav"},
    {0x004D0019u, 2898u, "sc-tr-audio\\u000793.wav"},
    {0x004D001Bu, 890u, "sc-tr-audio\\u000795.wav"},
    {0x004D001Du, 1240u, "sc-tr-audio\\u000797.wav"},
    {0x004D001Fu, 1282u, "sc-tr-audio\\u000799.wav"},
    {0x007A0010u, 1300u, "sc-tr-audio\\u000815.wav"},
    {0x007A0012u, 2659u, "sc-tr-audio\\u000817.wav"},
    {0x007A0014u, 1043u, "sc-tr-audio\\u000819.wav"},
    {0x007A0016u, 1786u, "sc-tr-audio\\u000821.wav"},
    {0x007A0018u, 1117u, "sc-tr-audio\\u000823.wav"},
    {0x007A001Au, 888u, "sc-tr-audio\\u000825.wav"},
    {0x007A001Cu, 5929u, "sc-tr-audio\\u000827.wav"},
    {0x007A0033u, 1716u, "sc-tr-audio\\u000829.wav"},
    {0x007A0034u, 708u, "sc-tr-audio\\u000830.wav"},
    {0x007A0035u, 3312u, "sc-tr-audio\\u000831.wav"},
    {0x007A0036u, 2290u, "sc-tr-audio\\u000832.wav"},
    {0x007A0037u, 898u, "sc-tr-audio\\u000833.wav"},
    {0x007B0000u, 5665u, "sc-tr-audio\\u000834.wav"},
    {0x007A0043u, 2305u, "sc-tr-audio\\u000835.wav"},
    {0x007A0044u, 950u, "sc-tr-audio\\u000836.wav"},
    {0x007A0045u, 2829u, "sc-tr-audio\\u000837.wav"},
    {0x007A0049u, 5597u, "sc-tr-audio\\u000838.wav"},
    {0x007A004Au, 1135u, "sc-tr-audio\\u000839.wav"},
    {0x007A004Bu, 3639u, "sc-tr-audio\\u000840.wav"},
    {0x007A004Cu, 693u, "sc-tr-audio\\u000841.wav"},
    {0x007A0025u, 1434u, "sc-tr-audio\\u000867.wav"},
    {0x00880001u, 1120u, "sc-tr-audio\\u000881.wav"},
    {0x00880003u, 6542u, "sc-tr-audio\\u000883.wav"},
    {0x00880004u, 2045u, "sc-tr-audio\\u000884.wav"},
    {0x00880005u, 10357u, "sc-tr-audio\\u000885.wav"},
    {0x0088000Cu, 7276u, "sc-tr-audio\\u000886.wav"},
    {0x004E001Cu, 1439u, "sc-tr-audio\\u000910.wav"},
    {0x004E001Eu, 4113u, "sc-tr-audio\\u000912.wav"},
    {0x004E0029u, 8947u, "sc-tr-audio\\u000913.wav"},
    {0x004E002Au, 4940u, "sc-tr-audio\\u000914.wav"},
    {0x004E002Bu, 3791u, "sc-tr-audio\\u000915.wav"},
    {0x004E001Bu, 5941u, "sc-tr-audio\\u000916.wav"},
    {0x007C0001u, 7650u, "sc-tr-audio\\u000917.wav"},
    {0x007C0000u, 7401u, "sc-tr-audio\\u000918.wav"},
    {0x004E000Fu, 3300u, "sc-tr-audio\\u000919.wav"},
    {0x004E0011u, 3305u, "sc-tr-audio\\u000921.wav"},
    {0x004F0014u, 1150u, "sc-tr-audio\\u000926.wav"},
    {0x004F0002u, 8900u, "sc-tr-audio\\u000942.wav"},
    {0x004F000Au, 3275u, "sc-tr-audio\\u000943.wav"},
    {0x004F000Bu, 1559u, "sc-tr-audio\\u000944.wav"},
    {0x004F000Cu, 7610u, "sc-tr-audio\\u000945.wav"},
    {0x004F002Du, 1270u, "sc-tr-audio\\u000946.wav"},
    {0x004F002Eu, 2143u, "sc-tr-audio\\u000947.wav"},
    {0x004F002Fu, 1484u, "sc-tr-audio\\u000948.wav"},
    {0x004F0031u, 9668u, "sc-tr-audio\\u000950.wav"},
    {0x004F0022u, 4188u, "sc-tr-audio\\u000955.wav"},
    {0x004F0024u, 6545u, "sc-tr-audio\\u000957.wav"},
    {0x004F0026u, 1776u, "sc-tr-audio\\u000959.wav"},
    {0x004F0027u, 1694u, "sc-tr-audio\\u000960.wav"},
    {0x004F0029u, 4098u, "sc-tr-audio\\u000962.wav"},
    {0x00500000u, 6949u, "sc-tr-audio\\u000969.wav"},
    {0x00500001u, 1786u, "sc-tr-audio\\u000970.wav"},
    {0x00500002u, 4510u, "sc-tr-audio\\u000971.wav"},
    {0x00500016u, 1836u, "sc-tr-audio\\u000977.wav"},
    {0x00500017u, 868u, "sc-tr-audio\\u000978.wav"},
    {0x00500018u, 2883u, "sc-tr-audio\\u000979.wav"},
    {0x00500019u, 696u, "sc-tr-audio\\u000980.wav"},
    {0x0050001Au, 2070u, "sc-tr-audio\\u000981.wav"},
    {0x0050001Bu, 876u, "sc-tr-audio\\u000982.wav"},
    {0x0050001Cu, 2065u, "sc-tr-audio\\u000983.wav"},
    {0x0050001Du, 2422u, "sc-tr-audio\\u000984.wav"},
    {0x0050001Eu, 1507u, "sc-tr-audio\\u000985.wav"},
    {0x0050001Fu, 6897u, "sc-tr-audio\\u000986.wav"},
    {0x00500020u, 3609u, "sc-tr-audio\\u000987.wav"},
    {0x00500021u, 781u, "sc-tr-audio\\u000988.wav"},
    {0x00500008u, 3307u, "sc-tr-audio\\u000990.wav"},
    {0x00500009u, 6568u, "sc-tr-audio\\u000991.wav"},
    {0x0050000Au, 1247u, "sc-tr-audio\\u000992.wav"},
    {0x0050000Bu, 7921u, "sc-tr-audio\\u000993.wav"},
    {0x00510029u, 3147u, "sc-tr-audio\\u001005.wav"},
    {0x0051002Au, 2080u, "sc-tr-audio\\u001006.wav"},
    {0x0051002Bu, 3278u, "sc-tr-audio\\u001007.wav"},
    {0x007D0000u, 5655u, "sc-tr-audio\\u001008.wav"},
    {0x00510065u, 1257u, "sc-tr-audio\\u001017.wav"},
    {0x00510066u, 1916u, "sc-tr-audio\\u001018.wav"},
    {0x00510067u, 3859u, "sc-tr-audio\\u001019.wav"},
    {0x00510027u, 4358u, "sc-tr-audio\\u001039.wav"},
    {0x00510069u, 6580u, "sc-tr-audio\\u001042.wav"},
    {0x00510047u, 4180u, "sc-tr-audio\\u001064.wav"},
    {0x00510048u, 1242u, "sc-tr-audio\\u001065.wav"},
    {0x00510049u, 8877u, "sc-tr-audio\\u001066.wav"},
    {0x00510046u, 5829u, "sc-tr-audio\\u001080.wav"},
    {0x0051000Au, 1157u, "sc-tr-audio\\u001084.wav"},
    {0x0051000Cu, 3220u, "sc-tr-audio\\u001086.wav"},
    {0x0051000Eu, 1359u, "sc-tr-audio\\u001088.wav"},
    {0x00510010u, 2060u, "sc-tr-audio\\u001090.wav"},
    {0x00510012u, 1187u, "sc-tr-audio\\u001092.wav"},
};

static const ExternalAudioEntry*
external_audio_by_editor(DWORD editor_id)
{
    for (DWORD i = 0; i < 408u; ++i) {
        if (g_external_audio[i].editor_id == editor_id)
            return &g_external_audio[i];
    }

    return (const ExternalAudioEntry*)NULLPTR;
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
        "snd-external-runtime-v9.log",
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

    const ExternalAudioEntry* external_audio =
        external_audio_by_editor(editor_id);

    if (external_audio) {
        write_line(
            "external_trigger",
            &editor_id,
            1);

        // PlaySoundA is the proven V8 backend.
        // A new dialogue replaces any previous PlaySoundA stream.
        BOOL external_ok = PlaySoundA(
            external_audio->path,
            (HMODULE)NULLPTR,
            0x00000001u |  // SND_ASYNC
            0x00000002u |  // SND_NODEFAULT
            0x00020000u);  // SND_FILENAME

        if (external_ok) {
            if (g_external_request != -1) {
                DWORD replaced =
                    (DWORD)g_external_request;

                write_line(
                    "external_replaced",
                    &replaced,
                    1);

                g_external_request = -1;
                g_external_until = 0;
            }

            g_external_pending = 1;
            g_external_pending_duration =
                external_audio->duration_ms;

            g_external_extended_logged = 0;
            g_external_release_logged = 0;
        }
        else {
            write_line(
                "external_play_failed",
                &editor_id,
                1);
        }
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
        g_external_until = GetTickCount() + g_external_pending_duration;

        write_line(
            "external_request",
            (DWORD*)&g_external_request,
            1);

        write_line(
            "external_until",
            &g_external_until,
            1);

        // Keep DareAudio's request identity, but silence the
        // original English SND request immediately.
        typedef void (__cdecl *StopOriginal)(DWORD);

        StopOriginal stop_original =
            (StopOriginal)GetProcAddress(
                original_module(),
                "SND_fn_vStopSoundRequest");

        if (stop_original && result != -1) {
            stop_original((DWORD)result);

            write_line(
                "native_stopped",
                (DWORD*)&g_external_request,
                1);
        }
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

static void
cancel_external_request(DWORD request_id)
{
    if (
        g_external_request != -1 &&
        request_id == (DWORD)g_external_request
    ) {
        PlaySoundA(
            (LPCSTR)NULLPTR,
            (HMODULE)NULLPTR,
            0u);

        write_line(
            "external_cancel",
            &request_id,
            1);

        g_external_request = -1;
        g_external_until = 0;
        g_external_pending = 0;
        g_external_pending_duration = 0;
        g_external_extended_logged = 0;
        g_external_release_logged = 0;
    }
}

extern "C"
__declspec(noinline)
void __cdecl probe_stop_request(DWORD request_id)
    __asm__("_probe_stop_request");

extern "C"
__declspec(noinline)
void __cdecl probe_stop_request(DWORD request_id)
{
    typedef void (__cdecl *Original)(DWORD);

    Original original =
        (Original)GetProcAddress(
            original_module(),
            "SND_fn_vStopSoundRequest");

    if (original)
        original(request_id);

    cancel_external_request(request_id);
}

extern "C"
__declspec(noinline)
void __cdecl probe_stop_request_with_fade(
    DWORD request_id,
    DWORD fade_a,
    DWORD fade_b)
    __asm__("_probe_stop_request_with_fade");

extern "C"
__declspec(noinline)
void __cdecl probe_stop_request_with_fade(
    DWORD request_id,
    DWORD fade_a,
    DWORD fade_b)
{
    typedef void (__cdecl *Original)(
        DWORD,
        DWORD,
        DWORD);

    Original original =
        (Original)GetProcAddress(
            original_module(),
            "SND_fn_vStopSoundRequestWithFade");

    if (original)
        original(
            request_id,
            fade_a,
            fade_b);

    cancel_external_request(request_id);
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
