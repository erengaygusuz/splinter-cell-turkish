#!/usr/bin/env python3
"""Align ordered utterances to word timestamps; write only unapproved PCM candidates."""
from pipeline import *
import os

def align(stage):
 if stage=='C':
  from physical_alignment import align_physical
  return align_physical()
 allrows=load(Q/'expected_candidates.json');sources=load(Q/'sources.json')
 expected=[r for r in allrows if r['stage']==stage];rank={r['candidate_key']:i for i,r in enumerate(expected)}
 groups=list(dict.fromkeys(r['group'] for r in expected))
 plans=[];unassigned=[];boundaries=[]
 for group in groups:
  rows=[r for r in expected if r['group']==group]
  srcs=[s for s in sources if s['stage']==stage and (stage!='A' or s['key']==group)]
  if any(not (Q/'source_asr'/(s['key']+'.json')).exists() for s in srcs):
   print('Waiting for full source transcripts',group);continue
  words=[]
  for s in srcs:
   d=load(Q/'source_asr'/(s['key']+'.json'));assert d['sha256']==s['sha256']
   words.extend(dict(w,source_key=s['key']) for w in d['words'])
  match,unknown=common.match_words([dict(id=r['candidate_key'],expected_text=r['expected_text']) for r in rows],words)
  unassigned.extend(dict(w,group=group) for w in unknown)
  plan=[]
  for row in rows:
   w=match[row['candidate_key']];keys=list(dict.fromkeys(x['source_key'] for x in w));notes=[]
   if len(keys)!=1:notes.append('MISSING_OR_MULTI_SOURCE')
   if len(keys)==1 and row['source_hint'] and keys[0]!=row['source_hint']:notes.append('WRONG_SOURCE')
   text=' '.join(x['text'] for x in w);score=common.score(text,row['expected_text'])
   if score<75:notes.append('LOW_ALIGNMENT')
   plan.append(dict(**row,source_key=keys[0] if len(keys)==1 else '',source_asr=text,source_match=score,word_anchors=w,alignment_flags=notes))
  for s in srcs:
   pcm=common.decode(ROOT/s['path']);runs=common.quiet_runs(pcm)
   subset=[r for r in plan if r['source_key']==s['key']]
   if not subset:continue
   cuts=[dict(time=0.,method='SOURCE_START',quiet_start=0.,quiet_end=0.)]
   for left,right in zip(subset,subset[1:]):
    boundary=common.pick_boundary(left['word_anchors'][-1]['end'],right['word_anchors'][0]['start'],runs)
    override_path=Q/f'boundary_overrides_{stage}.json'
    overrides=load(override_path) if override_path.exists() else {}
    override=overrides.get(left['candidate_key']+'|'+right['candidate_key'])
    if override:boundary=dict(time=override['time'],quiet_start='',quiet_end='',method='REVIEWED_WAVEFORM_BOUNDARY')
    gap=rank[right['candidate_key']]-rank[left['candidate_key']]!=1
    if gap:
     left['alignment_flags'].append('MISSING_NEIGHBOR');right['alignment_flags'].append('MISSING_NEIGHBOR')
    cuts.append(boundary)
    boundaries.append(dict(stage=stage,source_key=s['key'],left=left['candidate_key'],right=right['candidate_key'],**boundary))
   cuts.append(dict(time=len(pcm)/RATE,method='SOURCE_END',quiet_start=len(pcm)/RATE,quiet_end=len(pcm)/RATE))
   for i,r in enumerate(subset):
    a,b=round(cuts[i]['time']*RATE),round(cuts[i+1]['time']*RATE)
    flags=r['alignment_flags']
    if not 0<=a<b<=len(pcm):flags.append('INVALID_INTERVAL')
    if any('NEEDS_REVIEW' in cuts[j]['method'] for j in (i,i+1)):flags.append('NO_QUIET_BOUNDARY')
    # Unassigned source words within a proposed clip are retained as explicit review evidence.
    unknown_here=[w for w in unknown if w['source_key']==s['key'] and a/RATE<=w['start']<b/RATE]
    if unknown_here:flags.append('UNASSIGNED_WORDS')
    segment=pcm[max(0,a):max(0,b)]
    lead=trail=0
    if len(segment):
     hop=220;v=segment[:len(segment)//hop*hop].astype(float).reshape(-1,hop)/32768
     active=np.flatnonzero(np.sqrt(np.mean(v*v,axis=1))>10**(-55/20))
     if len(active):lead=active[0]*hop/RATE*1000;trail=(len(v)-active[-1]-1)*hop/RATE*1000
     if min(lead,trail)<35:flags.append('SHORT_EDGE_MARGIN')
    r.update(source_path=s['path'],source_sha256=s['sha256'],start_sample=a,end_sample=b,start_sec=a/RATE,end_sec=b/RATE,start_method=cuts[i]['method'],end_method=cuts[i+1]['method'],leading_quiet_ms=round(lead,1),trailing_quiet_ms=round(trail,1),unknown_words=unknown_here)
  plans.extend(plan)
 save(Q/f'alignment_{stage}.json',plans);save(Q/f'unassigned_{stage}.json',unassigned)
 table(Q/f'boundaries_{stage}.tsv',boundaries,['stage','source_key','left','right','time','method','quiet_start','quiet_end'])
 print('Aligned',stage,len(plans),'rows; flags',Counter(f for r in plans for f in r['alignment_flags']),flush=True)

def make_cuts(stage,version='v01',only=None):
 import re
 assert re.fullmatch(r'v\d{2,}',version),version
 plan=load(Q/f'alignment_{stage}.json');sources={s['key']:s for s in load(Q/'sources.json')};outputs=[]
 previous=tsv(Q/f'cuts_{stage}.tsv') if only else []
 if only:
  assert set(only)<={r['candidate_key'] for r in plan}
  immutable_json(Q/f'cuts_{stage}_before_{version}.json',previous)
  plan=[r for r in plan if r['candidate_key'] in only]
 for key in dict.fromkeys(r['source_key'] for r in plan if r['source_key']):
  source=sources[key];p=ROOT/source['path'];assert sha(p)==source['sha256']
  width=3 if source['codec']=='pcm_s24le' else 2
  raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(p),'-ac','1','-ar',str(RATE),'-f',f's{width*8}le','-c:a',f'pcm_s{width*8}le','-'])
  for r in [r for r in plan if r['source_key']==key]:
   if r['excluded'] or any(f in r['alignment_flags'] for f in ['MISSING_OR_MULTI_SOURCE','WRONG_SOURCE','MISSING_NEIGHBOR','INVALID_INTERVAL']):continue
   a,b=r['start_sample'],r['end_sample'];assert 0<=a<b<=len(raw)//width
   suffix='' if stage!='C' else ('_fx' if r['take']=='FX_FIRST' else '_clean')
   out=ROOT/r['output_dir']/(r['id']+suffix+'_'+version+'.wav');out.parent.mkdir(parents=True,exist_ok=True)
   payload=raw[a*width:b*width]
   if out.exists():
    with wave.open(str(out),'rb') as w:assert w.getparams()[:3]==(1,width,RATE) and w.readframes(w.getnframes())==payload, str(out)+' already differs; use v02'
   else:
    with out.open('xb') as f:
     with wave.open(f,'wb') as w:w.setnchannels(1);w.setsampwidth(width);w.setframerate(RATE);w.writeframes(payload)
   outputs.append(dict(candidate_key=r['candidate_key'],id=r['id'],stage=stage,speaker=r['speaker'],take=r['take'],source_path=r['source_path'],source_sha256=r['source_sha256'],start_sample=a,end_sample=b,start_sec=a/RATE,end_sec=b/RATE,expected_text=r['expected_text'],wav_path=rel(out),sha256=sha(out),sample_rate=RATE,sample_width=width,channels=1,source_pcm_identical=True,version=version,qa_status='UNAPPROVED_AUTO_CANDIDATE'))
 immutable_json(Q/f'cuts_{stage}_{version}.json',outputs)
 if only:
  replacement={r['candidate_key']:r for r in outputs}
  assert set(replacement)==set(only),'Requested revision could not be cut'
  outputs=[replacement.get(r['candidate_key'],r) for r in previous]
 table(Q/f'cuts_{stage}.tsv',outputs);print('Wrote/preserved',len(outputs),stage,'unapproved WAV candidates',flush=True)

def clip_asr(stage,worker_index=0,workers=1):
 assert 0<=worker_index<workers
 cuts=tsv(Q/f'cuts_{stage}.tsv');model=None
 for r in cuts[worker_index::workers]:
  p=ROOT/r['wav_path'];assert sha(p)==r['sha256'];out=Q/'clip_asr'/(r['candidate_key']+'_'+r['version']+'.json')
  if out.exists():assert load(out)['sha256']==r['sha256'];continue
  if model is None:model=get_model()
  d=transcribe_one(model,p,r['sha256'],out)
 print('Isolated ASR finished:',stage,'worker',worker_index,'of',workers,len(cuts[worker_index::workers]),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['align','cut','clip_asr']);p.add_argument('--stage',required=True,choices=['A','B','C']);p.add_argument('--version',default='v01');p.add_argument('--only',nargs='+');p.add_argument('--worker-index',type=int,default=0);p.add_argument('--workers',type=int,default=1);a=p.parse_args()
 if a.mode=='cut':make_cuts(a.stage,a.version,a.only)
 elif a.mode=='clip_asr':clip_asr(a.stage,a.worker_index,a.workers)
 else:align(a.stage)
