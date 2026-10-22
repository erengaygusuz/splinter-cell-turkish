#!/usr/bin/env python3
"""Validate VD001 delivery, including the received E001 source without changing prior deliveries."""
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import wave
import zipfile
import vd001_audio_qa as qa


def read(name):
    return json.loads((qa.QA / name).read_text())


def validate_partition(cuts, lengths, expected_ids, excluded_tails=None):
    excluded_tails = excluded_tails or {}
    assert set(excluded_tails) <= set(lengths)
    assert len(cuts) == len({r['id'] for r in cuts}) == len(expected_ids)
    assert {r['id'] for r in cuts} == set(expected_ids)
    pairs = []
    for key, size in lengths.items():
        rows = sorted((r for r in cuts if r['source_key']==key), key=lambda r:int(r['start_sample']))
        assert rows and int(rows[0]['start_sample']) == 0
        expected_end = size
        if key in excluded_tails:
            tail = excluded_tails[key]
            assert tail['end_sample_exclusive'] == size
            assert 0 < tail['start_sample'] < size
            assert tail['id'] == rows[-1]['id']
            expected_end = tail['start_sample']
        assert int(rows[-1]['end_sample_exclusive']) == expected_end
        for row in rows:
            assert 0 <= int(row['start_sample']) < int(row['end_sample_exclusive']) <= size
        for left, right in zip(rows, rows[1:]):
            assert int(left['end_sample_exclusive']) == int(right['start_sample'])
            assert int(left['group_order'])+1 == int(right['group_order'])
            pairs.append((left,right))
    assert len(pairs) == len(cuts)-len(lengths)
    return pairs


def main():
    protected = qa.check_protected()
    snapshot = qa.tsv(qa.QA/'input_snapshot.tsv')
    roots = [Path('dubbing/characters/sam_fisher'), Path('dubbing/characters/irving_lambert')]
    old_paths = {r['path'] for r in snapshot if not Path(r['path']).is_relative_to(qa.BASE) and any(Path(r['path']).is_relative_to(root) for root in roots)}
    current_paths = {str(p) for root in roots for p in root.rglob('*') if p.is_file() and not p.is_relative_to(qa.BASE)}
    workspace_changes = read('workspace_changes.json')
    added = {r['path'] for r in workspace_changes['added']}
    removed = {r['path'] for r in workspace_changes['removed']}
    assert current_paths == (old_paths - removed) | added, 'Unrecorded character archive file set change'
    for item in workspace_changes['added']:
        assert qa.sha(item['path']) == item['sha256'], 'Observed external file changed again'
    expected, sources = qa.load_inputs()
    assert len(sources) == 3, 'The complete delivery requires E001 and both R001 sources'
    cuts = qa.selected_cuts()
    r001 = [r for r in expected if r['group'].startswith('R001')]
    e001 = [r for r in expected if r['id'] not in {c['id'] for c in cuts}]
    pcm = {s['key']:qa.decode(s['path']) for s in sources}
    tails = read('excluded_source_tails.json')
    pairs = validate_partition(cuts, {k:len(p) for k,p in pcm.items()}, [r['id'] for r in expected], tails)
    medium = {k:v for g in ['R001','E001'] for k,v in read(f'clip_asr_{g}_20261021.json').items()}
    original_cuts = [r for g in ['R001','E001'] for r in qa.tsv(qa.QA/f'cuts_{g}_20261021.tsv')]
    all_media = []
    for cut in original_cuts + qa.tsv(qa.QA/'revision_manifest.tsv'):
        digest = qa.sha(cut['wav_path'])
        assert digest == cut['sha256']
        if cut['version'] == 'v01':
            assert medium[cut['id']]['sha256'] == digest
        with wave.open(cut['wav_path']) as wav:
            assert wav.getparams()[:3] == (1,2,qa.RATE)
            a,b = int(cut['start_sample']),int(cut['end_sample_exclusive'])
            assert wav.getnframes() == b-a
            assert wav.readframes(wav.getnframes()) == pcm[cut['source_key']][a:b].tobytes()
        all_media.append(dict(id=cut['id'],version=cut['version'],wav_path=cut['wav_path'],sha256=digest,source_pcm_identical=True))
    qa.write_tsv(qa.QA/'all_wav_versions_integrity.tsv',all_media)
    medium.update(read('revision_asr.json'))
    large = read('isolated_retry_large_v3.json')
    large.update(read('revision_large_v3.json'))
    reviews = read('review_notes.json')
    alignment = {r['id']:r for g in ['R001','E001'] for r in read(f'alignment_{g}_20261021.json')}
    unmatched = read('unassigned_words.json')
    resolved = read('unassigned_word_resolutions.json')
    assert {(r['source_key'],r['word_index']) for r in unmatched} == {(r['source_key'],r['word_index']) for r in resolved}
    for resolution in resolved:
        assert resolution['assigned_id'] in alignment
    acoustic = {r['id']:r for r in qa.tsv(qa.QA/'acoustic_screen.tsv')}
    plots = {(r['left_id'],r['right_id']):r for r in qa.tsv(qa.QA/'boundary_plots/index.tsv')}
    visual = read('visual_review.json')
    assert visual['interline_boundaries_viewed'] == len(pairs) == len(plots)
    for name, digest in visual['plot_sha256'].items():
        assert qa.sha(qa.QA/'boundary_plots'/name) == digest
    assert set(medium) == {r['id'] for r in cuts}
    assert set(large) == set(read('retry_ids.json'))
    media, rows = [], []
    previous, following = {}, {}
    boundary_rows = []
    for left,right in pairs:
        previous[right['id']] = left['id']
        following[left['id']] = right['id']
        plot = plots[(left['id'],right['id'])]
        assert int(plot['boundary_sample']) == int(right['start_sample'])
        boundary_rows.append(dict(left_id=left['id'],right_id=right['id'],source_key=left['source_key'],
            boundary_sample=left['end_sample_exclusive'],boundary_sec=left['end_sec'],
            gap_samples=0,overlap_samples=0,visual_result='INTERLINE_QUIET_REGION',
            left_last_word_anchor=alignment[left['id']]['last_word'],
            right_first_word_anchor=alignment[right['id']]['first_word'],
            plot='boundary_plots/'+plot['page'],listened=False))
    qa.write_tsv(qa.QA/'neighbor_boundaries.tsv',boundary_rows)
    for cut in cuts:
        ident = cut['id']
        digest = qa.sha(cut['wav_path'])
        assert digest == cut['sha256'] == medium[ident]['sha256']
        assert Path(cut['wav_path']).is_relative_to(qa.BASE/'review_pending')
        assert Path(cut['wav_path']).name == f'{ident}_{cut["version"]}.wav'
        a,b = int(cut['start_sample']),int(cut['end_sample_exclusive'])
        with wave.open(cut['wav_path']) as wav:
            assert wav.getparams()[:3] == (1,2,qa.RATE)
            assert wav.getnframes() == b-a
            assert wav.readframes(wav.getnframes()) == pcm[cut['source_key']][a:b].tobytes()
        if ident in large:
            assert large[ident]['sha256'] == digest
        al, ac, m = alignment[ident], acoustic[ident], medium[ident]
        assert float(ac['start_sec']) == a/qa.RATE and float(ac['end_sec']) == b/qa.RATE
        assert ac['version'] == cut['version']
        media.append(dict(id=ident,version=cut['version'],path=cut['wav_path'],sha256=digest,
            frames=b-a,source_pcm_identical=True))
        note = reviews.get(ident, {})
        rows.append(dict(id=ident,catalog_order=al['catalog_order'],production_set=cut['group'][:4],
            production_sequence=cut['group_order'],expected_text=cut['expected_text'],
            source_mp3=cut['source_mp3'],source_sha256=cut['source_sha256'],
            start_sample=a,end_sample_exclusive=b,start_sec=a/qa.RATE,end_sec=b/qa.RATE,duration_sec=(b-a)/qa.RATE,
            selected_version=cut['version'],selected_wav=cut['wav_path'],wav_sha256=digest,
            whisper_text=m['text'],match_percent=m['match'],source_whisper_text=al['source_asr_text'],
            large_model_text=large.get(ident,{}).get('text',''),large_model_match=large.get(ident,{}).get('match',''),
            first_word_anchor=al['first_word'],first_word_start=al['first_word_start'],
            last_word_anchor=al['last_word'],last_word_end=al['last_word_end'],
            anchor_method='REVIEWED_SOURCE_WAVEFORM' if al.get('manual_anchor') else 'ORDERED_ASR_ALIGNMENT',
            previous_id=previous.get(ident,''),next_id=following.get(ident,''),
            leading_quiet_ms=ac['leading_quiet_ms'],trailing_quiet_ms=ac['trailing_quiet_ms'],
            start_edge_dbfs=ac['start_edge_dbfs'],end_edge_dbfs=ac['end_edge_dbfs'],acoustic_flags=ac['flags'],
            source_pcm_identical=True,technical_status='SOURCE_EDGE_REVIEW' if ac['flags'] else 'TECHNICAL_CUT_PASS',
            decision=note.get('decision','NEEDS_LISTEN'),confidence=note.get('confidence','HIGH_TECHNICAL_NOT_AUDITORY'),
            content_issue=note.get('category',''),review_note=note.get('note','Kaynak sırası, WAV transkripti ve sessiz bölge kontrolü uyumlu; işitsel onay verilmedi.'),
            listened=False,approved=False,regenerate_confirmed=False))
    fields=list(rows[0])
    for item in e001:
        row={k:'' for k in fields}
        row.update(id=item['id'],catalog_order=item['catalog_order'],production_set='E001',
            production_sequence=item['group_order'],expected_text=item['expected_text'],
            technical_status='SOURCE_AUDIO_MISSING',decision='SOURCE_AUDIO_MISSING',
            confidence='NO_AUDIO',review_note='E001 kaynak MP3 teslim edilmedi. Eski Fisher sesiyle doldurulmadı.',
            listened=False,approved=False,regenerate_confirmed=False)
        rows.append(row)
    rows.sort(key=lambda r:int(r['catalog_order']))
    assert len(rows)==len({r['id'] for r in rows})==201
    qa.write_tsv(qa.QA/'vd001_qa_decisions_201.tsv',rows)
    qa.write_tsv(qa.QA/'missing_source_audio.tsv',[r for r in rows if r['decision']=='SOURCE_AUDIO_MISSING'],fields)
    qa.write_tsv(qa.QA/'selected_cuts_201.tsv', [{k:r[k] for k in original_cuts[0]} for r in cuts])
    qa.write_tsv(qa.QA/'wav_integrity.tsv',media)
    qa.write_tsv(qa.QA/'pronunciation_review.tsv',[r for r in rows if r['content_issue']=='PRONUNCIATION_UNCONFIRMED'],fields)
    qa.write_tsv(qa.QA/'content_review.tsv',[r for r in rows if r['content_issue']=='CONTENT_UNCONFIRMED'],fields)
    qa.write_tsv(qa.QA/'regenerate_required.tsv',[],['id','reason','evidence'])
    fixes=[]
    for ident,anchor in read('manual_anchors.json').items():
        fixes.append(dict(id=ident,stage='BEFORE_V01',reason=anchor['reason'],
            selected_wav=next(c['wav_path'] for c in cuts if c['id']==ident),
            isolated_asr=medium[ident]['text'],status='CORRECTED_INITIAL_ALIGNMENT'))
    qa.write_tsv(qa.QA/'cut_corrections.tsv',fixes)
    old_by_id = {r['id']:r for r in original_cuts}
    qa.write_tsv(qa.QA/'revision_comparison.tsv', [dict(id=r['id'],old_wav=old_by_id[r['id']]['wav_path'],
        new_wav=r['wav_path'],old_end_sec=old_by_id[r['id']]['end_sec'],new_end_sec=r['end_sec'],
        old_sha256=old_by_id[r['id']]['sha256'],new_sha256=r['sha256'],reason=r['revision_reason'])
        for r in qa.tsv(qa.QA/'revision_manifest.tsv')])
    qa.write_tsv(qa.QA/'boundary_review.tsv',[r for r in rows if r['technical_status']=='SOURCE_EDGE_REVIEW'],fields)
    source_rows=[]
    for s in sources:
        group=[r for r in cuts if r['source_key']==s['key']]
        source_rows.append(dict(source_key=s['key'],path=s['path'],count=len(group),
            first_id=group[0]['id'],last_id=group[-1]['id'],first_order=group[0]['group_order'],
            last_order=group[-1]['group_order'],duration_sec=len(pcm[s['key']])/qa.RATE,
            first_text=group[0]['expected_text'],last_text=group[-1]['expected_text']))
    qa.write_tsv(qa.QA/'source_boundaries.tsv',source_rows)
    make_listen_page(rows)
    make_archive(cuts)
    qa.save_json(qa.QA/'validation.json',dict(protected_files_unchanged=protected,old_character_file_sets_unchanged=not bool(added or removed),
        observed_external_added_files=len(added),observed_external_removed_empty_placeholders=len(removed),
        expected_ids=201,available_cuts=len(cuts),missing_e001=len(e001),source_count=len(sources),
        source_distribution={r['source_key']:r['count'] for r in source_rows},
        duration_sec=sum(len(p) for p in pcm.values())/qa.RATE,exact_source_pcm_wavs=len(media),
        all_wav_versions_verified=len(all_media),selected_versions=dict(Counter(r['version'] for r in cuts)),
        excluded_tail_samples=sum(r['end_sample_exclusive']-r['start_sample'] for r in tails.values()),
        excluded_tail_sec=sum(r['end_sample_exclusive']-r['start_sample'] for r in tails.values())/qa.RATE,
        contiguous_boundaries=len(pairs),visually_reviewed_boundaries=len(pairs),source_edges_viewed=2*len(sources),
        originally_unassigned_asr_words=len(unmatched),unassigned_words_resolved=len(resolved),
        isolated_medium_count=len(medium),medium_exact_matches=sum(v['match']==100 for v in medium.values()),
        large_isolated_count=len(large),large_context_windows=len(read('context_asr_large_v3.json'))+len(read('followup_context_asr_large_v3.json')),
        decision_counts=dict(Counter(r['decision'] for r in rows)),content_counts=dict(Counter(r['content_issue'] for r in rows if r['content_issue'])),
        active_edge_flags=sum('ACTIVE_EDGE' in r['flags'] for r in acoustic.values()),
        short_edge_flags=sum('SHORT_EDGE_MARGIN' in r['flags'] for r in acoustic.values()),
        clipped_samples=sum(int(r['clipped_samples']) for r in acoustic.values()),
        listened=0,approved=0,confirmed_regenerate_required=0,completion='201 WAV candidates; no missing source audio; auditory review pending'))
    print('Verified:',len(cuts),'WAVs;',len(e001),'explicitly missing;',len(pairs),'boundaries;',protected,'protected files unchanged.')


def make_archive(cuts):
    path=qa.BASE/'review_pending/sam_fisher_VD001_201_v2_20261021.zip'
    if not path.exists():
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for cut in sorted(cuts,key=lambda r:r['id']):
                info=zipfile.ZipInfo(Path(cut['wav_path']).name,date_time=(2026,10,21,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,Path(cut['wav_path']).read_bytes())
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==201
        assert set(z.namelist())=={Path(r['wav_path']).name for r in cuts}
        for cut in cuts:
            assert hashlib.sha256(z.read(Path(cut['wav_path']).name)).hexdigest()==cut['sha256']
    qa.save_json(qa.QA/'delivery_archive.json',dict(path=str(path),bytes=path.stat().st_size,
        sha256=qa.sha(path),wav_count=201,voice_version='VD001',missing_e001=0,status='REVIEW_PENDING'))


def make_listen_page(rows):
    esc=html.escape
    cards=[]
    for r in sorted(rows,key=lambda r:(r['decision']=='SOURCE_AUDIO_MISSING',not bool(r['content_issue']),int(r['catalog_order']))):
        content=f'<h2>{r["id"]} · {r["production_set"]} · {r["decision"]}</h2><p>{esc(r["expected_text"])}</p>'
        if r['selected_wav']:
            wav=os.path.relpath(r['selected_wav'],qa.QA)
            source=os.path.relpath(r['source_mp3'],qa.QA)
            start=max(0,float(r['start_sec'])-.75)
            end=float(r['end_sec'])+.75
            content+=f'<audio controls preload="none" src="{esc(wav,quote=True)}"></audio><p><a href="{esc(wav,quote=True)}">WAV</a> · <a href="{esc(source,quote=True)}#t={start:.3f},{end:.3f}">Kaynak ve komşu bağlamı</a> · {r["start_sec"]:.3f}–{r["end_sec"]:.3f} sn</p>'
            content+=f'<details><summary>Transkript ve kesim kanıtı</summary><p>Medium: {esc(r["whisper_text"])} ({r["match_percent"]}%)</p><p>Large-v3: {esc(r["large_model_text"])}</p><p>{esc(r["review_note"])}</p></details>'
        else:
            content+='<p>E001 kaynak MP3 bekleniyor. Bu ID için VD001 WAV oluşturulmadı.</p>'
        cards.append(f'<article data-search="{esc(r["id"]+" "+r["expected_text"],quote=True)}">{content}</article>')
    page='''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Sam Fisher VD001 — 201 ses adayı</title>
<style>body{font:17px system-ui;max-width:960px;margin:32px auto;padding:0 20px;background:#f5f6f8;color:#17212b}article{padding:20px;margin:16px 0;background:white;border:1px solid #ccd3d9;border-radius:8px}h2{font-size:18px}audio,input{width:100%}input{box-sizing:border-box;padding:12px;font:inherit}p{line-height:1.55}a{color:#075ea6}</style>
<h1>Sam Fisher VD001</h1><p>190 R001 ve 11 E001 kesimi mevcut. Eksik kaynak sesi yok. CIA repliği u000125 için kaynak sonu dinleme kontrolü gerekli. Eski Fisher sesi kullanılmadı. İşitsel onay verilmedi; telaffuz bayrakları doğrulanmış üretim hatası değildir.</p>
<p><a href="vd001_summary.md">Rapor</a> · <a href="vd001_qa_decisions_201.tsv">201 ID tablosu</a></p><label for="search">ID veya replik ara</label><input id="search" type="search"><p id="count">201 kayıt</p>'''
    page+='\n'.join(cards)
    page+='''<script>const search=document.getElementById('search');search.addEventListener('input',()=>{let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=!a.dataset.search.toLocaleLowerCase('tr').includes(search.value.toLocaleLowerCase('tr'));if(!a.hidden)n++});document.getElementById('count').textContent=n+' kayıt'});document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true);</script></html>'''
    (qa.QA/'listen.html').write_text(page,encoding='utf-8')


if __name__=='__main__':
    main()
