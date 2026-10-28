#!/usr/bin/env python3
"""Resolve all 1,258 production rows to exactly one of 31 physical MP3s."""
from common import *
from collections import Counter
import shutil

MERGED={
 'camera_all_27_':['CAMERA_BIRMANIE','CAMERA_GEORGIE','CAMERA_USA'],
 'story_ex-spetsnaz-1-2_all_2_':['STORY_EX-SPETSNAZ-1','STORY_EX-SPETSNAZ-2'],
 'story_kola_all_29_':['STORY_KOLA_MAFIOSO','STORY_KOLA_MAFIOSO_1','STORY_KOLA_MAFIOSO_2','STORY_KOLA_NIKOLAI_SPETZ','STORY_KOLA_PHONE_SPETZ','STORY_KOLA_SPETSNAZ_1','STORY_KOLA_SPETSNAZ_2','STORY_KOLA_SPETSNAZ_3','STORY_KOLA_TECHNICIAN','STORY_KOLA_TECHNICIAN_2'],
 'story_masse_to_vselka_spetsnaz_all_25_':['STORY_MASSE','STORY_SPETSNAZ','STORY_VSELKA_INTERROGATED_MERC']+['STORY_VSELKA_SPETSNAZ_'+str(i) for i in range(1,8)],
 'story_vselka_sub_exspetsnaz_all_8_':['STORY_VSELKA_SUB_EXSPETSNAZ_'+str(i) for i in range(1,6)]}

def run():
    expected=rows(INDEX/'00_production_index.csv');authority={r['new_id']:r for r in rows(ROOT/'manifests/full-game-voice-audit/final-turkish-production-voices.csv')}
    assert len(expected)==len({r['new_id'] for r in expected})==len(authority)==1258
    assert {r['new_id'] for r in expected}==set(authority)
    groups=list(dict.fromkeys(r['voice_group'] for r in expected));assert len(groups)==55
    input_hashes=[]
    for target in sorted({r['mp3_target'] for r in expected}):
        part=[r for r in expected if r['mp3_target']==target]
        assert [int(r['line_in_mp3']) for r in part]==list(range(1,len(part)+1))
        txt=INDEX/Path(target).with_suffix('.txt');lines=[alignment.spoken(t) for t in txt.read_text(encoding='utf-8-sig').splitlines() if alignment.spoken(t)]
        assert lines==[r['turkish_final'] for r in part],f'TXT/index mismatch: {txt}'
        input_hashes.append(dict(path=str(txt),sha256=sha(txt)))
    for p in (INDEX/'00_production_index.csv',INDEX/'00_voice_groups.csv',ROOT/'manifests/full-game-voice-audit/final-turkish-production-voices.csv'):
        input_hashes.append(dict(path=str(p),sha256=sha(p)))
    files=sorted((BASE/'production_sources').rglob('*.mp3'));assert len(files)==31
    sources=[];mapped=[]
    for p in files:
        keys=next((v for prefix,v in MERGED.items() if p.name.startswith(prefix)),None)
        if p.name.startswith('exspetsnaz_part'):
            keys=['Exspetsnaz'];parts=range(1,5) if '001-004' in p.name else [5]
            selected=[r for r in expected if r['mp3_target'] in [f'exspetsnaz_part{i:03}.mp3' for i in parts]]
        else:
            if keys is None:keys=[g for g in groups if p.name.startswith(g.lower()+'_all_')]
            assert keys,p
            selected=[r for g in keys for r in sorted(expected,key=lambda r:(r['mp3_target'],int(r['line_in_mp3']))) if r['voice_group']==g]
        assert selected,p
        namecount=re.search(r'_all_(\d+)_',p.name)
        if namecount:assert len(selected)==int(namecount[1]),(p,len(selected))
        digest=sha(p);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]));s=probe['streams'][0]
        decoded=pcm(p);decoded_path=BUILD/'decoded_sources'/f'{p.stem}.wav';wav(decoded_path,decoded)
        source=dict(source_key=p.stem,physical_source_mp3=rel(p),physical_source_sha256=digest,bytes=p.stat().st_size,
            codec=s['codec_name'],source_rate=s['sample_rate'],source_channels=s['channels'],decoded_wav=rel(decoded_path),
            decoded_sha256=sha(decoded_path),decoded_pcm_sha256=hashlib.sha256(decoded.tobytes()).hexdigest(),sample_rate=RATE,
            sample_count=len(decoded),duration_sec=len(decoded)/RATE,expected_lines=len(selected),groups=keys)
        sources.append(source)
        for i,r in enumerate(selected,1):
            a=authority[r['new_id']]
            for k in ('turkish_final','event_name','map','source_pcm_sha256'):assert r[k]==a[k],(r['new_id'],k)
            mapped.append(dict(**r,source_key=p.stem,physical_source_mp3=rel(p),physical_source_sha256=digest,sequence_in_source=i,
                expected_text=alignment.spoken(r['turkish_final']),original_bank=a['bank'],original_stream_index=a['stream_index'],original_stream_offset=a['stream_offset']))
    assert len(mapped)==len({r['new_id'] for r in mapped})==1258
    assert set(r['new_id'] for r in mapped)==set(authority)
    save(QA/'sources.json',sources,True);save(QA/'expected.json',mapped,True);save(QA/'production_input_hashes.json',input_hashes,True)
    table(QA/'physical_source_inventory.csv',sources);table(QA/'physical_line_mapping.csv',mapped)
    ref=QA/'production_reference';ref.mkdir(parents=True,exist_ok=True)
    for p in [INDEX/'00_production_index.csv',INDEX/'00_voice_groups.csv']:
        dest=ref/p.name
        if dest.exists():assert sha(dest)==sha(p)
        else:shutil.copyfile(p,dest)
    save(QA/'source_summary.json',dict(physical_mp3s=31,logical_voice_groups=55,unique_ids=1258,
        decoded_duration_minutes=sum(r['duration_sec'] for r in sources)/60,counts={r['source_key']:r['expected_lines'] for r in sources}),True)
    print('Verified 31 MP3 / 55 groups / 1258 IDs; minutes',round(sum(r['duration_sec'] for r in sources)/60,2),flush=True)

if __name__=='__main__':run()
