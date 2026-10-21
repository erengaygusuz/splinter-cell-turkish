#!/usr/bin/env python3
"""Source-preserving Lambert gameplay segmentation and QA. Never approves audio."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unicodedata
import wave

import numpy as np

BASE = Path('dubbing/characters/irving_lambert')
QA = BASE / 'gameplay/qa/lambert_207_v1_20261021'
RATE = 44100


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tsv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_tsv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def spoken(text):
    return re.sub(r'\[[^\]\n]*\]', '', text).strip()


def norm(text):
    text = unicodedata.normalize('NFKD', spoken(text).casefold().replace('ı', 'i'))
    return ' '.join(re.findall('[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c))))


def score(a, b):
    from rapidfuzz.fuzz import ratio
    return round(ratio(norm(a), norm(b)), 1)


def load_inputs():
    catalog = tsv(BASE / 'gameplay/catalog.tsv')
    assert len(catalog) == len({r['id'] for r in catalog}) == 207
    reference = [s.strip() for s in (BASE / 'reference/irving_lambert_207_sade_v2.txt')
                 .read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    assert reference == [r['prompt'] for r in catalog]
    by_id = {r['id']: r for r in catalog}
    prod = BASE / 'gameplay/production_source/remaining_197'
    groups = [('E001_20261021', 'E001_10_ID_esleme.tsv', 'pilot_order', 10),
              ('R001_20261021', 'Irving_Lambert_Kalan_197_ID_ve_Parti_Esleme.tsv', 'remaining_order', 197)]
    rows, sources = [], []
    for group, filename, order_key, count in groups:
        mapping = tsv(prod / filename)
        assert len(mapping) == count
        assert [int(r[order_key]) for r in mapping] == list(range(1, count + 1))
        for r in mapping:
            ident = r['sound_id']
            assert spoken(r['production_prompt']) == spoken(by_id[ident]['prompt']), ident
            rows.append(dict(id=ident, group=group, group_order=int(r[order_key]),
                catalog_order=int(by_id[ident]['order']), expected_text=spoken(r['production_prompt']),
                production_prompt=r['production_prompt']))
        folder = BASE / 'gameplay/batches' / group
        manifest = json.loads((folder / 'manifest.json').read_text())
        if group.startswith('E001'):
            assert manifest['expected_ordered_sound_ids'] == [r['sound_id'] for r in mapping]
            items = [dict(part=1, stored_filename=manifest['stored_filename'], sha256=manifest['audio_sha256'])]
        else:
            items = manifest['files']
        for item in items:
            path = folder / item['stored_filename']
            assert sha(path) == item['sha256'], path
            sources.append(dict(key=f'{group}_part{item["part"]:02d}', group=group,
                part=item['part'], path=str(path), sha256=sha(path)))
        for ref in manifest['reference_files']:
            path = BASE / (ref.get('target') or ref['project_relative_path'])
            assert sha(path) == ref['sha256'], path
    assert len(rows) == len({r['id'] for r in rows}) == 207
    assert {r['id'] for r in rows} == set(by_id)
    return rows, sources


def inventory():
    rows, sources = load_inputs()
    result = []
    for source in sources:
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                                   '-show_format', '-of', 'json', source['path']]))
        stream = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
        pcm = decode(source['path'])
        result.append(dict(**source, bytes=Path(source['path']).stat().st_size,
            codec=stream['codec_name'], sample_rate=int(stream['sample_rate']), channels=stream['channels'],
            container_duration=float(probe['format']['duration']), decoded_duration=len(pcm)/RATE,
            decoded_samples=len(pcm)))
    write_tsv(QA / 'source_inventory.tsv', result)
    write_tsv(QA / 'expected_207.tsv', rows)
    print('Verified: four MP3 hashes; 10 + 197 disjoint IDs; 207 reference/catalog texts.', flush=True)


def decode(path):
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
        '-vn', '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-c:a', 'pcm_s16le', '-'])
    return np.frombuffer(raw, dtype='<i2')


def check_protected():
    snapshot = tsv(QA / 'input_snapshot.tsv')
    for r in snapshot:
        if not Path(r['path']).is_file() or sha(r['path']) != r['sha256']:
            raise RuntimeError('Protected input changed: ' + r['path'])
    return len(snapshot)


def source_asr():
    from faster_whisper import WhisperModel
    check_protected()
    _, sources = load_inputs()
    model = None
    for source in sources:
        path = QA / 'source_asr' / (source['key'] + '.json')
        if path.exists():
            data = json.loads(path.read_text())
            assert data['source_sha256'] == source['sha256']
            print('Cached:', source['key'], flush=True)
            continue
        if model is None:
            model = WhisperModel('medium', device='cpu', compute_type='int8', cpu_threads=6, local_files_only=True)
        data = dict(source=source['path'], source_sha256=source['sha256'], model='medium',
            language='tr', device='cpu', compute_type='int8', initial_prompt=None, segments=[], words=[])
        segments, info = model.transcribe(source['path'], language='tr', task='transcribe',
            beam_size=5, condition_on_previous_text=False, vad_filter=False, word_timestamps=True)
        tick = time.monotonic()
        for s in segments:
            data['segments'].append(dict(start=s.start, end=s.end, text=s.text.strip()))
            data['words'].extend(dict(start=w.start, end=w.end, text=w.word.strip(), probability=w.probability)
                                for w in (s.words or []))
            if time.monotonic()-tick > 25:
                print(source['key'], f'{s.end:.1f}/{info.duration:.1f} s', s.text.strip()[:100], flush=True)
                save_json(path.with_suffix('.partial.json'), data)
                tick = time.monotonic()
        data['text'] = ' '.join(s['text'] for s in data['segments'])
        save_json(path, data)
        # Leave any partial checkpoint as diagnostic evidence; final JSON is authoritative.
        path.with_suffix('.txt').write_text('\n'.join(
            f'[{s["start"]:.3f}–{s["end"]:.3f}] {s["text"]}' for s in data['segments'])+'\n')
        print('Completed', source['key'], len(data['words']), 'words', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inventory', 'source_asr'])
    args = parser.parse_args()
    globals()[args.mode]()
