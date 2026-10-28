#!/usr/bin/env python3
"""Align only within each declared physical source; emit versioned candidates."""
from common import *
import argparse
from collections import Counter
import numpy as np

def run():
    p=argparse.ArgumentParser();p.add_argument('--model',default='medium');p.add_argument('--version',default='v01');p.add_argument('--only',nargs='+');args=p.parse_args()
    assert re.fullmatch(r'v\d{2,}',args.version)
    expected=read(QA/'resolved_expected.json');plans=[];cuts=[];boundaries=[];unknown_all=[]
    overrides=read(QA/'boundary_overrides.json') if (QA/'boundary_overrides.json').exists() else {}
    for src in read(QA/'sources.json'):
        subset=[r for r in expected if r['source_key']==src['source_key']]
        if args.only and not any(r['new_id'] in args.only for r in subset):continue
        cache=QA/('source_asr_'+args.model)/(src['source_key']+'.json')
        if not cache.exists():print('Waiting for source ASR',src['source_key'],flush=True);continue
        d=read(cache);assert d['sha256']==src['decoded_sha256']
        words=[dict(w,source_word_index=i) for i,w in enumerate(d['words'])]
        matched,unknown=alignment.match_words([dict(id=r['new_id'],expected_text=r['expected_text']) for r in subset],words)
        unknown_all.extend(dict(w,source_key=src['source_key']) for w in unknown)
        path=ROOT/src['decoded_wav'];assert sha(path)==src['decoded_sha256']
        with wave.open(str(path)) as w:data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        quiet=alignment.quiet_runs(data,threshold=-50,min_seconds=.04)
        local=[]
        for r in subset:
            anchors=matched[r['new_id']];text=' '.join(w['text'] for w in anchors);score=alignment.score(text,r['expected_text'])
            flags=[]
            if not anchors:flags.append('MISSING_WORD_ANCHORS')
            if score<85:flags.append('LOW_SOURCE_TEXT_MATCH')
            local.append(dict(**r,source_asr=text,source_score=score,word_anchors=anchors,alignment_flags=flags))
        points=[dict(time=0.,quiet_start=0.,quiet_end=0.,method='SOURCE_START')]
        for left,right in zip(local,local[1:]):
            pair=left['new_id']+'|'+right['new_id']
            if pair in overrides:
                o=overrides[pair];assert o['physical_source_sha256']==src['physical_source_sha256']
                cut=dict(time=o['time'],quiet_start=o.get('quiet_start',''),quiet_end=o.get('quiet_end',''),method=o['basis'],threshold_dbfs=o.get('threshold_dbfs',-50))
            elif left['word_anchors'] and right['word_anchors']:
                cut=alignment.pick_boundary(left['word_anchors'][-1]['end'],right['word_anchors'][0]['start'],quiet)
            else:cut=dict(time=None,method='MISSING_NEIGHBOR_ANCHORS',quiet_start='',quiet_end='')
            points.append(cut);boundaries.append(dict(source_key=src['source_key'],left=left['new_id'],right=right['new_id'],**cut))
        points.append(dict(time=len(data)/RATE,quiet_start=len(data)/RATE,quiet_end=len(data)/RATE,method='SOURCE_END'))
        for i,r in enumerate(local):
            if args.only and r['new_id'] not in args.only:continue
            left,right=points[i:i+2];flags=r['alignment_flags']
            if left['time'] is None or right['time'] is None:
                flags.append('UNRESOLVED_BOUNDARY');plans.append(r);continue
            a,b=round(left['time']*RATE),round(right['time']*RATE)
            if not 0<=a<b<=len(data):flags.append('INVALID_INTERVAL');plans.append(r);continue
            for edge in (left,right):
                if 'NEEDS_REVIEW' in edge['method']:flags.append('NO_QUIET_BOUNDARY')
            chunk=data[a:b];hop=220;amplitude=chunk[:len(chunk)//hop*hop].astype(float).reshape(-1,hop)/32768
            active=np.flatnonzero(np.sqrt(np.mean(amplitude*amplitude,axis=1))>10**(-50/20))
            lead=active[0]*hop/RATE if len(active) else len(chunk)/RATE;trail=(len(amplitude)-active[-1]-1)*hop/RATE if len(active) else len(chunk)/RATE
            # Keep the actual per-edge noise criterion instead of treating a
            # low-level reverberation tail as a clipped lexical word.
            for edge in (left,right):
                threshold=edge.get('threshold_dbfs',-50)
                if threshold!=-50:
                    at=np.flatnonzero(np.sqrt(np.mean(amplitude*amplitude,axis=1))>10**(threshold/20))
                    if len(at):
                        if edge is left:lead=at[0]*hop/RATE
                        else:trail=(len(amplitude)-at[-1]-1)*hop/RATE
            if min(lead,trail)<.025:flags.append('SHORT_EDGE_MARGIN')
            unassigned=[w for w in unknown if a/RATE<=w['start']<b/RATE]
            if unassigned:flags.append('UNASSIGNED_WORDS')
            out=BASE/'review_pending/R001_20261028'/args.version/(r['new_id']+'.wav');wav(out,chunk)
            r.update(start_sample=a,end_sample=b,start_sec=a/RATE,end_sec=b/RATE,leading_quiet_ms=round(lead*1000,1),trailing_quiet_ms=round(trail*1000,1),
                start_method=left['method'],end_method=right['method'],unassigned_words=unassigned,output_wav_path=rel(out),output_wav_sha256=sha(out),version=args.version,
                start_threshold_dbfs=left.get('threshold_dbfs',-50),end_threshold_dbfs=right.get('threshold_dbfs',-50),
                sample_rate=RATE,qa_status='REVIEW_PENDING',alignment_status='FLAGS_PRESENT' if flags else 'SOURCE_ALIGNED')
            plans.append(r);cuts.append({k:v for k,v in r.items() if k not in {'word_anchors','unassigned_words'}})
    if args.only:
        assert set(args.only)=={r['new_id'] for r in cuts}
        for file,data in [('alignment.json',plans),('cuts.json',cuts)]:
            old=read(QA/file);new={r['new_id']:r for r in data};save(QA/(Path(file).stem+'_'+args.version+'.json'),data,True)
            save(QA/file,[new.get(r['new_id'],r) for r in old])
    else:
        save(QA/('alignment_'+args.version+'.json'),plans,True);save(QA/('cuts_'+args.version+'.json'),cuts,True)
        save(QA/'alignment.json',plans);save(QA/'cuts.json',cuts)
    table(QA/('boundaries_'+args.version+'.csv'),boundaries);save(QA/('unassigned_'+args.version+'.json'),unknown_all)
    table(QA/'cuts.csv',read(QA/'cuts.json'))
    print('Planned',len(plans),'cut',len(cuts),'flags',dict(Counter(f for r in plans for f in r['alignment_flags'])),flush=True)

if __name__=='__main__':run()
