#!/usr/bin/env python3
"""Transcribe selected uncertain WAVs with large-v3, without text prompting."""
import json
from faster_whisper import WhisperModel
import vd001_audio_qa as qa

qa.check_protected()
cuts = {r['id']: r for r in qa.selected_cuts()}
targets = json.loads((qa.QA / 'retry_ids.json').read_text())
path = qa.QA / 'isolated_retry_large_v3.json'
cache = json.loads(path.read_text()) if path.exists() else {}
model = None
for ident, reason in targets.items():
    cut = cuts[ident]
    if ident in cache:
        assert cache[ident]['sha256'] == qa.sha(cut['wav_path'])
        continue
    if model is None:
        model = WhisperModel('large-v3', device='cuda', compute_type='int8_float16', local_files_only=True)
    segments, _ = model.transcribe(cut['wav_path'], language='tr', beam_size=5,
        temperature=0, word_timestamps=True, condition_on_previous_text=False, vad_filter=False)
    segments = list(segments)
    text = ' '.join(s.text.strip() for s in segments)
    cache[ident] = dict(sha256=qa.sha(cut['wav_path']), model='large-v3', device='cuda',
        compute_type='int8_float16', initial_prompt=None, reason=reason, text=text,
        match=qa.score(cut['expected_text'],text),
        words=[dict(text=w.word.strip(), start=w.start, end=w.end, probability=w.probability)
               for s in segments for w in (s.words or [])])
    qa.save_json(path,cache)
    print(ident, cache[ident]['match'], text, flush=True)
