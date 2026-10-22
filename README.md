# Splinter Cell Turkish

Technical source repository for an unofficial Turkish localization and dubbing
research project for the PC version of *Tom Clancy's Splinter Cell* (2002).

This repository is intentionally **source-only**. It does not contain the game,
Ubisoft assets, installed binaries, generated voice audio, AI model files,
Wine prefixes, build outputs, or local backups.

## Repository layout

- `runtime/snd-proxy/experiments/` — successive SND/DareAudio runtime experiments.
- `subtitles/hud/` — UnrealScript HUD/subtitle research sources.
- `tools/audio-runtime/` — audio inspection, proxy and codec tooling.
- `tools/subtitles/` — subtitle/tracker preparation utilities.
- `tools/localization/` — localization and legacy-patch integration utilities.
- `tools/dubbing/` — dubbing preparation and slot-fit utilities.
- `tools/fmv/` — FMV analysis/subtitle utilities.
- `tools/corpus/` — corpus and transcription utilities.
- `dubbing/characters/` — character-specific QA/preparation tools only.
- `manifests/` — small selected mapping/validation metadata.
- `docs/` — scope and current technical research status.

## Audio runtime research status

The SND proxy experiments are preserved as research versions, not as one
production-ready patch.

- V5 demonstrated external WAV playback.
- V6 extended the game-visible request lifetime.
- V7 stopped the corresponding native English request.
- V8 provided a stable single-line Turkish external-audio proof of concept.
- V9 expanded the approach to the staged dialogue set but exposed sequencing
  problems, so it is retained only as an experiment.
- V10 is a passive SND request diagnostic.
- V11 passively hooks `UDareAudioSubsystem::PlaySoundW` through its vtable.

The latest V11 test confirmed that observed `PlaySoundW` calls correspond to
SND request sends, while the opening Lambert/Fisher face-to-face lines were
audible through the original game audio yet were not observed as the expected
`003C0000`–`003C0004` playback calls. That path remains under investigation.

## Scope

This is a fan-made preservation/localization research project. No affiliation
with or endorsement by Ubisoft is claimed. Rights to third-party game content,
characters, trademarks and original assets remain with their respective owners.
