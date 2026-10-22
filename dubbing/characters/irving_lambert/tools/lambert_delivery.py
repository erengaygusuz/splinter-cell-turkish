#!/usr/bin/env python3
"""Validate and document Lambert cuts without assigning auditory approval."""
from collections import Counter
import html
import json
import os
from pathlib import Path
import wave
import zipfile

import lambert_audio_qa as qa


def read_json(name):
    return json.loads((qa.QA / name).read_text())


def validate_partitions(cuts, lengths):
    assert len(cuts) == len({r['id'] for r in cuts}) == 207
    pairs = []
    for key, length in lengths.items():
        rows = sorted((r for r in cuts if r['source_key'] == key), key=lambda r: int(r['start_sample']))
        assert rows and int(rows[0]['start_sample']) == 0, key
        assert int(rows[-1]['end_sample_exclusive']) == length, key
        for left, right in zip(rows, rows[1:]):
            assert int(left['end_sample_exclusive']) == int(right['start_sample']), (left['id'], right['id'])
            pairs.append((left, right))
    assert len(pairs) == 203
    return pairs


def main():
    protected = qa.check_protected()
    expected, sources = qa.load_inputs()
    fisher = Path('dubbing/characters/sam_fisher')
    snapshot = qa.tsv(qa.QA / 'input_snapshot.tsv')
    assert {str(p) for p in fisher.rglob('*') if p.is_file()} == {
        r['path'] for r in snapshot if Path(r['path']).is_relative_to(fisher)}
    cuts = qa.selected_cuts()
    assert {r['id'] for r in cuts} == {r['id'] for r in expected}
    originals = [r for group in ['E001', 'R001'] for r in qa.tsv(qa.QA / f'cuts_{group}_20261021.tsv')]
    revisions = qa.tsv(qa.QA / 'revision_manifest.tsv')
    pcm = {s['key']: qa.decode(s['path']) for s in sources}
    pairs = validate_partitions(cuts, {k: len(v) for k, v in pcm.items()})
    media = []
    for row in originals + revisions:
        assert qa.sha(row['wav_path']) == row['sha256'], row['wav_path']
        a, b = int(row['start_sample']), int(row['end_sample_exclusive'])
        with wave.open(row['wav_path']) as wav:
            assert wav.getparams()[:3] == (1, 2, qa.RATE)
            assert wav.getnframes() == b-a
            assert wav.readframes(wav.getnframes()) == pcm[row['source_key']][a:b].tobytes()
        media.append(dict(id=row['id'], version=row['version'], path=row['wav_path'],
                          sha256=row['sha256'], frames=b-a, source_pcm_identical=True))
    qa.write_tsv(qa.QA / 'all_wav_integrity.tsv', media)
    medium = {k: v for group in ['E001', 'R001'] for k, v in read_json(f'clip_asr_{group}_20261021.json').items()}
    assert len(medium) == 207
    for r in originals:
        assert medium[r['id']]['sha256'] == r['sha256']
    medium.update(read_json('revision_asr.json'))
    context, retry = read_json('context_asr_large_v3.json'), read_json('isolated_retry_large_v3.json')
    acoustic = {r['id']: r for r in qa.tsv(qa.QA / 'acoustic_screen.tsv')}
    alignment = {r['id']: r for g in ['E001', 'R001'] for r in read_json(f'alignment_{g}_20261021.json')}
    plot_rows = qa.tsv(qa.QA / 'boundary_plots/index.tsv')
    plot_index = {(r['left_id'], r['right_id']): r for r in plot_rows}
    review = read_json('visual_review.json')
    assert len(plot_rows) == 203 and review['interline_boundaries_viewed'] == 203
    for name, digest in review['plot_sha256'].items():
        assert qa.sha(qa.QA / 'boundary_plots' / name) == digest
    before, after = {}, {}
    neighbors = []
    for left, right in pairs:
        before[right['id']] = left['id']
        after[left['id']] = right['id']
        p = plot_index[(left['id'], right['id'])]
        assert int(p['boundary_sample']) == int(right['start_sample'])
        neighbors.append(dict(left_id=left['id'], right_id=right['id'], source_key=left['source_key'],
            cut_sec=left['end_sec'], cut_sample=left['end_sample_exclusive'], gap_samples=0, overlap_samples=0,
            left_last_asr_word=alignment[left['id']]['last_word'],
            left_last_asr_word_end=alignment[left['id']]['last_word_end'],
            right_first_asr_word=alignment[right['id']]['first_word'],
            right_first_asr_word_start=alignment[right['id']]['first_word_start'],
            visual_review='LOW_LEVEL_NOISE_REVIEW' if left['id']=='u000285' else 'INTERLINE_QUIET_REGION',
            plot='boundary_plots/'+p['page'], listened=False))
    qa.write_tsv(qa.QA / 'neighbor_boundaries.tsv', neighbors)
    rows = []
    special = {
        'u000285': 'Komşu u000287 sınırında düşük seviyeli ses/kuyruk var. Kesim ±15 ms RMS kontrolünü geçiyor; nefesin hangi repliğe ait olduğu dinlenmeli.',
        'u000287': 'Komşu u000285 sınırında düşük seviyeli ses/kuyruk var. Kesim ±15 ms RMS kontrolünü geçiyor; nefesin hangi repliğe ait olduğu dinlenmeli.',
        'u000912': 'Kaynak MP3 sıfırıncı örnekten korunuyor. İlk sözcük Tüh ASR içinde mevcut; başlangıç sessizliği 24,9 ms. Kaynağın önü kesilmedi.',
    }
    for cut in cuts:
        ident = cut['id']
        m, a, al = medium[ident], acoustic[ident], alignment[ident]
        assert m['sha256'] == cut['sha256']
        assert a['version'] == cut['version'] and a['source_pcm_identical'] == 'True'
        assert float(a['start_sec']) == float(cut['start_sec'])
        assert float(a['end_sec']) == float(cut['end_sec'])
        extra = context.get(ident, {})
        independent = retry.get(ident, {})
        if extra:
            assert extra['selected_sha256'] == cut['sha256']
        if independent:
            assert independent['sha256'] == cut['sha256']
        notes = special.get(ident, 'Kaynak sırası, bağımsız kesim transkripti ve sessiz bölge kontrolü ile eşleştirildi.')
        if cut['version'] == 'v02':
            notes += ' Paylaşılan sınır daha geniş sessizliğe taşındı; v01 korundu.'
        notes += ' Seslendirme kullanıcı tarafından doğru kabul ediliyor; ASR yazım farkları üretim hatası sayılmadı.'
        rows.append(dict(id=ident, group=cut['group'], group_order=cut['group_order'],
            expected_text=cut['expected_text'], source_mp3=cut['source_mp3'],
            start_sec=cut['start_sec'], end_sec=cut['end_sec'], duration_sec=cut['duration_sec'],
            start_sample=cut['start_sample'], end_sample_exclusive=cut['end_sample_exclusive'],
            selected_version=cut['version'], selected_wav=cut['wav_path'], sha256=cut['sha256'],
            whisper_text=m['text'], match_percent=m['match'], source_whisper_text=al['source_asr_text'],
            source_first_word=al['first_word'], source_first_word_start=al['first_word_start'],
            source_last_word=al['last_word'], source_last_word_end=al['last_word_end'],
            asr_start_margin_ms=round((al['first_word_start']-float(cut['start_sec']))*1000, 2),
            asr_end_margin_ms=round((float(cut['end_sec'])-al['last_word_end'])*1000, 2),
            previous_id=before.get(ident, ''), next_id=after.get(ident, ''),
            leading_quiet_ms=a['leading_quiet_ms'], trailing_quiet_ms=a['trailing_quiet_ms'],
            start_edge_dbfs=a['start_edge_dbfs'], end_edge_dbfs=a['end_edge_dbfs'],
            acoustic_flags=a['flags'], source_pcm_identical=True,
            technical_status='BOUNDARY_REVIEW' if ident in special else 'TECHNICAL_CUT_PASS',
            decision='NEEDS_BOUNDARY_LISTEN' if ident in special else 'NEEDS_LISTEN',
            listened=False, approved=False, voice_content='ACCEPTED_BY_USER',
            large_context_text=extra.get('selected_text', ''),
            large_isolated_text=independent.get('text', ''), notes=notes))
    qa.write_tsv(qa.QA / 'lambert_qa_decisions.tsv', rows)
    qa.write_tsv(qa.QA / 'selected_cuts.tsv', [{k: r[k] for k in originals[0]} for r in cuts])
    qa.write_tsv(qa.QA / 'boundary_listen_priority.tsv', [r for r in rows if r['id'] in special])
    source_rows = []
    for s in sources:
        group = [r for r in cuts if r['source_key'] == s['key']]
        source_rows.append(dict(source_key=s['key'], source_mp3=s['path'], count=len(group),
            first_group_order=group[0]['group_order'], last_group_order=group[-1]['group_order'],
            first_id=group[0]['id'], last_id=group[-1]['id'], decoded_duration=len(pcm[s['key']])/qa.RATE,
            first_text=group[0]['expected_text'], last_text=group[-1]['expected_text']))
    qa.write_tsv(qa.QA / 'source_boundaries.tsv', source_rows)
    old = {r['id']: r for r in originals}
    comparison = []
    for new in revisions:
        prior = old[new['id']]
        comparison.append(dict(id=new['id'], old_wav=prior['wav_path'], new_wav=new['wav_path'],
            old_start_sec=prior['start_sec'], new_start_sec=new['start_sec'],
            old_end_sec=prior['end_sec'], new_end_sec=new['end_sec'],
            old_sha256=prior['sha256'], new_sha256=new['sha256'], reason=new['revision_reason']))
    qa.write_tsv(qa.QA / 'revision_comparison.tsv', comparison)
    qa.write_tsv(qa.QA / 'rerecord_required.tsv', [], ['id', 'reason'])
    qa.save_json(qa.QA / 'validation.json', dict(protected_files_unchanged=protected,
        fisher_file_set_unchanged=True, unique_selected_ids=207, v01_files=207, v02_files=len(revisions),
        selected_versions=dict(Counter(r['version'] for r in cuts)), source_pcm_exact_wavs=len(media),
        sources=4, duration_sec=sum(len(p) for p in pcm.values())/qa.RATE,
        contiguous_neighbor_pairs=len(pairs), active_edge_flags=sum('ACTIVE_EDGE' in r['flags'] for r in acoustic.values()),
        short_edge_flags=sum('SHORT_EDGE_MARGIN' in r['flags'] for r in acoustic.values()),
        source_clipped_samples=sum(int(r['clipped_samples']) for r in acoustic.values()),
        full_source_asr_count=4, isolated_v01_asr_count=207, revised_asr_count=len(revisions),
        large_context_count=len(context), large_isolated_retry_count=len(retry),
        technical_cut_pass=sum(r['technical_status']=='TECHNICAL_CUT_PASS' for r in rows),
        priority_boundary_review=len(special), listened=0, approved=0, rerecord_required=0))
    for group, count in [('E001',10), ('R001',197)]:
        folder = qa.BASE / 'gameplay/qa' / f'{group}_20261021'
        subset = [r for r in rows if r['group'].startswith(group)]
        assert len(subset) == count
        qa.write_tsv(folder / f'{count}_replik_kontrol.tsv', subset)
        qa.write_tsv(folder / 'ses_dosyasi_sinirlari.tsv', [r for r in source_rows if r['source_key'].startswith(group)])
        (folder / 'RAPOR.md').write_text(f'# {group}: {count} Lambert repliği\n\n'
            f'{count} benzersiz ID eşleştirildi ve WAV kesimleri oluşturuldu. '
            'Seslendirmeler doğru kabul edildi; bu çalışma kesim sınırlarına odaklanır.\n\n'
            f'- [Karar tablosu]({count}_replik_kontrol.tsv)\n'
            '- [Kaynak sınırları](ses_dosyasi_sinirlari.tsv)\n'
            '- [Ayrıntılı rapor](../lambert_207_v1_20261021/lambert_qa_summary.md)\n'
            '- [Dinleme sayfası](../lambert_207_v1_20261021/listen.html)\n\n'
            'İşitsel onay verilmedi; WAV dosyaları review_pending altında.\n', encoding='utf-8')
    make_listen_page(rows)
    make_archive(cuts)
    print('Validated 207 selected cuts, 211 preserved WAV versions, 203 contiguous boundaries and', protected, 'protected files.')


def make_archive(cuts):
    path = qa.BASE / 'gameplay/review_pending/lambert_207_selected_v1_20261021.zip'
    if not path.exists():
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for cut in sorted(cuts, key=lambda r: r['id']):
                info = zipfile.ZipInfo(Path(cut['wav_path']).name, date_time=(2026,10,21,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, Path(cut['wav_path']).read_bytes())
    import hashlib
    with zipfile.ZipFile(path) as archive:
        assert len(archive.namelist()) == 207
        assert set(archive.namelist()) == {Path(r['wav_path']).name for r in cuts}
        for cut in cuts:
            assert hashlib.sha256(archive.read(Path(cut['wav_path']).name)).hexdigest() == cut['sha256']
    qa.save_json(qa.QA / 'delivery_archive.json', dict(path=str(path), sha256=qa.sha(path),
        bytes=path.stat().st_size, wav_count=207, versions={'v01':203,'v02':4},
        status='REVIEW_PENDING', included_audio_verified_against_selected_manifest=True))


def make_listen_page(rows):
    cards = []
    for r in sorted(rows, key=lambda r: (r['technical_status']!='BOUNDARY_REVIEW', r['group'], int(r['group_order']))):
        wav = os.path.relpath(r['selected_wav'], qa.QA)
        source = os.path.relpath(r['source_mp3'], qa.QA)
        a, b = max(0, float(r['start_sec'])-1), float(r['end_sec'])+1
        assert (qa.QA/wav).is_file() and (qa.QA/source).is_file()
        esc = html.escape
        cards.append(f'<article data-search="{esc(r["id"]+" "+r["expected_text"], quote=True)}">'
            f'<h2>{r["id"]} · {r["selected_version"]} · {r["technical_status"]}</h2>'
            f'<p>{esc(r["expected_text"])}</p><audio controls preload="none" src="{esc(wav, quote=True)}"></audio>'
            f'<p><a href="{esc(wav, quote=True)}">WAV</a> · '
            f'<a href="{esc(source, quote=True)}#t={a:.3f},{b:.3f}">Kaynak ve komşu bağlamı</a> · '
            f'{float(r["start_sec"]):.3f}–{float(r["end_sec"]):.3f} sn</p>'
            f'<details><summary>Kesim kanıtları</summary><p>Whisper: {esc(r["whisper_text"])} '
            f'({r["match_percent"]}%)</p><p>{esc(r["notes"])}</p>'
            f'<p>Baş/son sessizlik: {r["leading_quiet_ms"]} / {r["trailing_quiet_ms"]} ms. '
            f'Komşular: {r["previous_id"] or "Kaynak başı"} / {r["next_id"] or "Kaynak sonu"}.</p></details></article>')
    page = '''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Lambert — 207 kesim</title><style>body{font:17px system-ui;max-width:960px;margin:32px auto;padding:0 20px;background:#f6f7f8;color:#17212b}article{padding:20px;margin:16px 0;background:white;border:1px solid #ccd3d9;border-radius:8px}h2{font-size:18px}audio{width:100%}input{box-sizing:border-box;padding:12px;width:100%;font:inherit}a{color:#075ea6}details{font-size:15px}p{line-height:1.55}</style>
<h1>Lambert: 207 replik kesimi</h1><p>Seslendirmeler doğru kabul edildi. Kontrol: ilk/son hece, komşu replik taşması ve doğal nefesler.
Kesimler teknik olarak incelendi; işitsel onay verilmedi. Üç öncelikli kayıt başta listelenir.</p>
<p><a href="lambert_qa_summary.md">Rapor</a> · <a href="lambert_qa_decisions.tsv">207 satırlık tablo</a></p>
<label for="search">ID veya replik ara</label><input id="search" type="search"><p id="count">207 kayıt</p>'''
    page += '\n'.join(cards)
    page += '''<script>const search=document.getElementById('search');search.addEventListener('input',()=>{let n=0;for(const a of document.querySelectorAll('article')){a.hidden=!a.dataset.search.toLocaleLowerCase('tr').includes(search.value.toLocaleLowerCase('tr'));if(!a.hidden)n++}document.getElementById('count').textContent=n+' kayıt'});document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true);</script></html>'''
    (qa.QA / 'listen.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
