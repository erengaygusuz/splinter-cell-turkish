#!/usr/bin/env python3
"""Source-preserving Fisher VD001 gameplay segmentation and QA. Never approves audio."""
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

BASE = Path('dubbing/characters/sam_fisher/gameplay/voice_versions/VD001')
QA = BASE / 'qa/r001_v1_20261021'
RATE = 44100
DEVICE = 'cpu'
COMPUTE = 'int8'


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
    parent = BASE.parents[2]
    catalog = tsv(parent / 'gameplay/catalog.tsv')
    expected = tsv(BASE / 'production_source/full_201_expected.tsv')
    assert len(expected) == len({r['gameplay_id'] for r in expected}) == 201
    assert {r['id'] for r in catalog} == {r['gameplay_id'] for r in expected}
    by_id = {r['id']: r for r in catalog}
    for r in expected:
        assert r['expected_prompt'] == by_id[r['gameplay_id']]['prompt']
        assert int(r['catalog_order']) == int(by_id[r['gameplay_id']]['order'])
    reference = [s.strip() for s in (parent / 'reference/sam_fisher_201_sade_v2.txt').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    assert reference == [r['expected_prompt'] for r in expected]
    manifest = json.loads((BASE / 'batches/R001_20261021/source_manifest.json').read_text())
    rows = []
    for group, name, order, count, manifest_key in [
        ('R001_20261021', 'remaining_190_id_order.tsv', 'global_sequence', 190, 'r001_190_id_order'),
        ('E001_20261021', 'test_11_id_order.tsv', 'test_sequence', 11, 'e001_11_id_order')]:
        mapping = tsv(BASE / 'production_source' / name)
        assert len(mapping) == count
        assert [int(r[order]) for r in mapping] == list(range(1,count+1))
        assert [r['gameplay_id'] for r in mapping] == manifest[manifest_key]
        for r in mapping:
            ident = r['gameplay_id']
            assert r['prompt'] == by_id[ident]['prompt']
            authority = next(e for e in expected if e['gameplay_id'] == ident)
            assert authority['production_set'].startswith(group[:4])
            assert int(authority['production_sequence']) == int(r[order])
            rows.append(dict(id=ident, group=group, group_order=int(r[order]),
                catalog_order=int(r['catalog_order']), expected_text=spoken(r['prompt']), production_prompt=r['prompt']))
    assert len(rows) == len({r['id'] for r in rows}) == 201
    sources = []
    for item in manifest['r001_audio']:
        path = BASE / 'batches/R001_20261021' / item['archive_filename']
        assert sha(path) == item['sha256'] and path.stat().st_size == item['bytes']
        sources.append(dict(key=f'R001_20261021_part{item["part"]:02d}', group='R001_20261021',
            part=item['part'], path=str(path), sha256=sha(path)))
    assert len(sources) == 2
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
    write_tsv(QA / 'expected_201.tsv', rows)
    print('Verified: two VD001 MP3 hashes; 190 + 11 disjoint IDs; 201 reference/catalog texts.', flush=True)


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
            model = WhisperModel('medium', device=DEVICE, compute_type=COMPUTE, cpu_threads=6, local_files_only=True)
        data = dict(source=source['path'], source_sha256=source['sha256'], model='medium',
            language='tr', device=DEVICE, compute_type=COMPUTE, initial_prompt=None, segments=[], words=[])
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


def match_words(rows, words):
    """Ordered character anchors, with raw ASR times retained as uncertain evidence.

    Levenshtein global alignment avoids greedy matching of common words across
    distant lines. Unknown words enclosed by anchors of one line join that line;
    words between different lines remain explicitly unassigned.
    """
    from rapidfuzz.distance import Levenshtein
    expected, owners, recognized, word_owner = '', [], '', []
    for row in rows:
        chars = norm(row['expected_text']).replace(' ', '')
        expected += chars
        owners.extend([row['id']] * len(chars))
    for i, word in enumerate(words):
        chars = norm(word['text']).replace(' ', '')
        recognized += chars
        word_owner.extend([i] * len(chars))
    votes = defaultdict(Counter)
    for op in Levenshtein.opcodes(expected, recognized):
        if op.tag == 'equal':
            for k in range(op.src_end-op.src_start):
                votes[word_owner[op.dest_start+k]][owners[op.src_start+k]] += 1
    assigned = {}
    for index, counter in votes.items():
        ident, count = counter.most_common(1)[0]
        assigned[index] = (ident, count, 'CHARACTER_ANCHOR')
    known = sorted(assigned)
    for left, right in zip(known, known[1:]):
        if assigned[left][0] == assigned[right][0]:
            for i in range(left+1, right):
                assigned.setdefault(i, (assigned[left][0], 0, 'ENCLOSED_ASR_WORD'))
    output = defaultdict(list)
    unassigned = []
    rank = {r['id']: i for i, r in enumerate(rows)}
    previous = -1
    for i, word in enumerate(words):
        if i not in assigned:
            unassigned.append(dict(word, word_index=i))
            continue
        ident, count, method = assigned[i]
        if rank[ident] < previous:
            raise RuntimeError(f'Non-monotonic assignment at {ident}: {word}')
        previous = rank[ident]
        output[ident].append(dict(word, word_index=i, matched_characters=count, method=method))
    return output, unassigned


def quiet_runs(pcm, threshold=-55, min_seconds=.035):
    hop = 220
    x = pcm[:len(pcm)//hop*hop].astype(float).reshape(-1, hop) / 32768
    quiet = np.sqrt(np.mean(x*x, axis=1)) < 10**(threshold/20)
    changes = np.diff(np.r_[False, quiet, False].astype(int))
    return [(a*hop/RATE, b*hop/RATE) for a, b in
            zip(np.where(changes == 1)[0], np.where(changes == -1)[0])
            if (b-a)*hop/RATE >= min_seconds]


def pick_boundary(left_end, right_start, runs):
    target = (left_end + right_start)/2
    # Whisper boundaries can lag real speech offsets. Search near the last/first
    # word, not across the duration of an entire utterance.
    lo, hi = min(left_end, right_start)-.35, max(left_end, right_start)+.15
    choices = [(max(a, lo), min(b, hi)) for a, b in runs if min(b, hi)-max(a, lo) >= .035]
    if not choices:
        return dict(time=target, quiet_start='', quiet_end='', method='NO_QUIET_BOUNDARY_NEEDS_REVIEW')
    a, b = min(choices, key=lambda r: abs((r[0]+r[1])/2-target)-min(.1, r[1]-r[0])*.2)
    return dict(time=(a+b)/2, quiet_start=a, quiet_end=b, method='ASR_BRACKET_AND_QUIET_RMS')


def align(group_filter=None):
    check_protected()
    expected, sources = load_inputs()
    evidence, unmatched, plans, boundary_rows = [], [], [], []
    inventory_rows = {r['key']: r for r in tsv(QA / 'source_inventory.tsv')}
    for group in ['E001_20261021', 'R001_20261021']:
        if group_filter and not group.startswith(group_filter):
            continue
        source_group = [s for s in sources if s['group'] == group]
        if not source_group:
            print('SOURCE_AUDIO_MISSING:', group, flush=True)
            continue
        cache_paths = [QA / 'source_asr' / (s['key'] + '.json') for s in source_group]
        if not all(p.exists() for p in cache_paths):
            print('Waiting for complete source ASR:', group, flush=True)
            continue
        rows = [r for r in expected if r['group'] == group]
        words = []
        for source, path in zip(source_group, cache_paths):
            data = json.loads(path.read_text())
            assert data['source_sha256'] == source['sha256']
            words.extend(dict(w, source_key=source['key']) for w in data['words'])
        matches, unassigned = match_words(rows, words)
        unmatched.extend(dict(w, group=group) for w in unassigned)
        group_plan = []
        for row in rows:
            match = matches[row['id']]
            for word in match:
                evidence.append(dict(id=row['id'], group=group, **word))
            keys = list(dict.fromkeys(w['source_key'] for w in match))
            result = dict(**row, source_key=keys[0] if len(keys) == 1 else '',
                matched_source_keys=keys, source_asr_text=' '.join(w['text'] for w in match),
                alignment_match=score(row['expected_text'], ' '.join(w['text'] for w in match)),
                first_word_start=match[0]['start'] if match else None,
                last_word_end=match[-1]['end'] if match else None,
                first_word=match[0]['text'] if match else '', last_word=match[-1]['text'] if match else '',
                status='ALIGNED_CANDIDATE' if len(keys) == 1 else 'MISSING_OR_MULTI_SOURCE_REVIEW')
            group_plan.append(result)
        for source in source_group:
            subset = [r for r in group_plan if r['source_key'] == source['key']]
            if not subset:
                continue
            pcm = decode(source['path'])
            runs = quiet_runs(pcm)
            boundaries = [dict(time=0., quiet_start=0., quiet_end=0., method='SOURCE_START')]
            for left, right in zip(subset, subset[1:]):
                boundary = pick_boundary(left['last_word_end'], right['first_word_start'], runs)
                boundaries.append(boundary)
                boundary_rows.append(dict(source_key=source['key'], left_id=left['id'], right_id=right['id'],
                    left_last_word=left['last_word'], right_first_word=right['first_word'],
                    left_asr_end=left['last_word_end'], right_asr_start=right['first_word_start'], **boundary))
            boundaries.append(dict(time=len(pcm)/RATE, quiet_start=len(pcm)/RATE,
                                   quiet_end=len(pcm)/RATE, method='SOURCE_END'))
            for i, row in enumerate(subset):
                start, end = boundaries[i], boundaries[i+1]
                row.update(start_sample=round(start['time']*RATE), end_sample=round(end['time']*RATE),
                    start_sec=round(start['time']*RATE)/RATE, end_sec=round(end['time']*RATE)/RATE,
                    source_path=source['path'], source_sha256=source['sha256'],
                    start_method=start['method'], end_method=end['method'])
                if row['start_sample'] >= row['end_sample']:
                    row['status'] = 'NON_MONOTONIC_CUT_REVIEW'
                if 'NEEDS_REVIEW' in start['method']+end['method']:
                    row['status'] = 'BOUNDARY_REVIEW'
                if row['alignment_match'] < 75:
                    row['status'] = 'ALIGNMENT_REVIEW'
            print(source['key'], len(subset), 'IDs:', subset[0]['id'], 'to', subset[-1]['id'], flush=True)
        save_json(QA / ('alignment_' + group + '.json'), group_plan)
        plans.extend(group_plan)
    if evidence:
        suffix = '_' + group_filter if group_filter else ''
        write_tsv(QA / ('word_alignment' + suffix + '.tsv'), evidence)
        save_json(QA / ('unassigned_words' + suffix + '.json'), unmatched)
        write_tsv(QA / ('boundary_proposals' + suffix + '.tsv'), boundary_rows)
        print('Alignment states:', dict(Counter(r['status'] for r in plans)), flush=True)


def save_cut(path, pcm, start, end):
    if not 0 <= start < end <= len(pcm):
        raise ValueError(f'Invalid interval {start}..{end} for {path}')
    raw = pcm[start:end].tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with wave.open(str(path)) as wav:
            assert wav.getparams()[:3] == (1, 2, RATE)
            assert wav.readframes(wav.getnframes()) == raw, f'Refusing changed existing WAV: {path}'
        return
    with path.open('xb') as f:
        with wave.open(f, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(raw)


def cut(group_filter=None):
    check_protected()
    expected, sources = load_inputs()
    pcm = {}
    for group in ['E001_20261021', 'R001_20261021']:
        if group_filter and not group.startswith(group_filter):
            continue
        path = QA / ('alignment_' + group + '.json')
        if not path.exists():
            continue
        rows = json.loads(path.read_text())
        manifests = []
        for row in rows:
            if not row.get('source_key') or row['status'] == 'NON_MONOTONIC_CUT_REVIEW':
                print('No guessed cut:', row['id'], row['status'], flush=True)
                continue
            key = row['source_key']
            if key not in pcm:
                pcm[key] = decode(row['source_path'])
            wav = BASE / 'review_pending' / group / (row['id'] + '_v01.wav')
            save_cut(wav, pcm[key], row['start_sample'], row['end_sample'])
            manifests.append(dict(id=row['id'], group=group, group_order=row['group_order'],
                source_key=key, source_mp3=row['source_path'], source_sha256=row['source_sha256'],
                start_sample=row['start_sample'], end_sample_exclusive=row['end_sample'],
                start_sec=row['start_sec'], end_sec=row['end_sec'],
                duration_sec=(row['end_sample']-row['start_sample'])/RATE,
                expected_text=row['expected_text'], version='v01', wav_path=str(wav),
                sha256=sha(wav), alignment_match=row['alignment_match'], alignment_status=row['status'],
                start_method=row['start_method'], end_method=row['end_method']))
        write_tsv(QA / ('cuts_' + group + '.tsv'), manifests)
        print('WAV candidates:', group, len(manifests), flush=True)


def clip_asr(group_filter=None):
    from faster_whisper import WhisperModel
    check_protected()
    model = None
    for group in ['E001_20261021', 'R001_20261021']:
        if group_filter and not group.startswith(group_filter):
            continue
        manifest = QA / ('cuts_' + group + '.tsv')
        if not manifest.exists():
            continue
        path = QA / ('clip_asr_' + group + '.json')
        cache = json.loads(path.read_text()) if path.exists() else {}
        rows = tsv(manifest)
        for index, row in enumerate(rows, 1):
            ident, wav_path = row['id'], row['wav_path']
            digest = sha(wav_path)
            if cache.get(ident, {}).get('sha256') == digest:
                continue
            if model is None:
                model = WhisperModel('medium', device=DEVICE, compute_type=COMPUTE, cpu_threads=6, local_files_only=True)
            segments, _ = model.transcribe(wav_path, language='tr', beam_size=5,
                condition_on_previous_text=False, vad_filter=False, word_timestamps=True)
            segments = list(segments)
            text = ' '.join(s.text.strip() for s in segments)
            cache[ident] = dict(sha256=digest, model='medium', device=DEVICE, compute_type=COMPUTE,
                initial_prompt=None, text=text,
                match=score(row['expected_text'], text),
                words=[dict(start=w.start, end=w.end, text=w.word, probability=w.probability)
                       for s in segments for w in (s.words or [])])
            save_json(path, cache)
            print(f'{group} {index}/{len(rows)} {ident} {cache[ident]["match"]}% {text[:120]}', flush=True)


def db(samples):
    values = np.asarray(samples, dtype=float)/32768
    return round(20*np.log10(max(1e-9, np.sqrt(np.mean(values**2)))), 2) if len(values) else -180.


def acoustic_metrics(pcm, start, end):
    quiet = []
    for position, direction in [(start, 1), (end, -1)]:
        length = 0
        for offset in range(0, min(end-start, RATE), 220):
            a, b = ((position+offset, min(end, position+offset+220)) if direction == 1
                    else (max(start, position-offset-220), position-offset))
            if db(pcm[a:b]) >= -55:
                break
            length += b-a
        quiet.append(round(length*1000/RATE, 1))
    width = round(.015*RATE)
    return dict(start_edge_dbfs=db(pcm[max(0, start-width):start+width]),
        end_edge_dbfs=db(pcm[max(0, end-width):end+width]),
        leading_quiet_ms=quiet[0], trailing_quiet_ms=quiet[1],
        clipped_samples=int(np.count_nonzero(np.abs(pcm[start:end].astype(int)) >= 32767)))


def selected_cuts():
    rows = []
    for group in ['E001_20261021', 'R001_20261021']:
        path = QA / ('cuts_' + group + '.tsv')
        if path.exists():
            rows.extend(tsv(path))
    revisions = QA / 'revision_manifest.tsv'
    if revisions.exists():
        by_id = {r['id']: r for r in rows}
        for row in tsv(revisions):
            by_id[row['id']] = row
        rows = list(by_id.values())
    return rows


def acoustic():
    check_protected()
    _, sources = load_inputs()
    pcm = {s['key']: decode(s['path']) for s in sources}
    rows = []
    for cut in selected_cuts():
        key = cut['source_key']
        a, b = int(cut['start_sample']), int(cut['end_sample_exclusive'])
        with wave.open(cut['wav_path']) as wav:
            assert wav.getparams()[:3] == (1, 2, RATE)
            raw = wav.readframes(wav.getnframes())
        assert raw == pcm[key][a:b].tobytes(), cut['id']
        ev = acoustic_metrics(pcm[key], a, b)
        flags = []
        if max(ev['start_edge_dbfs'], ev['end_edge_dbfs']) > -45:
            flags.append('ACTIVE_EDGE')
        if min(ev['leading_quiet_ms'], ev['trailing_quiet_ms']) < 30:
            flags.append('SHORT_EDGE_MARGIN')
        if ev['clipped_samples']:
            flags.append('CLIPPED_SOURCE_SAMPLES')
        rows.append(dict(id=cut['id'], version=cut['version'], source_key=key,
            start_sec=a/RATE, end_sec=b/RATE, flags=','.join(flags), source_pcm_identical=True, **ev))
    write_tsv(QA / 'acoustic_screen.tsv', rows)
    print('Acoustic screen:', len(rows), 'rows;', sum(bool(r['flags']) for r in rows), 'flagged', flush=True)
    for r in rows:
        if r['flags']:
            print(r, flush=True)


def revise():
    check_protected()
    plan = json.loads((QA / 'revision_plan.json').read_text())
    original = {}
    for group in ['E001_20261021', 'R001_20261021']:
        original.update({r['id']: r for r in tsv(QA / ('cuts_'+group+'.tsv'))})
    pcm, manifest = {}, []
    for ident, revision in plan.items():
        row = dict(original[ident])
        if row['source_key'] not in pcm:
            pcm[row['source_key']] = decode(row['source_mp3'])
        a, b = round(revision['start_sec']*RATE), round(revision['end_sec']*RATE)
        path = BASE / 'review_pending' / row['group'] / (ident+'_v02.wav')
        save_cut(path, pcm[row['source_key']], a, b)
        row.update(start_sample=a, end_sample_exclusive=b, start_sec=a/RATE, end_sec=b/RATE,
            duration_sec=(b-a)/RATE, version='v02', wav_path=str(path), sha256=sha(path),
            start_method='REVIEWED_WAVEFORM_BOUNDARY', end_method='REVIEWED_WAVEFORM_BOUNDARY',
            revision_reason=revision['rationale'])
        manifest.append(row)
    write_tsv(QA / 'revision_manifest.tsv', manifest)
    print('New immutable revisions:', len(manifest), flush=True)


def verify_revisions():
    from faster_whisper import WhisperModel
    check_protected()
    rows = tsv(QA / 'revision_manifest.tsv')
    path = QA / 'revision_asr.json'
    cache = json.loads(path.read_text()) if path.exists() else {}
    model = None
    for row in rows:
        if cache.get(row['id'], {}).get('sha256') == sha(row['wav_path']):
            continue
        if model is None:
            model = WhisperModel('medium', device=DEVICE, compute_type=COMPUTE, local_files_only=True, cpu_threads=6)
        segments, _ = model.transcribe(row['wav_path'], language='tr', beam_size=5,
            word_timestamps=True, condition_on_previous_text=False, vad_filter=False)
        segments = list(segments)
        text = ' '.join(s.text.strip() for s in segments)
        cache[row['id']] = dict(sha256=sha(row['wav_path']), model='medium', device=DEVICE,
            compute_type=COMPUTE, initial_prompt=None, text=text, match=score(row['expected_text'], text),
            words=[dict(start=w.start, end=w.end, text=w.word) for s in segments for w in (s.words or [])])
        save_json(path, cache)
        print(row['id'], cache[row['id']]['match'], text, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inventory','source_asr','align','cut','clip_asr','acoustic','revise','verify_revisions'])
    parser.add_argument('--group', choices=['E001','R001'])
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    parser.add_argument('--compute-type', default='int8')
    args=parser.parse_args()
    DEVICE, COMPUTE = args.device, args.compute_type
    if args.mode in ['align','cut','clip_asr']: globals()[args.mode](args.group)
    else: globals()[args.mode]()
