#!/usr/bin/env python3
"""Constrain B002 alignment to evidenced physical source and role/take blocks."""
from pipeline import *

def physical_groups(expected, mapping):
 groups={};seen=[]
 for source,sections in mapping['files'].items():
  groups[source]=[]
  for section in sections:
   rows=[dict(r) for r in expected if r['speaker']==section['speaker'] and r['take']==section['take']]
   assert rows,section
   duplicate=section.get('exclude_duplicate',False)
   for r in rows:
    if duplicate:r.update(candidate_key=r['candidate_key']+'_duplicate_'+source,excluded=True)
    else:seen.append(r['candidate_key'])
   groups[source].append(rows)
 missing=[r for r in expected if r['candidate_key'] not in seen]
 assert len(seen)==len(set(seen)), 'Candidate assigned to multiple source files'
 assert {(r['speaker'],r['take']) for r in missing}=={(r['speaker'],r['take']) for r in mapping['unmapped']}
 return groups,missing

def align_physical():
 expected=[r for r in load(Q/'expected_candidates.json') if r['stage']=='C']
 mapping=load(Q/'physical_source_map_C.json');groups,missing=physical_groups(expected,mapping)
 sources={s['key']:s for s in load(Q/'sources.json') if s['stage']=='C'}
 assert set(groups)==set(sources)
 plans=[];boundaries=[];passes=[];unknown_all=[];duplicates=[]
 for key,blocks in groups.items():
  source=sources[key];d=load(Q/'source_asr'/(key+'.json'));assert d['sha256']==source['sha256']
  words=[dict(w,source_key=key,source_word_index=i) for i,w in enumerate(d['words'])]
  # First identify the role/take span in THIS MP3. Only then align its own lines.
  role_rows=[dict(id=str(i),expected_text=' '.join(r['expected_text'] for r in rows)) for i,rows in enumerate(blocks)]
  role_words,unassigned=common.match_words(role_rows,words)
  plan=[]
  for i,rows in enumerate(blocks):
   local_words=role_words[str(i)]
   matched,unknown=common.match_words([dict(id=r['candidate_key'],expected_text=r['expected_text']) for r in rows],local_words)
   unassigned.extend(unknown)
   for row in rows:
    w=matched[row['candidate_key']];txt=' '.join(x['text'] for x in w);flags=[]
    if not w:flags.append('MISSING_OR_MULTI_SOURCE')
    score=common.score(txt,row['expected_text'])
    if score<75:flags.append('LOW_ALIGNMENT')
    plan.append(dict(**row,source_key=key if w else '',source_asr=txt,source_match=score,word_anchors=w,alignment_flags=flags,role_block_index=i))
  pcm=common.decode(ROOT/source['path']);runs=common.quiet_runs(pcm)
  mapped=[r for r in plan if r['source_key']];rank={r['candidate_key']:i for i,r in enumerate(plan)}
  assert mapped,key
  cuts=[dict(time=0.,method='SOURCE_START',quiet_start=0.,quiet_end=0.)]
  override_path=Q/'boundary_overrides_C.json';overrides=load(override_path) if override_path.exists() else {}
  for left,right in zip(mapped,mapped[1:]):
   b=common.pick_boundary(left['word_anchors'][-1]['end'],right['word_anchors'][0]['start'],runs)
   pair=left['candidate_key']+'|'+right['candidate_key']
   if pair in overrides:b=dict(time=overrides[pair]['time'],method='REVIEWED_WAVEFORM_BOUNDARY',quiet_start='',quiet_end='')
   if rank[right['candidate_key']]!=rank[left['candidate_key']]+1:
    left['alignment_flags'].append('MISSING_NEIGHBOR');right['alignment_flags'].append('MISSING_NEIGHBOR')
   cuts.append(b);boundaries.append(dict(stage='C',source_key=key,left=left['candidate_key'],right=right['candidate_key'],**b))
  cuts.append(dict(time=len(pcm)/RATE,method='SOURCE_END',quiet_start=len(pcm)/RATE,quiet_end=len(pcm)/RATE))
  for i,r in enumerate(mapped):
   a,b=[round(cuts[j]['time']*RATE) for j in (i,i+1)];flags=r['alignment_flags']
   if not 0<=a<b<=len(pcm):flags.append('INVALID_INTERVAL')
   if any('NEEDS_REVIEW' in cuts[j]['method'] for j in (i,i+1)):flags.append('NO_QUIET_BOUNDARY')
   unknown_here=[w for w in unassigned if a/RATE<=w['start']<b/RATE]
   if unknown_here:flags.append('UNASSIGNED_WORDS')
   segment=pcm[max(0,a):max(0,b)];hop=220;lead=trail=0.
   if len(segment)>=hop:
    v=segment[:len(segment)//hop*hop].astype(float).reshape(-1,hop)/32768
    active=np.flatnonzero(np.sqrt(np.mean(v*v,axis=1))>10**(-55/20))
    if len(active):lead=active[0]*hop/RATE*1000;trail=(len(v)-active[-1]-1)*hop/RATE*1000
   if min(lead,trail)<35:flags.append('SHORT_EDGE_MARGIN')
   r.update(source_path=source['path'],source_sha256=source['sha256'],start_sample=a,end_sample=b,start_sec=a/RATE,end_sec=b/RATE,start_method=cuts[i]['method'],end_method=cuts[i+1]['method'],leading_quiet_ms=round(lead,1),trailing_quiet_ms=round(trail,1),unknown_words=unknown_here)
  for i,rows in enumerate(blocks):
   members=[r for r in mapped if r['role_block_index']==i]
   passes.append(dict(source_key=key,speaker=rows[0]['speaker'],take=rows[0]['take'],excluded_duplicate=rows[0]['excluded'],expected_lines=len(rows),mapped_lines=len(members),start_sec=min((r['start_sec'] for r in members),default=''),end_sec=max((r['end_sec'] for r in members),default=''),source_sha256=source['sha256'],basis='SOURCE_TRANSCRIPT_ROLE_THEN_LINE',listened='NO'))
  plans.extend(r for r in plan if not r['excluded']);duplicates.extend(r for r in plan if r['excluded']);unknown_all.extend(unassigned)
 for r in missing:plans.append(dict(**r,source_key='',source_asr='',source_match=0,word_anchors=[],alignment_flags=['SOURCE_SECTION_NOT_LOCATED']))
 order={r['candidate_key']:i for i,r in enumerate(expected)};plans.sort(key=lambda r:order[r['candidate_key']])
 assert len(plans)==393 and len({r['candidate_key'] for r in plans})==393
 save(Q/'alignment_C.json',plans);save(Q/'unassigned_C.json',unknown_all);save(Q/'excluded_duplicate_sections_C.json',duplicates)
 table(Q/'physical_pass_boundaries_C.tsv',passes)
 table(Q/'boundaries_C.tsv',boundaries,['stage','source_key','left','right','time','method','quiet_start','quiet_end'])
 print('Source/role-constrained C:',len(plans),'catalogue candidates;',len(duplicates),'excluded duplicate lines; flags',Counter(f for r in plans for f in r['alignment_flags']),flush=True)

if __name__=='__main__':align_physical()
