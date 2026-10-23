#!/usr/bin/env python3
"""Build a per-candidate QA ledger and an offline, exportable listening review page."""
from pipeline import *
import html,os

def main():
 expected=load(Q/'expected_candidates.json');rows=[];plans={};cuts={}
 for stage in 'ABC':
  if (Q/f'alignment_{stage}.json').exists():plans.update({r['candidate_key']:r for r in load(Q/f'alignment_{stage}.json')})
  if (Q/f'cuts_{stage}.tsv').exists():cuts.update({r['candidate_key']:r for r in tsv(Q/f'cuts_{stage}.tsv')})
 for e in expected:
  if e['excluded']:continue
  key=e['candidate_key'];p=plans.get(key,{});c=cuts.get(key,{});f=Q/'clip_asr'/(key+'_'+c.get('version','v01')+'.json');a=load(f) if f.exists() else {}
  if a:assert a['sha256']==c['sha256']
  score=common.score(e['expected_text'],a.get('text','')) if a else ''
  flags=p.get('alignment_flags',[]).copy()
  if not c:flags.append('CUT_NOT_AVAILABLE')
  elif not a:flags.append('ISOLATED_ASR_PENDING')
  elif score!=100:
   compact_expected=common.norm(e['expected_text']).replace(' ','')
   compact_asr=common.norm(a['text']).replace(' ','')
   if compact_expected!=compact_asr:flags.append('ASR_DIFFERENCE')
  if e['speaker_hold']:flags.append('SPEAKER_IDENTITY_HOLD')
  if e['stage']=='C' and e['take'] in ['FX_FIRST','CLEAN']:flags.append('CHANNEL_FX_HOLD')
  status='TECHNICAL_PASS_PENDING_GAME_TEST' if not flags else 'REVIEW_REQUIRED'
  rows.append(dict(candidate_key=key,id=e['id'],stage=e['stage'],speaker=e['speaker'],take=e['take'],expected_text=e['expected_text'],source_path=c.get('source_path',''),source_sha256=c.get('source_sha256',''),start_sec=c.get('start_sec',''),end_sec=c.get('end_sec',''),wav_path=c.get('wav_path',''),sha256=c.get('sha256',''),source_match=p.get('source_match',''),isolated_asr=a.get('text',''),isolated_match=score,leading_quiet_ms=p.get('leading_quiet_ms',''),trailing_quiet_ms=p.get('trailing_quiet_ms',''),qa_status=status,flags=';'.join(flags),listened='NO',in_game_review='NOT_TESTED',approved='NO'))
 assert len(rows)==714 and len({r['id'] for r in rows})==678
 table(Q/'candidate_qa_714.tsv',rows);table(Q/'review_required.tsv',[r for r in rows if r['flags']],list(rows[0]))
 selected=[]
 for uid in dict.fromkeys(r['id'] for r in rows):
  group=[r for r in rows if r['id']==uid]
  # Clean is merely the default preview for unresolved FX pairs, never an install decision.
  r=next((r for r in group if r['take']=='CLEAN'),group[0]).copy()
  r['selection_status']='PROVISIONAL_NOT_INSTALL_APPROVED'
  selected.append(r)
 table(Q/'selected_cuts_678.tsv',selected)
 summary=dict(expected_unique_ids=678,expected_usable_candidates=714,available_candidates=len(cuts),isolated_asr_completed=sum(bool(r['isolated_asr']) for r in rows),technical_pass=sum(not r['flags'] for r in rows),review_required=sum(bool(r['flags']) for r in rows),cut_missing=sum(not r['wav_path'] for r in rows),stage_counts={s:dict(expected=sum(r['stage']==s for r in rows),cut=sum(r['stage']==s and bool(r['wav_path']) for r in rows),asr=sum(r['stage']==s and bool(r['isolated_asr']) for r in rows)) for s in 'ABC'},approved=0,installed_new=0,flags=dict(Counter(f for r in rows for f in r['flags'].split(';') if f)))
 save(Q/'progress.json',summary)
 page='''<!doctype html><html lang="tr"><meta charset="utf-8"><title>678 yeni replik — kesim kontrolü</title><style>body{font:16px system-ui;max-width:1000px;margin:24px auto;padding:16px;background:#edf1f5}article{background:white;padding:16px;margin:12px 0;border-radius:8px}audio{width:100%}input,select,button{padding:8px}header{position:sticky;top:0;background:#edf1f5;padding:12px}small{overflow-wrap:anywhere}p{line-height:1.4}</style><h1>678 yeni replik / 714 aday</h1><p>FX/temiz alternatifler ayrı tutulur; aynı oyun ID'sine yalnız bir sürüm kurulabilir. Buradaki seçimler inceleme kaydıdır; dosya veya DLL değiştirmez. Dinleme yapılmış kabul edilmez. Varsayılan görünüm belirsiz kayıtları gösterir.</p><header><input id="search" placeholder="ID, karakter veya metin"><label><input id="all" type="checkbox"> Tüm adayları göster</label> <button id="export">Kontrol sonuçlarını indir</button><span id="count"></span></header>'''
 esc=html.escape
 for r in rows:
  key=r['candidate_key'];page+=f'<article data-key="{key}" data-review="{bool(r["flags"])}" data-search="{esc(key+" "+r["speaker"]+" "+r["expected_text"],quote=True)}"><h3>{key} · {r["speaker"]}</h3><p>{esc(r["expected_text"])}</p><p>{esc(r["flags"] or r["qa_status"])}</p>'
  if r['wav_path']:
   wav=os.path.relpath(ROOT/r['wav_path'],Q);src=os.path.relpath(ROOT/r['source_path'],Q);start=max(0,float(r['start_sec'])-.5);end=float(r['end_sec'])+.5
   page+=f'<audio controls preload="none" src="{esc(wav,quote=True)}"></audio><p><a href="{esc(src,quote=True)}#t={start:.3f},{end:.3f}">Kaynak ve komşu bağlamı</a> · {r["start_sec"]}–{r["end_sec"]} sn</p><p>Whisper: {esc(r["isolated_asr"])} ({r["isolated_match"]}%)</p>'
  page+='<select class="decision"><option>PENDING</option><option>PASSED</option><option>RECUT_REQUIRED</option><option>SPEAKER_IDENTITY_HOLD</option><option>CHANNEL_FX_HOLD</option><option>RETAKE_REQUIRED</option></select> <input class="note" placeholder="Kontrol notu"><small> Dinleyerek verdiğin karar</small></article>'
 page+='''<script>const store='sc678-review-v1', saved=JSON.parse(localStorage.getItem(store)||'{}'), cards=[...document.querySelectorAll('article')];function persist(){const data={};for(const c of cards)data[c.dataset.key]={decision:c.querySelector('select').value,note:c.querySelector('.note').value};localStorage.setItem(store,JSON.stringify(data));return data}for(const c of cards){const x=saved[c.dataset.key];if(x){c.querySelector('select').value=x.decision;c.querySelector('.note').value=x.note}c.addEventListener('change',persist)}function filter(){const q=document.querySelector('#search').value.toLocaleLowerCase('tr'),all=document.querySelector('#all').checked;let n=0;for(const c of cards){c.hidden=(!all&&c.dataset.review==='False')||!c.dataset.search.toLocaleLowerCase('tr').includes(q);if(!c.hidden)n++}document.querySelector('#count').textContent=' '+n+' aday'}document.querySelector('#search').oninput=filter;document.querySelector('#all').onchange=filter;filter();document.querySelector('#export').onclick=()=>{const data=persist(),blob=new Blob([JSON.stringify({schema:'sc678-review-v1',decisions:data},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='remaining678_review.json';a.click();URL.revokeObjectURL(a.href)};document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')for(const a of document.querySelectorAll('audio'))if(a!==e.target)a.pause()},true)</script></html>'''
 (Q/'listen.html').write_text(page,encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
