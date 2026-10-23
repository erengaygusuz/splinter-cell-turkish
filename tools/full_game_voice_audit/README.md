# Installed gameplay voice audit

This pipeline reads the installed V27 game and writes only into
`build/full-game-voice-audit/`. It does not install audio or change game banks.
FMV is excluded. All 412 files under Sounds are inventoried; English and common
banks are decoded, with other installed language banks retained in the inventory.

## Reproduce

Run from the repository root, using the existing Whisper virtual environment
for scripts requiring NumPy or faster-whisper:

1. `python3 tools/full_game_voice_audit/inventory.py`
2. `python3 tools/full_game_voice_audit/build_decoder.py`
3. `python3 tools/full_game_voice_audit/extract.py`
4. `python3 tools/full_game_voice_audit/event_graph.py`
5. `python3 tools/full_game_voice_audit/catalog.py`
6. Run `fingerprints.py` with NumPy, then `catalog.py` again.
7. Run `containers.py` with NumPy and `validate.py` with Python.
8. Run `transcribe.py` and `verify_asr.py` with faster-whisper.

`inventory.py --index-only` reindexes the saved inventory without replacing the
protected installation baseline. Full inventory execution verifies the baseline
and fails if installed files have changed. ASR writes one atomic JSON per WAV
and resumes completed records. CUDA is optional; CPU/int8 is supported.
CUDA libraries, if needed, remain private to the build directory. Set
`LD_LIBRARY_PATH` to its `cuda-runtime/nvidia/cublas/lib` and
`cuda-runtime/nvidia/cudnn/lib` directories for GPU execution.

## Evidence and limitations

* The bundled vgmstream source rejected all version-7 resources because its
  40-byte resource-name capacity check used `>=` rather than `>`. The build
  script patches a private source copy, records hashes, and leaves the decoder
  checkout and game unchanged.
* Leaf resources are extracted using source offsets and lengths. One-resource
  wrappers preserve the actual encoded bytes and codec metadata. Every output
  is checked for the exact rate, channels and sample count. Random/sequence
  containers do not create additional physical voice lines.
* Event editor IDs and resource header IDs are separate namespaces. The graph
  follows event targets, switch selectors and random/sequence tables. It does
  not join equal numeric IDs. The GeorgianCop `005A0003` collision has a
  regression check. Runtime hooking has not been tested or installed.
* All 1,093 original corpus records are compared by PCM identity. Current
  modified LS0 slots are labelled separately from PCM matches: 483 live payloads
  differ from the archived original audio. Their old original WAVs remain intact.
* Exact PCM groups and full-waveform lossy-codec matches are recorded separately.
  A complete equal-length signal correlation >=0.995 plus residual SNR >=20 dB
  is required. Named `.wav`/`.ima` variants additionally support a >=0.985,
  >=15 dB threshold. Identical text/duration alone never merges recordings.
* Bonus maps reference PCM music in `Sounds/Common`, whereas the main game's
  root files use ADPCM and different offsets. The entire PCM files are accounted
  for and compared to compressed music at >0.99 waveform correlation.
* Multitrack ambience streams are indexed separately, including their source
  offsets, metadata and hashes. They are not claimed to have been listened to.
* ASR remains automatic evidence. The second model disables VAD to catch very
  short words missed by silence filtering. Transcription uncertainty and
  nonverbal noises must remain separate from new dialogue decisions.

Large WAVs, decoder builds, CUDA libraries and per-file ASR caches are local
artifacts. Only tools, compact reports and source identity manifests belong in Git.
