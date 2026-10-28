# New 1,258 gameplay voices

Working branch: `work/full-game-1258-integration-20261028`, based on the reviewed
production-preparation branch. The working V27 installation is never an output.

Use `/home/ereng/.cache/splinter-cell-whisper-venv/bin/python` for audio scripts.
For CUDA, use the two private cublas/cudnn library paths documented in
`tools/full_game_voice_audit/README.md`. Models are cached; no external voice
generation service is called.

1. `inventory.py` verifies the 31 original MP3s, all production TXT/index pairs,
   55 voice groups and 1,258 canonical IDs. It decodes only into `build/new1258/`.
2. `transcribe.py --mode source --model medium`, then `--model large-v3`, keeps
   independent full-source transcripts with word times and no text prompts.
3. `resolve_order.py` preserves the handoff order and records the **observed Kola
   permutation**: mafioso_1, mafioso_2, mafioso; technician_2, technician. Both
   source models support the order; the medium whole-text similarity is 99.3%.
4. `select_alignment.py` chooses complete source coverage. `segment.py --model
   selected --version v02` emits immutable candidates. v01 used the declared
   order and is retained only for comparison.
5. `transcribe.py --mode clips --model large-v3` independently transcribes each
   cut. `review.py` keeps text checks, acoustic margins, approval and game tests
   as separate statuses. `--model medium --only-text-review` checks disagreements.
6. `refine_boundaries.py` records v03 acoustic-gap corrections.
   `repair_reviewed_boundaries.py` records v04 corrections using alternate-model
   word timings. Recut only IDs listed by the repair tool with `segment.py
   --model selected --version v04 --only ...`, then re-run isolated ASR.

Outputs live under `dubbing/full-game-new-voices/qa/R001_20261028/`; WAVs are in
`review_pending/R001_20261028/vNN/`. `expected.json` is the immutable declared
order; `resolved_expected.json` is the corrected order. Never apply legacy
678-line grouping or substitute a neighboring source for a missing match.

## Independent integration research

`sandbox.py` creates a byte-independent Wine-prefix copy and a full live-game
baseline. It isolates Linux home-directory links in the Windows user profile.
The original 1,086 WAVs, DLLs, fonts, subtitles and sound banks are preserved.

`runtime_map.py` maps 1,258 IDs to 2,852 physical resource occurrences. There are
192 map/event combinations with multiple leaves, so the existing V27 Dare hook's
event/duration dispatch cannot identify the selected bark safely.

`native_preview.py --version pNN` therefore prepares **isolated native PCM bank
previews**. It preserves event IDs, random/switch/sequence data and every unrelated
resource. It relocates map metadata and PCM blocks in four English LM0 copies.
The existing V27 DLL is unchanged. Original game effects and spatial playback
remain native; whether additional processing is needed requires game testing.

`validate_native.py --version pNN` independently decodes every new resource,
checks unchanged metadata, and rejects collisions with the 1,086 legacy V27
duration entries. Binary validation is not an in-game playback test. Preview
banks remain unapproved until cut QA and runtime testing are complete.

Only tools and text evidence are committed. MP3/WAVs, Wine copies, derived banks,
models and decoder binaries remain outside Git.
