#!/usr/bin/env python3
"""Non-destructive Fisher source cuts and evidence reports; never approves audio.

Run from the project root. Requires ffmpeg and numpy. The transcribe subcommand
also requires faster-whisper. Existing archive tools/data are read-only inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from difflib import SequenceMatcher
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
import wave

import numpy as np

BASE = Path('dubbing/characters/sam_fisher')
OLD = BASE / 'gameplay/qa/whisper_medium_cpu_int8'
OUT = BASE / 'gameplay/qa/fisher_boundary_review_v3_20261021'
RATE = 44100


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_tsv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_tsv(path, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def norm(text):
    text = unicodedata.normalize('NFKD', text.casefold().replace('ı', 'i'))
    return ' '.join(re.findall('[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c))))


def similarity(a, b):
    # Same normalized character-ratio metric used in the existing QA environment.
    try:
        from rapidfuzz.fuzz import ratio
        return round(ratio(norm(a), norm(b)), 1)
    except ImportError:
        return round(100 * SequenceMatcher(None, norm(a), norm(b)).ratio(), 1)


def check_inputs():
    rows = read_tsv(OUT / 'input_snapshot.tsv')
    errors = [r['path'] for r in rows if not Path(r['path']).is_file()
              or sha(r['path']) != r['sha256']]
    if errors:
        raise RuntimeError('Protected input changed: ' + ', '.join(errors))
    return len(rows)


def load_archive():
    catalog = read_tsv(BASE / 'gameplay/catalog.tsv')
    assert len(catalog) == len({r['id'] for r in catalog}) == 201
    reference = [s.strip() for s in (BASE / 'reference/sam_fisher_201_sade_v2.txt')
                 .read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    assert reference == [r['prompt'] for r in catalog], 'Catalog differs from reference text'
    cats = {r['id']: r for r in catalog}
    clips, sources = [], {}
    for path in sorted((BASE / 'gameplay/batches').glob('*/batch_info.json')):
        info = json.loads(path.read_text())
        batch = path.parent.name
        mp3 = path.parent / (info.get('source_file') or info['source_filename'])
        assert sha(mp3) == info['source_sha256'], mp3
        sources[batch] = mp3
        for row in read_tsv(path.parent / 'cut_manifest.tsv'):
            ident = row.get('id') or row['orijinal_id']
            pilot = batch.startswith('B001')
            clips.append(dict(id=ident, batch=batch, order=int(cats[ident]['order']),
                expected_text=re.sub(r'\[[^\]]+\]', '', cats[ident]['prompt']).strip(),
                start=float(row['kaynak_baslangic_sn'] if pilot else row['start_sec']),
                end=float(row['kaynak_bitis_sn'] if pilot else row['end_sec']),
                path=str(BASE / ('gameplay/takes/' + ident + '_v01.wav' if pilot
                                 else row['candidate_relative_path']))))
    assert len(clips) == len({c['id'] for c in clips}) == 201
    assert Counter(c['batch'][:4] for c in clips) == {'B001': 10, 'B002': 167, 'B003': 24}
    return clips, sources


def decode(path):
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
        '-vn', '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-c:a', 'pcm_s16le', '-'])
    return np.frombuffer(raw, dtype='<i2')


def cut_samples(pcm, start, end):
    a, b = round(start * RATE), round(end * RATE)
    if not 0 <= a < b <= len(pcm):
        raise ValueError(f'Invalid source interval {start}..{end}')
    return a, b, pcm[a:b].tobytes()


def save_cut(path, raw):
    """Refuse overwrites, including a previous candidate from this run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as file:
        with wave.open(file, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(raw)


def build():
    check_inputs()
    clips, sources = load_archive()
    by_id = {c['id']: c for c in clips}
    plan = json.loads((OUT / 'cut_plan.json').read_text())
    pcm = {batch: decode(source) for batch, source in sources.items()}
    rows = []
    for ident, cut in plan.items():
        c = by_id[ident]
        a, b, raw = cut_samples(pcm[c['batch']], cut['start'], cut['end'])
        path = OUT / 'cuts' / c['batch'] / (ident + '_v03_candidate.wav')
        if path.exists():
            with wave.open(str(path)) as wav:
                assert wav.getparams()[:3] == (1, 2, RATE)
                assert wav.readframes(wav.getnframes()) == raw, path
        else:
            save_cut(path, raw)
        rows.append(dict(id=ident, batch=c['batch'], source_mp3=str(sources[c['batch']]),
            source_sha256=sha(sources[c['batch']]), start_sample=a, end_sample_exclusive=b,
            start_sec=a / RATE, end_sec=b / RATE, sample_rate=RATE,
            selected_path=str(path), sha256=sha(path), rationale=cut['rationale']))
    write_tsv(OUT / 'new_cut_manifest.tsv', rows)
    print(f'{len(rows)} source-exact PCM cuts; {check_inputs()} inputs unchanged.', flush=True)


def transcribe():
    from faster_whisper import WhisperModel
    path = OUT / 'new_clip_asr_medium.json'
    cache = json.loads(path.read_text()) if path.exists() else {}
    model = None
    for row in read_tsv(OUT / 'new_cut_manifest.tsv'):
        ident, wav = row['id'], row['selected_path']
        digest = sha(wav)
        if cache.get(ident, {}).get('sha256') == digest:
            continue
        if model is None:
            model = WhisperModel('medium', device='cpu', compute_type='int8',
                                 cpu_threads=6, local_files_only=True)
        segments, _ = model.transcribe(wav, language='tr', beam_size=5,
            word_timestamps=True, condition_on_previous_text=False, vad_filter=False)
        segments = list(segments)
        cache[ident] = dict(sha256=digest, model='medium', initial_prompt=None,
            text=' '.join(s.text.strip() for s in segments),
            words=[dict(start=w.start, end=w.end, text=w.word)
                   for s in segments for w in (s.words or [])])
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n')
        temp.replace(path)
        print(ident, cache[ident]['text'], flush=True)


def context():
    """Optional independent context check; never supply the expected text as a prompt."""
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    check_inputs()
    _, sources = load_archive()
    source = sources['B002_20261021']
    path = OUT / 'context_asr_large_v3.json'
    if path.exists():
        data = json.loads(path.read_text())
        assert data['source_sha256'] == sha(source)
        assert len(data['contexts']) == 4
        print('Verified existing contextual ASR cache; no re-transcription.')
        return
    model = WhisperModel('large-v3', device='cpu', compute_type='int8',
                         cpu_threads=6, local_files_only=True)
    audio = decode_audio(str(source))
    data = dict(model='large-v3', device='cpu', compute_type='int8',
                initial_prompt=None, source_sha256=sha(source), contexts=[])
    for start, end in [(19, 28), (140.7, 153.2), (155.6, 168.3), (237.9, 241.6)]:
        segments, _ = model.transcribe(audio[int(start*16000):int(end*16000)],
            language='tr', beam_size=5, word_timestamps=True,
            condition_on_previous_text=False, vad_filter=False)
        segments = list(segments)
        data['contexts'].append(dict(source_batch='B002_20261021', start=start, end=end,
            text=' '.join(s.text for s in segments), words=[dict(start=round(w.start+start, 3),
            end=round(w.end+start, 3), text=w.word) for s in segments for w in (s.words or [])]))
        print(start, end, data['contexts'][-1]['text'], flush=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def aligned_words(clips, full):
    """Character anchors tolerate merged words and names. These are ASR evidence,
    not forced alignment or a substitute for listening. Retain every raw word.
    """
    output = defaultdict(list)
    for batch, entry in full.items():
        expected, owners, recognized, word_owners = '', [], '', []
        for c in (c for c in clips if c['batch'] == batch):
            chars = norm(c['expected_text']).replace(' ', '')
            expected += chars
            owners.extend([c['id']] * len(chars))
        words = entry['result']['words']
        for i, w in enumerate(words):
            chars = norm(w['text']).replace(' ', '')
            recognized += chars
            word_owners.extend([i] * len(chars))
        votes = defaultdict(Counter)
        for a, b, n in SequenceMatcher(None, expected, recognized, autojunk=False).get_matching_blocks():
            for k in range(n):
                votes[word_owners[b + k]][owners[a + k]] += 1
        for i, vote in votes.items():
            owner, count = vote.most_common(1)[0]
            output[owner].append(dict(words[i], matched_characters=count,
                                     assignment='ASR_CHARACTER_ANCHOR_NOT_VERIFIED'))
    return output


def db(samples):
    values = np.asarray(samples, dtype=float) / 32768
    return round(20 * np.log10(max(1e-9, np.sqrt(np.mean(values ** 2)))), 2) if len(values) else -180.0


def edge_metrics(pcm, start, end):
    a, b, _ = cut_samples(pcm, start, end)
    hop = 220  # approx. 5 ms, evaluated at original decoded sample rate
    quiet = []
    for pos, direction in [(a, 1), (b, -1)]:
        length = 0
        for offset in range(0, min(b - a, RATE), hop):
            lo, hi = ((pos + offset, min(b, pos + offset + hop)) if direction == 1
                      else (max(a, pos - offset - hop), pos - offset))
            if db(pcm[lo:hi]) >= -55:
                break
            length += hi - lo
        quiet.append(round(length * 1000 / RATE, 1))
    window = round(.015 * RATE)
    return dict(start_edge_dbfs=db(pcm[max(0, a-window):a+window]),
                end_edge_dbfs=db(pcm[max(0, b-window):b+window]),
                leading_quiet_ms=quiet[0], trailing_quiet_ms=quiet[1])


def wav_metrics(path, pcm, start):
    with wave.open(str(path)) as wav:
        assert wav.getparams()[:3] == (1, 2, RATE), path
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
    a = round(start * RATE)
    errors = []
    # Legacy manifests round time to 5 decimals, and ffmpeg seek may round by one sample.
    for shift in range(-2, 3):
        lo = a + shift
        hi = lo + len(samples)
        if lo >= 0 and hi <= len(pcm):
            error = np.sqrt(np.mean((samples.astype(float) - pcm[lo:hi]) ** 2))
            errors.append((float(error), shift))
    error, shift = min(errors)
    return dict(wav_frames=len(samples), wav_peak=float(np.max(np.abs(samples.astype(float))) / 32768),
        clipped_samples=int(np.count_nonzero(np.abs(samples.astype(int)) >= 32767)),
        wav_source_pcm_rms_error=round(error, 6), wav_source_offset_samples=shift,
        wav_first_20ms_dbfs=db(samples[:882]), wav_last_20ms_dbfs=db(samples[-882:]))


def report():
    protected = check_inputs()
    clips, sources = load_archive()
    pcm = {batch: decode(path) for batch, path in sources.items()}
    full = json.loads((OLD / 'full_mp3_cache.json').read_text())
    for batch, source in sources.items():
        assert full[batch]['sha256'] == sha(source)
    context_data = json.loads((OUT / 'context_asr_large_v3.json').read_text())
    assert context_data['source_sha256'] == sha(sources['B002_20261021'])
    old_cache = json.loads((OLD / 'clip_cache.json').read_text())
    new_cache = json.loads((OUT / 'new_clip_asr_medium.json').read_text())
    cuts = {r['id']: r for r in read_tsv(OUT / 'new_cut_manifest.tsv')}
    notes = json.loads((OUT / 'review_notes.json').read_text())
    assigned = aligned_words(clips, full)
    decisions, word_rows, candidates = [], [], []
    v2 = {r['id']: r for r in read_tsv(OLD / 'repair_candidates_v2/aday_kesim_whisper_karsilastirma.tsv')}
    v2_cache = json.loads((OLD / 'repair_candidates_v2/candidate_transcript_cache.json').read_text())
    for c in sorted(clips, key=lambda c: c['order']):
        ident = c['id']
        assert old_cache[ident]['sha256'] == sha(c['path'])
        alternatives = [('v01', c['path'], c['start'], c['end'], old_cache[ident]['result']['text'])]
        if ident in v2 and v2[ident]['aday_wav']:
            r = v2[ident]
            assert v2_cache[ident]['sha256'] == sha(r['aday_wav'])
            alternatives.append(('v02_candidate', r['aday_wav'], float(r['aday_bas_sn']),
                                 float(r['aday_bit_sn']), v2_cache[ident]['text']))
        if ident in cuts:
            r = cuts[ident]
            assert new_cache[ident]['sha256'] == sha(r['selected_path'])
            alternatives.append(('v03_candidate', r['selected_path'], float(r['start_sec']),
                                 float(r['end_sec']), new_cache[ident]['text']))
        chosen = alternatives[-1] if ident in cuts else alternatives[0]
        for version, path, start, end, text in alternatives:
            candidates.append(dict(id=ident, version=version, path=path, source_start=start,
                source_end=end, asr_match=similarity(c['expected_text'], text), asr_text=text,
                selected=version == chosen[0], sha256=sha(path),
                **edge_metrics(pcm[c['batch']], start, end),
                **wav_metrics(path, pcm[c['batch']], start)))
        version, path, start, end, text = chosen
        ev = edge_metrics(pcm[c['batch']], start, end)
        extra = notes.get(ident, {})
        priority = extra.get('priority', 'HIGH' if c['batch'].startswith('B001')
                             or similarity(c['expected_text'], text) < 95 else 'NORMAL')
        # A quiet edge excludes a click at the cut, not a wrong utterance.
        status = 'NEEDS_LISTEN'
        if max(ev['start_edge_dbfs'], ev['end_edge_dbfs']) > -45:
            status = 'NEEDS_CUT'
        words = assigned[ident]
        for w in words:
            midpoint = (w['start'] + w['end']) / 2
            word_rows.append(dict(id=ident, batch=c['batch'], source_start=w['start'],
                source_end=w['end'], recognized_word=w['text'],
                midpoint_inside_selected=start <= midpoint <= end,
                matched_characters=w['matched_characters'], evidence=w['assignment']))
        decisions.append(dict(id=ident, expected_text=c['expected_text'], selected_version=version,
            selected_path=path, asr_match=similarity(c['expected_text'], text), manual_listen='NOT_PERFORMED',
            status=status, notes=extra.get('notes', 'Kaynak/komşu ASR ve akustik sınır taraması; işitsel onay bekliyor.'),
            sha256=sha(path), batch=c['batch'], source_mp3=str(sources[c['batch']]),
            source_start_sec=round(start, 6), source_end_sec=round(end, 6),
            first_asr_word=words[0]['text'] if words else '', last_asr_word=words[-1]['text'] if words else '',
            first_asr_word_start=words[0]['start'] if words else '', last_asr_word_end=words[-1]['end'] if words else '',
            selected_asr_text=text, priority=priority,
            word_onset_check='ACOUSTIC_SCREEN_ONLY_NEEDS_LISTEN',
            word_offset_check='ACOUSTIC_SCREEN_ONLY_NEEDS_LISTEN',
            neighbor_spill_check='SOURCE_ORDER_AND_ASR_SCREEN_ONLY_NEEDS_LISTEN',
            reviewed_by='Codex: transcript and waveform analysis only', review_date='2026-10-21', **ev,
            **wav_metrics(path, pcm[c['batch']], start)))
    assert len(decisions) == len({r['id'] for r in decisions}) == 201
    write_tsv(OUT / 'fisher_qa_decisions.tsv', decisions)
    write_tsv(OUT / 'candidate_comparison.tsv', candidates)
    write_tsv(OUT / 'source_word_evidence.tsv', word_rows)
    write_tsv(OUT / 'text_discrepancies.tsv', [r for r in decisions if r['asr_match'] < 100])
    # Pairwise selected intervals, including silent shared source intervals.
    neighbors = []
    selected = {r['id']: r for r in decisions}
    for batch in sources:
        rows = [selected[c['id']] for c in clips if c['batch'] == batch]
        for left, right in zip(rows, rows[1:]):
            gap = right['source_start_sec'] - left['source_end_sec']
            neighbors.append(dict(batch=batch, left_id=left['id'], right_id=right['id'],
                source_gap_sec=round(gap, 6), overlap=gap < -.00003,
                left_last_asr=left['last_asr_word'], right_first_asr=right['first_asr_word'],
                left_trailing_quiet_ms=left['trailing_quiet_ms'],
                right_leading_quiet_ms=right['leading_quiet_ms'], manual_listen='NOT_PERFORMED'))
    write_tsv(OUT / 'neighbor_audit.tsv', neighbors)
    make_html(decisions)
    (OUT / 'selected_201.m3u8').write_text('#EXTM3U\n' + '\n'.join(
        f"#EXTINF:-1,{r['id']} {r['expected_text']}\n{os.path.relpath(r['selected_path'], OUT)}"
        for r in decisions) + '\n')
    print(Counter(r['status'] for r in decisions), f'; {protected} inputs unchanged.', flush=True)


def make_html(rows):
    esc = html.escape
    body = []
    for r in rows:
        source = os.path.relpath(r['source_mp3'], OUT)
        clip = os.path.relpath(r['selected_path'], OUT)
        context = f"{source}#t={max(0, r['source_start_sec']-.5):.3f},{r['source_end_sec']+.5:.3f}"
        body.append(f'<tr data-priority="{esc(r["priority"])}"><td>{r["id"]}<br>{r["selected_version"]}'
            f'<br>{r["status"]}</td><td>{esc(r["expected_text"])}<p>ASR: {esc(r["selected_asr_text"])}'
            f' ({r["asr_match"]}%)</p><small>{esc(r["notes"])}</small></td><td>'
            f'<audio controls preload="none" src="{esc(clip)}"></audio><br>'
            f'<a href="{esc(context)}">MP3: kaynak ve komşular</a><br>'
            f'{r["source_start_sec"]:.3f}–{r["source_end_sec"]:.3f} s</td></tr>')
    (OUT / 'listen_review.html').write_text('''<!doctype html><html lang="tr"><meta charset="utf-8">
<title>Sam Fisher — 201 replik dinleme kuyruğu</title><style>
body{font:16px system-ui;margin:24px;background:#15191f;color:#e5eaf1}h1{font-size:24px}
table{width:100%;border-collapse:collapse}td{padding:14px;border-bottom:1px solid #46515c;vertical-align:top}
td:first-child{white-space:nowrap}a{color:#8bd4ff}small{color:#b4c2d1}audio{width:260px}button{padding:10px}
tr[data-priority="HIGH"]{background:#372d20}p{margin:.6em 0}</style>
<h1>Sam Fisher — 201 replik dinleme kuyruğu</h1>
<p>İşitsel kontrol yapılmadı. ASR yüzdesi ve sessiz sınırlar onay değildir. Kaynak bağlantısı her iki tarafta
0,5 saniye bağlam açar. Tarayıcınız zaman bağlantısını uygulamazsa belirtilen saniyeye gidin.</p>
<p>Seçili WAV'ı ve MP3 komşularını dinleyin: ilk/son hece, eksik sözcük, komşu taşması ve telaffuz.</p>
<button onclick="document.querySelectorAll('tr[data-priority]').forEach(r=>r.hidden=r.dataset.priority!=='HIGH')">Öncelikliler</button>
<button onclick="document.querySelectorAll('tr').forEach(r=>r.hidden=false)">201 kaydın tümü</button>
<table>''' + ''.join(body) + '</table></html>', encoding='utf-8')


def verify():
    protected = check_inputs()
    clips, sources = load_archive()
    pcm = {batch: decode(path) for batch, path in sources.items()}
    rows = read_tsv(OUT / 'fisher_qa_decisions.tsv')
    assert len(rows) == len({r['id'] for r in rows}) == 201
    assert {r['id'] for r in rows} == {c['id'] for c in clips}
    for r in rows:
        assert sha(r['selected_path']) == r['sha256']
        assert r['manual_listen'] == 'NOT_PERFORMED' and r['status'] != 'APPROVED'
        assert float(r['wav_source_pcm_rms_error']) <= 5, r['id']
        assert int(r['clipped_samples']) == 0, r['id']
    cuts = read_tsv(OUT / 'new_cut_manifest.tsv')
    for r in cuts:
        with wave.open(r['selected_path']) as wav:
            assert wav.getparams()[:3] == (1, 2, RATE)
            raw = wav.readframes(wav.getnframes())
        expected = pcm[r['batch']][int(r['start_sample']):int(r['end_sample_exclusive'])].tobytes()
        assert raw == expected, r['id']
        assert sha(r['selected_path']) == r['sha256']
    neighbors = read_tsv(OUT / 'neighbor_audit.tsv')
    assert len(neighbors) == 198
    assert all(abs(float(r['source_gap_sec'])) <= 1 / RATE for r in neighbors)
    for batch, source_pcm in pcm.items():
        selected = sorted((r for r in rows if r['batch'] == batch),
                          key=lambda r: float(r['source_start_sec']))
        assert float(selected[0]['source_start_sec']) == 0
        assert abs(float(selected[-1]['source_end_sec']) - len(source_pcm)/RATE) < 1 / RATE
    snapshot = read_tsv(OUT / 'input_snapshot.tsv')
    for folder in [BASE / 'gameplay/approved', BASE / 'gameplay/game_ready']:
        before = {r['path'] for r in snapshot if Path(r['path']).is_relative_to(folder)}
        after = {str(p) for p in folder.rglob('*') if p.is_file()}
        assert before == after, folder
    result = dict(protected_files_unchanged=protected, unique_decisions=201,
        new_cuts_source_pcm_identical=len(cuts), selected_hashes_valid=201,
        selected_source_pcm_verified=201, selected_source_overlaps=0,
        catalog_reference_matches=201, contiguous_neighbor_pairs=198,
        full_source_coverage_batches=3, approved_and_game_ready_unchanged=True,
        clipped_selected_wavs=0, approvals=0, manual_listens=0)
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['build', 'transcribe', 'context', 'report', 'verify'])
    args = parser.parse_args()
    globals()[args.mode]()
