# Technical research status

## Working findings

The PC build loads `DareAudio.dll`, which in turn imports the legacy SND API
from `SNDDSound3DDLL_VBR.dll`.

Disassembly and vtable inspection identified the following
`UDareAudioSubsystem` entries:

- `+0x068` — `StopSound`
- `+0x07C` — `PlaySoundW`
- `+0x0C0` — `AddRequest`

The runtime experiments preserve the original 291-export SND DLL ABI while
intercepting selected calls.

## Current diagnostic

V11 installs a passive vtable hook for `PlaySoundW`.

During the latest Training test, nine observed DareAudio playback calls matched
nine SND request sends. The expected opening dialogue event IDs
`003C0000`–`003C0004` were mapped by the SND layer but were not observed by the
V11 `PlaySoundW` hook even though those original English lines were heard.

Therefore the opening face-to-face dialogue should not yet be assumed to use
the same runtime path as the later observed Training dialogue.

## Next investigation

Trace the opening scripted dialogue from its UnrealScript/HUD-visible sound
objects into DareAudio and determine which runtime call path actually starts
those sounds before attempting another global Turkish-audio override.
