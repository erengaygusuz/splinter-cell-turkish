typedef unsigned long DWORD;
typedef int BOOL;

struct RuntimeRequestState
{
    DWORD active;
    DWORD request_id;
    DWORD editor_id;
    DWORD until;
    DWORD extend_logged;
};

extern "C" {
extern RuntimeRequestState g_runtime_requests[32];
extern DWORD g_runtime_pause_active;

BOOL __cdecl probe_is_playing(DWORD request_id)
    __asm__("_probe_is_playing");
}

extern "C"
__declspec(noinline)
BOOL __cdecl probe_is_playing_v25(DWORD request_id)
    __asm__("_probe_is_playing_v25");

extern "C"
__declspec(noinline)
BOOL __cdecl probe_is_playing_v25(DWORD request_id)
{
    // While the game is paused, the external waveOut voice is frozen.
    // Keep the matching logical SND request alive as well. Otherwise
    // V18's duration-based poll can expire the request while the WAV is
    // paused, and V23 later resumes an orphan voice on top of the next
    // queued dialogue.
    if (g_runtime_pause_active) {
        for (DWORD i = 0u; i < 32u; ++i) {
            RuntimeRequestState* state =
                &g_runtime_requests[i];

            if (
                state->active &&
                state->request_id == request_id
            )
                return 1;
        }
    }

    return probe_is_playing(request_id);
}
