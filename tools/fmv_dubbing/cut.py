"""Make versioned, unprocessed masters with per-source ordered word alignment.
ASR and energy are evidence, never human listening approval. Input files are read-only.
"""
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import json, re, subprocess
import numpy as np
from catalog import ROOT, QA, norm, sha, write
RUN=ROOT/'work/fmv-dub/R001_20261029'
RATE=48000

def tokens(s):return [norm(x) for x in s.split() if norm(x)]
def similarity(a,b):return SequenceMatcher(None,a,b,autojunk=False).ratio()
def alignment(expected,actual):
 n,m=len(expected),len(actual);dp=np.zeros((n+1,m+1),np.float32);back=np.zeros((n+1,m+1),np.int8)
 dp[:,0]=np.arange(n+1);dp[0,:]=np.arange(m+1);back[1:,0]=1;back[0,1:]=2
 for i in range(1,n+1):
  for j in range(1,m+1):
   sim=similarity(expected[i-1],actual[j-1])
   cost=0 if sim==1 else 1.4*(1-sim)+0.25
   opts=(dp[i-1,j-1]+cost,dp[i-1,j]+1,dp[i,j-1]+1)
   k=int(np.argmin(opts));dp[i,j]=opts[k];back[i,j]=k
 pairs=[];i=n;j=m
 while i or j:
  k=back[i,j]
  if k==0:pairs.append((i-1,j-1));i-=1;j-=1
  elif k==1:i-=1
  else:j-=1
 return pairs[::-1]
def audio(p):
 return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-ar',str(RATE),'-ac','1','-f','f32le','-']),dtype='<f4').copy()
def quiet_boundary(x,a,b,target):
 a=max(0,a);b=min(len(x)/RATE,b)
 if b<=a:return max(0,min(len(x)/RATE,target)),False
 # Search complete 10 ms windows, preferring silence close to the gap midpoint.
 hop=240;win=480;lo=int(a*RATE);hi=int(b*RATE)
 starts=np.arange(lo,max(lo+1,hi-win+1),hop)
 levels=np.array([np.sqrt(np.mean(x[s:min(s+win,len(x))]**2)) for s in starts])
 floor=min(float(np.min(levels))*2,0.008)
 good=np.where(levels<=max(floor,0.001))[0]
 idx=min(good,key=lambda j:abs((starts[j]+win/2)/RATE-target)) if len(good) else int(np.argmin(levels))
 return (starts[idx]+win/2)/RATE,bool(levels[idx]<0.008)
def save_master(x,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar',str(RATE),'-ac','1','-i','-','-c:a','pcm_s24le',str(path)],input=x.astype('<f4').tobytes(),check=True)
def main():
 catalog=json.loads((QA/'catalog.json').read_text());by_source=defaultdict(list);report=[]
 for u in catalog:by_source[u['source']].append(u)
 for source,units in by_source.items():
  units.sort(key=lambda u:u['production_order']);path=ROOT/source;x=audio(path);duration=len(x)/RATE
  asr_model='large-v3' if units[0]['video'].startswith('05_') else 'medium'
  asr=json.loads((RUN/'asr'/units[0]['video']/(path.stem+'_'+asr_model+'.json')).read_text())
  assert asr['sha256']==sha(path)
  words=[w for s in asr['segments'] for w in s['words'] if norm(w['word'])]
  expected=[];owners=[]
  for i,u in enumerate(units):
   t=tokens(u['text']);expected+=t;owners += [i]*len(t)
  pairs=alignment(expected,[norm(w['word']) for w in words]);assigned=defaultdict(list);matched=defaultdict(list)
  for a,b in pairs:assigned[owners[a]].append(b);matched[owners[a]].append(a)
  bounds=[]
  for i,u in enumerate(units):
   ids=assigned[i]
   if not ids:raise ValueError((u['video'],u['id'],'No bounded alignment; do not fabricate audio'))
   bounds.append((words[min(ids)]['start'],words[max(ids)]['end']))
  cuts=[0.0];quiet=[]
  for i in range(len(units)-1):
   left,right=bounds[i][1],bounds[i+1][0]
   t,ok=quiet_boundary(x,left-0.035,right+0.035,(left+right)/2)
   cuts.append(t);quiet.append(ok)
  cuts.append(duration)
  for i,u in enumerate(units):
   r=dict(u);flags=[]
   if 'source_start' in u:
    a,b=u['source_start'],min(duration,u['source_end']);method=u['boundary_method']
   else:
    a,b=cuts[i:i+2];method='ordered_per_source_ASR_plus_energy_gap'
    # Retain the complete utterance between neighbouring boundaries, including breaths.
    if i>0 and not quiet[i-1]:flags.append('NO_CLEAR_LEADING_GAP')
    if i<len(units)-1 and not quiet[i]:flags.append('NO_CLEAR_TRAILING_GAP')
   if not 0<=a<b<=duration:raise ValueError((u['video'],u['id'],a,b,duration))
   observed=[w for w in words if (w['start']+w['end'])/2>=a and (w['start']+w['end'])/2<b]
   text=' '.join(w['word'].strip() for w in observed);score=similarity(norm(u['text']),norm(text))
   if score<0.92:flags.append('TEXT_DIFFERENCE_REVIEW')
   chunk=x[round(a*RATE):round(b*RATE)]
   if np.max(np.abs(chunk))<0.003:flags.append('LOW_SIGNAL')
   master=RUN/'review_pending'/u['video']/'master'/f"{u['id']}_v01.wav"
   if master.exists():
    decoded=audio(master)
    assert len(decoded)==len(chunk) and np.max(np.abs(decoded-chunk))<2e-7, f'Existing master differs: {master}'
   else:save_master(chunk,master)
   r.update(source_start=a,source_end=b,duration=b-a,boundary_method=method,asr_text=text,text_similarity=round(score,4),master=str(master.relative_to(ROOT)),master_sha256=sha(master),source_sha256=asr['sha256'],asr_model=asr_model,flags=flags,qa_status='REVIEW_PENDING',listened=False)
   report.append(r)
  write(QA/'cuts_v01.json',report)
  print(units[0]['video'],len(units),'masters',flush=True)
 write(QA/'cuts_v01.json',report)
 print('TOTAL',len(report),'flagged',sum(bool(r['flags']) for r in report))
if __name__=='__main__':main()
