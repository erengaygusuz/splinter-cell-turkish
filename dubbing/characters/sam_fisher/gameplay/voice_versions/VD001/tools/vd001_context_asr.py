#!/usr/bin/env python3
"""Independent source-window ASR without expected-text prompting."""
import argparse
import json
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
import vd001_audio_qa as qa

parser = argparse.ArgumentParser()
parser.add_argument('--plan', default='context_windows.json')
parser.add_argument('--output', default='context_asr_large_v3.json')
args = parser.parse_args()
qa.check_protected()
_, sources = qa.load_inputs()
sources = {s['key']: s for s in sources}
plan = json.loads((qa.QA / args.plan).read_text())
out = qa.QA / args.output
cache = json.loads(out.read_text()) if out.exists() else {}
audio, model = {}, None
for key, item in plan.items():
    source = sources[item['source_key']]
    if key in cache:
        assert cache[key]['source_sha256'] == source['sha256']
        assert cache[key]['window'] == item
        continue
    if model is None:
        model = WhisperModel('large-v3', device='cuda', compute_type='int8_float16', local_files_only=True)
    if source['key'] not in audio:
        audio[source['key']] = decode_audio(source['path'])
    a, b = item['start_sec'], item['end_sec']
    segments, _ = model.transcribe(audio[source['key']][round(a*16000):round(b*16000)],
        language='tr', beam_size=5, temperature=0, word_timestamps=True,
        condition_on_previous_text=False, vad_filter=False)
    segments = list(segments)
    result = dict(source_sha256=source['sha256'], window=item, model='large-v3',
        device='cuda', compute_type='int8_float16', initial_prompt=None,
        text=' '.join(s.text.strip() for s in segments),
        words=[dict(text=w.word.strip(), start=w.start+a, end=w.end+a, probability=w.probability)
               for s in segments for w in (s.words or [])])
    cache[key] = result
    qa.save_json(out, cache)
    print(key, result['text'], flush=True)
