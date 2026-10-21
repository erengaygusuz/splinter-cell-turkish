# Fisher boundary review v3 — local handoff

Start with [the summary](fisher_qa_summary.md), [201 decisions](fisher_qa_decisions.tsv), or [the listening queue](listen_review.html).

**No listening approval has been given.** All 201 selections are `NEEDS_LISTEN`; `approved` and `game_ready` are untouched. `NEEDS_LISTEN` extends the handoff's three-state vocabulary so a technically screened but unheard clip is not mislabeled as approved or defective.

The selection contains 174 existing v01 files and 27 new v03 candidates. Use `selected_path` in the TSV; do not blindly select the highest version elsewhere in the archive. In particular u000041, u000435, u000604 and u000723 retain v01. The M3U8 playlist and HTML page reference the actual selected files without copying or replacing old audio.

## Reproduce and verify

Run from `/run/media/ereng/files/projects/splinter-cell-turkish`:

```bash
PY=/home/ereng/.cache/splinter-cell-whisper-venv/bin/python
TOOL=dubbing/characters/sam_fisher/tools/fisher_boundary_qa_v3.py

# Refuses changed source inputs. Existing identical v03 cuts are verified, not overwritten.
"$PY" "$TOOL" build

# Uses the hash-verified caches when present. Models are local; no expected-text prompt.
"$PY" "$TOOL" transcribe
"$PY" "$TOOL" context

# Rebuild only this version's reports; preserve original inputs and older reports.
"$PY" "$TOOL" report
"$PY" "$TOOL" verify

python3 -m unittest discover -s dubbing/characters/sam_fisher/tools -p 'test_fisher_boundary_qa_v3.py' -v
python3 dubbing/characters/sam_fisher/tools/render_fisher_boundary_evidence.py
```

Requirements: ffmpeg, numpy; faster-whisper/rapidfuzz in the named ASR environment; matplotlib in the system Python for waveform rendering. `environment.json` records installed versions. PCM cuts use full-source decoding followed by an exact, end-exclusive sample slice. No normalization, fade, stretch, or game encoding is performed.

`cut_plan.json` is the fixed reviewed timing plan; `new_cut_manifest.tsv` records the rounded sample positions. Do not edit this plan and overwrite a generated WAV. Any further cut change must use another version and a separate manifest. No script here promotes a candidate to approved.

`report` rewrites the generated decision TSV, so subsequent human decisions should be recorded in a **new versioned manifest**, with listener, date, selected SHA-256, and separate onset/offset/neighbor/content decisions. Only after actual listening should an existing archive approval workflow be used.

The input snapshot also contains pre-existing Python bytecode. If a later environment refresh legitimately changes those files, retain this snapshot and start another review version instead of silently accepting different hashes.
