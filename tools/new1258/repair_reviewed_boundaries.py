#!/usr/bin/env python3
"""Revisit held clips using the alternate model's complete local word anchors."""
from common import *
from collections import defaultdict
import numpy as np

def run():
    plan=read(QA/'alignment.json');review={r['new_id'] for r in rows(QA/'review_required.csv')}
    sources={r['source_key']:r for r in read(QA/'sources.json')};overrides=read(QA/'boundary_overrides.json')
    save(QA/'boundary_overrides_before_v04.json',overrides,True)
    affected=set();evidence=[]
    for key,source in sources.items():
        local=[r for r in plan if r['source_key']==key]
        if not any(r['new_id'] in review for r in local):continue
        d=read(QA/'source_asr_medium'/(key+'.json'))
        matched,_=alignment.match_words([dict(id=r['new_id'],expected_text=r['expected_text']) for r in local],d['words'])
        with wave.open(str(ROOT/source['decoded_wav'])) as w:audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        quiet={t:alignment.quiet_runs(audio,threshold=t,min_seconds=.04) for t in (-50,-45,-40)}
        for left,right in zip(local,local[1:]):
            if not ({left['new_id'],right['new_id']}&review):continue
            pair=left['new_id']+'|'+right['new_id'];anchors=[]
            for r in (left,right):
                medium=matched[r['new_id']]
                score=alignment.score(' '.join(w['text'] for w in medium),r['expected_text'])
                anchors.append(medium if medium and score>=85 else r['word_anchors'])
            lw,rw=anchors[0][-1],anchors[1][0];target=(lw['end']+rw['start'])/2
            lo=max(left['start_sec']+.08,lw['start']+.4*(lw['end']-lw['start'])-.05)
            hi=min(right['end_sec']-.08,rw['start']+.6*(rw['end']-rw['start'])+.05)
            chosen=None
            for threshold,runs in quiet.items():
                options=[(a,b) for a,b in runs if lo<(a+b)/2<hi and abs((a+b)/2-target)<.45]
                if options:chosen=(*min(options,key=lambda ab:abs((ab[0]+ab[1])/2-target)),threshold);break
            if chosen is None:continue
            a,b,t=chosen;new=(a+b)/2
            if abs(new-left['end_sec'])<.004 and pair in overrides:continue
            region=audio[max(0,int((new-.6)*RATE)):min(len(audio),int((new+.6)*RATE))].astype(float)/32768
            region=region[:len(region)//220*220].reshape(-1,220)
            speech=20*np.log10(max(1e-7,float(np.percentile(np.sqrt(np.mean(region*region,axis=1)),90))))
            if speech-t<15:continue
            overrides[pair]=dict(time=new,quiet_start=a,quiet_end=b,threshold_dbfs=t,neighbor_speech_dbfs=round(speech,2),
                basis='ALTERNATE_WORD_ANCHORS_AND_ACOUSTIC_GAP',physical_source_sha256=source['physical_source_sha256'])
            evidence.append(dict(source_key=key,left=left['new_id'],right=right['new_id'],previous_time=left['end_sec'],**overrides[pair]))
            affected.update((left['new_id'],right['new_id']))
    save(QA/'boundary_overrides_v04.json',overrides,True);save(QA/'boundary_overrides.json',overrides)
    save(QA/'boundary_refinement_ids_v04.json',sorted(affected),True);table(QA/'boundary_refinement_v04.csv',evidence)
    print('Alternate-timing repairs',len(evidence),'boundaries;',len(affected),'clips')

if __name__=='__main__':run()
