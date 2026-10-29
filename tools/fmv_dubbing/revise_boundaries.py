"""Apply inspected waveform boundaries to adjacent pairs; retain v01 masters."""
import json
from catalog import ROOT,QA,write,sha
from cut import RUN,RATE,audio,save_master
OVERRIDES=[('02_Tbilisi','TBI-001','TBI-005',1.45),('08_Kalinatek','OD-01','OD-02',3.12),('10_PowerPlant_Osprey','SA-01','SA-02',3.78),('05_CaspianOilRefinery','OD-01','OD-02',16.8),('05_CaspianOilRefinery','OD-03','OD-04',44.52),('06_CIA','OD-05','GE-01',59.87)]
def main():
 rows=json.loads((QA/'cuts_v01.json').read_text());index={(r['video'],r['id']):dict(r) for r in rows};changed={}
 for v,left,right,t in OVERRIDES:
  l=index[v,left];r=index[v,right];assert l['source']==r['source'] and abs(l['source_end']-r['source_start'])<1e-6
  l['source_end']=t;r['source_start']=t
  for u in (l,r):changed[v,u['id']]=u
 for u in changed.values():
  x=audio(ROOT/u['source']);a,b=u['source_start'],u['source_end'];p=RUN/'review_pending'/u['video']/'master'/(u['id']+'_v02.wav')
  chunk=x[round(a*RATE):round(b*RATE)]
  if not p.exists():save_master(chunk,p)
  else:
   import numpy as np
   y=audio(p);assert len(y)==len(chunk) and np.max(np.abs(y-chunk))<2e-7
  u.update(master=str(p.relative_to(ROOT)),master_sha256=sha(p),duration=b-a,boundary_method='waveform_inspection_with_adjacent_ASR_context',boundary_reference=str((RUN/'boundary_review_2.png').relative_to(ROOT)),flags=[f for f in u['flags'] if not f.startswith('NO_CLEAR_')],revision_reason='Move boundary into observed silence; preserve complete neighbouring words',asr_text_v01=u.pop('asr_text'),text_similarity_v01=u.pop('text_similarity'))
 write(QA/'cut_revisions_v02.json',list(changed.values()));print(len(changed),'revised masters')
if __name__=='__main__':main()
