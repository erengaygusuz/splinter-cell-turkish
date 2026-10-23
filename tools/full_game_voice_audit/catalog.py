#!/usr/bin/env python3
"""Join source identities, decoded PCM, existing corpus and event evidence."""
import collections, hashlib, json
from inventory import PROJECT,GAME,OUT,csv_read,csv_write,json_write
FIELDS='new_id mission map speaker_or_archetype event_name editor_id bank stream_index stream_offset sample_count sample_rate duration_sec english_asr english_final classification duplicate_group source_path wav_path confidence notes'.split()


def run():
    refs=csv_read(OUT/'audio-resource-references.csv');decoded=csv_read(OUT/'decoded-unique-resources.csv')
    uax=csv_read(OUT/'uax-events.csv');corpus=csv_read(PROJECT/'manifests/corpus.csv')
    pcm=csv_read(OUT/'original-corpus-pcm.csv');canonical={r['id']:r for r in csv_read(PROJECT/'manifests/canonical-english-final.csv')}
    by_pcm=collections.defaultdict(list);by_enc=collections.defaultdict(list);by_key=collections.defaultdict(list)
    for r in pcm:by_pcm[(r['pcm_sha256'],r['sample_rate'],r['channels'],r['sample_count'])].append(r)
    for r in corpus:by_enc[r['encoded_sha256']].append(r)
    slots={(r['resource_name'],r['stream_offset'],r['stream_size']):r for r in corpus}
    for r in refs:
        if r.get('encoded_key'):by_key[r['encoded_key']].append(r)
    groupnames=collections.defaultdict(set);direct=collections.defaultdict(set)
    graph=collections.defaultdict(list)
    for g in csv_read(OUT/'event-resource-links.csv'):graph[g['encoded_key']].append(g)
    for r in uax:
        groupnames[r['editor_id'][:4]].add(r['package']);direct[r['editor_id']].add(r['package']+'.'+r['event_name'])
    # Union only measured signal matches; never collapse equal transcripts.
    waveform=csv_read(OUT/'waveform-matches.csv') if (OUT/'waveform-matches.csv').exists() else []
    parent={d['new_id']:d['new_id'] for d in decoded}
    def find(x):
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    signal_corpus=collections.defaultdict(set)
    for w in waveform:
        if w['matched_id'].startswith('u'):signal_corpus[w['new_id']].add(w['matched_id'])
        else:union(w['new_id'],w['matched_id'])
    pcm_seen={}
    for d in decoded:
        key=(d['pcm_sha256'],d['sample_rate'],d['channels'],d['sample_count'])
        if key in pcm_seen:union(d['new_id'],pcm_seen[key])
        else:pcm_seen[key]=d['new_id']
    rows=[];physical_duplicates=collections.defaultdict(list)
    for d in decoded:
        if d['status']!='OK':continue
        rr=by_key[d['encoded_key']];r=rr[0]
        cm=by_pcm[(d['pcm_sha256'],d['sample_rate'],d['channels'],d['sample_count'])]
        known={x['id'] for x in cm};changed=set()
        for x in rr:
            if x['bank']=='Sounds/ENGLISH/MAPS.LM0':
                c=slots.get((x['resource_name'],x['stream_offset'],x['stream_size']))
                if c and c['id'] not in known:changed.add(c['id'])
        signal=signal_corpus[d['new_id']]
        ids=known|changed|signal
        notes=[]
        if signal:notes.append('ORIGINAL_CORPUS_WAVEFORM_MATCH: '+','.join(sorted(signal))+'; full PCM correlation >=0.995 and residual SNR >=20dB')
        if changed:notes.append('LIVE_LS0_PAYLOAD_DIFFERS_FROM_ORIGINAL_CORPUS: '+','.join(sorted(changed))+'; slot identity only, not a PCM duplicate')
        packages=sorted({n for x in rr for n in groupnames[x['editor_id'][:4]]})
        links=graph[d['encoded_key']]
        events=sorted({n for x in links for n in x['event_name'].split(';') if n})
        editor_ids=sorted({x['event_editor_id'] for x in links})
        switch_values=sorted({x['switch_value'] for x in links if x['switch_value']})
        human=any(x['language'].lower()=='english' for x in rr) or bool(set(packages)&{'FisherVoice','GenericLife','SoundEvent','radio'})
        cls='PENDING_ASR' if human else 'NON_SPEECH'
        if ids:cls='ALREADY_DUBBED' if all((GAME/'system/sc-tr-audio'/f'{i}.wav').exists() for i in ids) else 'EXISTING_CORPUS'
        if not human and not ids:notes.append('Non-voice UAX archetype; classification by source identity, not listening')
        identity=hashlib.sha256('|'.join(d[k] for k in ['pcm_sha256','sample_rate','channels','sample_count']).encode()).hexdigest()
        row=dict(new_id=d['new_id'],mission=';'.join(sorted({x['mission'] for x in rr})),map=';'.join(sorted({x['map'] for x in rr})),
          speaker_or_archetype=';'.join(packages),event_name=';'.join(events),editor_id=';'.join(editor_ids),
          bank=r['bank'],stream_index=r['stream_index'],stream_offset=r['stream_offset'],sample_count=d['sample_count'],sample_rate=d['sample_rate'],
          duration_sec=d['duration_sec'],english_asr='',english_final='',classification=cls,duplicate_group='audio_'+find(d['new_id']),
          source_path=r['source_path'],wav_path=d['wav_path'],confidence='source_identity' if ids else 'PENDING',notes='; '.join(notes),
          resource_header_id=';'.join(sorted({x['editor_id'] for x in rr})),switch_values=';'.join(switch_values),event_usage_count=len(links),resource_name=';'.join(sorted({x['resource_name'] for x in rr})),reference_count=len(rr),pcm_sha256=d['pcm_sha256'],channels=d['channels'],
          corpus_ids=';'.join(sorted(ids)),corpus_match_kind='PCM_EXACT' if known else ('WAVEFORM_MATCH' if signal else ('PHYSICAL_SLOT_CHANGED_PAYLOAD' if changed else '')),
          human_candidate=int(human),encoded_key=d['encoded_key'])
        result=OUT/'asr-large-v3'/f'{d["new_id"]}.json'
        if result.exists():
            result=json.loads(result.read_text());row['english_asr']=result['text'];row['asr_avg_logprob']=result['avg_logprob'];row['asr_no_speech_prob']=result['no_speech_prob']
        rows.append(row);physical_duplicates[identity].append(row['new_id'])
    csv_write(OUT/'all-unique-audio-resources.csv',rows,FIELDS+list(dict.fromkeys(k for r in rows for k in r if k not in FIELDS)))
    candidates=[r for r in rows if r['human_candidate'] or r['corpus_ids']]
    csv_write(OUT/'full-game-voice-candidates.csv',candidates,FIELDS+list(dict.fromkeys(k for r in candidates for k in r if k not in FIELDS)))
    json_write(OUT/'pcm-duplicate-groups.json',{k:v for k,v in physical_duplicates.items() if len(v)>1})
    print('Classifications',dict(collections.Counter(r['classification'] for r in rows)))
    pending=[r for r in candidates if r['classification']=='PENDING_ASR']
    print('Pending human candidates',len(pending),'minutes',sum(float(r['duration_sec']) for r in pending)/60)
if __name__=='__main__':run()
