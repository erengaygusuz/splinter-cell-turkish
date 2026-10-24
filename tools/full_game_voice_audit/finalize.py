#!/usr/bin/env python3
"""Validate the audit, verify the untouched game, then publish text artifacts."""
import collections,datetime,json,shutil
from inventory import PROJECT,GAME,OUT,csv_read,csv_write,json_write,sha
from extract import pcm_identity

DELIVERABLES='''full-game-audio-inventory.csv bank-index.csv audio-resource-references.csv
decoded-unique-resources.csv original-corpus-pcm.csv uax-events.csv event-resource-links.csv
uax-reference-coverage.csv external-container-coverage.csv external-container-gaps.csv
orphan-stream-headers.csv multitrack-resources.csv waveform-matches.csv event-source-text.csv
full-game-voice-candidates.csv full-game-new-voice-lines.csv full-game-vocalizations.csv
full-game-review-required.csv full-game-transcript-review.csv full-game-other-language-speech.csv
all-audio-decisions.csv full-game-new-voice-summary.txt summary.json validation.json
common-pcm-music-comparison.json asr-evidence.csv final-validation.json
protected-installation-verification.json'''.split()

def run():
    baseline=json.loads((OUT/'protected-installation-baseline.json').read_text())
    mismatches=[rel for rel,digest in baseline.items() if not (GAME/rel).is_file() or sha(GAME/rel)!=digest]
    current={str(p.relative_to(GAME)) for p in (GAME/'Sounds').rglob('*') if p.is_file()}
    current|={str(p.relative_to(GAME)) for p in (GAME/'system/sc-tr-audio').rglob('*.wav')}
    current|={'system/SNDDSound3DDLL_VBR.dll','system/SNDDSound3DDLL_VBR_orig.dll'}
    changes=sorted(current.symmetric_difference(baseline))
    result=dict(verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protected_files=len(baseline),
        mismatches=mismatches,path_set_changes=changes,unchanged=not (mismatches or changes),
        installed_turkish_ids=len(list((GAME/'system/sc-tr-audio').rglob('*.wav'))),
        dll_sha256=baseline['system/SNDDSound3DDLL_VBR.dll'])
    json_write(OUT/'protected-installation-verification.json',result)
    assert result['unchanged'],result
    base=csv_read(OUT/'all-unique-audio-resources.csv')
    evidence=[]
    for r in base:
        fmt,digest=pcm_identity(PROJECT/r['wav_path'])
        assert digest==r['pcm_sha256'],r['new_id']
        assert fmt==(int(r['sample_rate']),int(r['channels']),2,int(r['sample_count'])),r['new_id']
        if r['classification']!='PENDING_ASR':continue
        for folder in ('asr-large-v3','asr-medium-en-no-vad','asr-large-v3-no-vad','radio-language','phrase-language'):
            path=OUT/folder/f'{r["new_id"]}.json'
            if not path.exists():
                assert folder not in {'asr-large-v3','asr-medium-en-no-vad'},r['new_id']
                continue
            a=json.loads(path.read_text())
            if 'pcm_sha256' in a:assert a['pcm_sha256']==r['pcm_sha256']
            evidence.append(dict(new_id=r['new_id'],pass_name=folder,pcm_sha256=r['pcm_sha256'],
                cache_path=str(path.relative_to(PROJECT)),cache_sha256=sha(path),text=a['text'],
                model=a.get('model','large-v3'),language=a.get('language','en'),
                avg_logprob=a.get('avg_logprob'),no_speech_prob=a.get('no_speech_prob'),
                vad_filter=folder=='asr-large-v3',word_timestamps_available=any(s.get('words') for s in a['segments'])))
    decisions=csv_read(OUT/'all-audio-decisions.csv');fresh=csv_read(OUT/'full-game-new-voice-lines.csv')
    assert len(decisions)==len({r['duplicate_group'] for r in decisions})==3655
    assert not any(r['classification']=='ASR_PENDING' for r in decisions)
    all_aliases=[v for r in decisions for v in r['alias_ids'].split(';')]
    assert len(all_aliases)==len(set(all_aliases))==len(base)
    assert all(not r['corpus_ids'] and r['classification']=='NEW_VOICE_REQUIRED' for r in fresh)
    old_ids={v for r in decisions if r['classification']=='ALREADY_DUBBED' for v in r['corpus_ids'].split(';') if v}
    assert old_ids=={p.stem for p in (GAME/'system/sc-tr-audio').rglob('*.wav')}
    assert all((not r['english_final'])==(r['text_qa']=='TEXT_REVIEW_REQUIRED') for r in fresh)
    police=next(r for r in fresh if r['new_id']=='v_e066ee2c634b8938')
    assert police['editor_id']=='00610000' and police['resource_header_id']=='00610036'
    assert police['english_final'].lower()=='is somebody over there?'
    russian=next(r for r in decisions if r['new_id']=='v_7d745aec116c42ad')
    assert russian['classification']=='NON_ENGLISH_SPEECH' and not russian['english_final']
    assert any('10' in r['english_final'] and '4' in r['english_final'] for r in fresh)
    for r in decisions:
        if r['finding_tag']:assert r['finding_tag']=='POLICE_STATION_CONFIRMED_MISSING_BARK'
    csv_write(OUT/'asr-evidence.csv',evidence)
    validation=dict(pcm_wavs_verified=len(base),protected_files_verified=len(baseline),
        asr_cache_records_verified=len(evidence),asr_pass_counts=dict(collections.Counter(r['pass_name'] for r in evidence)),
        existing_turkish_ids_accounted_for=len(old_ids),unique_decision_groups=len(decisions),
        new_dialogue_groups=len(fresh),police_station_identity_regression='PASS',
        russian_radio_regression='PASS',numeric_speech_regression='PASS',alias_coverage='PASS',
        manual_listening='NOT_PERFORMED',runtime_test='NOT_PERFORMED')
    json_write(OUT/'final-validation.json',validation)
    dest=PROJECT/'manifests/full-game-voice-audit';dest.mkdir(parents=True,exist_ok=True)
    for name in DELIVERABLES:shutil.copyfile(OUT/name,dest/name)
    print(json.dumps(validation,indent=2))

if __name__=='__main__':run()
