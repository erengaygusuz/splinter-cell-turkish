#!/usr/bin/env python3
"""Export source-grounded role/take and line timing proposals without forged listening flags."""
from pipeline import *

def main():
 p=load(Q/'alignment_C.json');by_key={r['candidate_key']:r for r in p};sources={s['key']:s for s in load(Q/'sources.json')};passes=[];timings=[]
 schedule=tsv(B2/'reference/02_EFEKT_ONCE_TEMIZ_SONRA_155_MANTIKSAL_PAS.tsv')
 for item in schedule:
  group=[r for r in p if r['speaker']==item['voice_id'] and r['take']==item['pass']]
  assert len(group)==int(item['expected_lines']),(item, len(group))
  assert [r['id'] for r in group]==item['gameplay_ids'].split(',')
  fragments=[]
  for key in dict.fromkeys(r['source_key'] for r in group if r['source_key']):
   part=[r for r in group if r['source_key']==key];valid=[r for r in part if 'start_sec' in r]
   if valid:fragments.append(dict(source_key=key,source_filename=Path(sources[key]['path']).name,source_file_index=int(key.rsplit('file',1)[1]),start_seconds=min(r['start_sec'] for r in valid),end_seconds=max(r['end_sec'] for r in valid)))
  passes.append(dict(order=item['order'],voice_id=item['voice_id'],take=item['pass'],expected_lines=item['expected_lines'],mapped_lines=sum(bool(r['source_key']) for r in group),gameplay_ids=item['gameplay_ids'],source_fragments=json.dumps(fragments,ensure_ascii=False),speaker_and_lyrics_manually_verified='NO',status='ASR_WAVEFORM_PROPOSAL' if len(fragments)==1 else 'MULTI_SOURCE_OR_UNMAPPED_REVIEW'))
 for template in tsv(B2/'reference/05_KESIM_ZAMANLARI_393_KAYIT_ADAYI_DOLDUR.tsv'):
  key=template['gameplay_id']+'_'+template['take'].lower();r=by_key[key];s=sources.get(r['source_key'],{})
  template.update(source_file_index=int(r['source_key'].rsplit('file',1)[1]) if s else '',source_filename=Path(s['path']).name if s else '',start_seconds=r.get('start_sec',''),end_seconds=r.get('end_sec',''),speaker_and_lyrics_manually_verified='NO',candidate_status='AUTOMATED_CANDIDATE_PENDING_QA' if s else 'TIMING_HOLD',notes=';'.join(r['alignment_flags']))
  timings.append(template)
 assert len(passes)==155 and len(timings)==393
 table(Q/'B002_pass_boundaries_155.tsv',passes);table(Q/'B002_candidate_timings_393.tsv',timings)
 print('Exported 155 role/take passes and 393 candidate timing rows. No manual listening flags fabricated.')
if __name__=='__main__':main()
