#!/usr/bin/env python3
"""Propose acoustic-gap centers with explicit noise thresholds and unchanged order."""
from common import *
import numpy as np

def run():
    plan=read(QA/'alignment.json');sources={r['source_key']:r for r in read(QA/'sources.json')}
    overrides={};affected=set();evidence=[]
    for key,source in sources.items():
        local=[r for r in plan if r['source_key']==key]
        with wave.open(str(ROOT/source['decoded_wav'])) as w:audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        runs={threshold:alignment.quiet_runs(audio,threshold=threshold,min_seconds=.065) for threshold in (-50,-45,-40)}
        for left,right in zip(local,local[1:]):
            if left['end_method']!='NO_QUIET_BOUNDARY_NEEDS_REVIEW' and min(left['trailing_quiet_ms'],right['leading_quiet_ms'])>=25:continue
            old=left['end_sec'];assert abs(old-right['start_sec'])<1/RATE
            chosen=None
            for threshold,quiet in runs.items():
                choices=[(a,b) for a,b in quiet if a-.001<=old<=b+.001 or abs((a+b)/2-old)<.25]
                if choices:
                    a,b=min(choices,key=lambda ab:abs((ab[0]+ab[1])/2-old));chosen=(a,b,threshold);break
            if chosen is None:continue
            a,b,threshold=chosen;new=(a+b)/2
            if not left['start_sec']+.08<new<right['end_sec']-.08:continue
            # An adaptive floor is allowed only when it is far below neighboring speech.
            neighbors=audio[max(0,round((old-.6)*RATE)):min(len(audio),round((old+.6)*RATE))].astype(float)/32768
            hop=220;blocks=neighbors[:len(neighbors)//hop*hop].reshape(-1,hop)
            peak_db=20*np.log10(max(1e-7,float(np.percentile(np.sqrt(np.mean(blocks*blocks,axis=1)),90))))
            if peak_db-threshold<20:continue
            pair=left['new_id']+'|'+right['new_id']
            overrides[pair]=dict(time=new,quiet_start=a,quiet_end=b,threshold_dbfs=threshold,neighbor_speech_dbfs=round(peak_db,2),
                basis='ACOUSTIC_GAP_CENTER_WITH_SOURCE_ORDER',physical_source_sha256=source['physical_source_sha256'])
            evidence.append(dict(source_key=key,left=left['new_id'],right=right['new_id'],old_time=old,**overrides[pair]))
            affected.update((left['new_id'],right['new_id']))
    save(QA/'boundary_overrides.json',overrides,True);table(QA/'boundary_refinement.csv',evidence)
    save(QA/'boundary_refinement_ids.json',sorted(affected),True)
    print('Acoustic refinements',len(overrides),'boundaries;',len(affected),'affected clips')

if __name__=='__main__':run()
