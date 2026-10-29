"""Generate a local review index and auditable decision table without approval claims."""
import json,os,html
from pathlib import Path
from collections import Counter
from catalog import ROOT,QA,write
from cut import RUN

def main():
 cuts=json.loads((QA/'cuts_v01.json').read_text());revs=json.loads((QA/'cut_revisions_v02.json').read_text());rr={(r['video'],r['id']):r for r in revs};cuts=[rr.get((r['video'],r['id']),r) for r in cuts]
 asr={(r['video'],r['id']):r for r in json.loads((QA/'cut_asr_v02.json').read_text())};mixes=json.loads((QA/'mixes_v01.json').read_text());mm={m['video']:m for m in mixes};rows=[]
 for r in cuts:
  a=asr[r['video'],r['id']];m=next(u for u in mm[r['video']]['units'] if u['id']==r['id']);flags=list(r['flags'])+m['flags']
  if a['similarity']<.92 and 'TEXT_DIFFERENCE_REVIEW' not in flags:flags.append('CUT_ASR_DIFFERENCE')
  rows.append(dict(video=r['video'],id=r['id'],speaker=r['speaker'],expected=r['text'],cut_transcript=a['text'],cut_similarity=a['similarity'],source=r['source'],source_start=r['source_start'],source_end=r['source_end'],master=r['master'],master_sha256=r['master_sha256'],timeline_start=m['start'],timeline_end=m['end'],reference_end=m['reference_end'],tempo=m['tempo'],effect=m['effect'],flags=flags,decision='REVIEW_PENDING',human_listened=False))
 write(QA/'qa_decisions_v01.json',rows)
 table=['# FMV replik kontrol tablosu','', '192 birim; otomatik kontroller insan dinleme onayı değildir. Kaynak sesler değiştirilmedi.','', '| Video | ID | MP3 kesimi (s) | Görüntü başlangıcı | Tempo | ASR benzerliği | İnceleme | Master |','|---|---|---|---|---|---|---|---|']
 for r in rows:
  link=os.path.relpath(ROOT/r['master'],QA)
  table.append(f"| {r['video']} | {r['id']} | {r['source_start']:.3f}–{r['source_end']:.3f} | {r['timeline_start']:.3f} | {r['tempo']:.3f} | {r['cut_similarity']:.3f} | {', '.join(r['flags']) or 'Dinleme bekliyor'} | [WAV]({link}) |")
 (QA/'QA_TABLE.md').write_text('\n'.join(table)+'\n')
 data=[]
 for m in mixes:
  us=[dict(r,master=os.path.relpath(ROOT/r['master'],RUN)) for r in rows if r['video']==m['video']]
  data.append(dict(name=m['video'],preview='review_pending/'+m['video']+'/preview_v01.mp4',mix=os.path.relpath(ROOT/m['mix'],RUN),rows=us))
 payload=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
 page='''<!doctype html><html lang="tr"><meta charset="utf-8"><title>Splinter Cell — FMV kontrolü</title><style>
body{font:16px system-ui;background:#101820;color:#e4edf3;max-width:1200px;margin:30px auto;padding:0 20px}a{color:#8bd8ff}button,select{padding:9px;margin:4px;background:#263c4a;color:white;border:1px solid #567;border-radius:5px}video{display:block;width:min(100%,800px);max-height:65vh;margin:20px auto;background:black}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #345;text-align:left;vertical-align:top}small{color:#b4c2cb}audio{max-width:250px}summary{cursor:pointer} .warn{color:#ffce82}h1{font-size:26px}textarea{width:95%;background:#20303b;color:white} .status{font-weight:bold;color:#ffce82}</style>
<h1>Splinter Cell — Türkçe FMV kontrolü</h1><p class="status">Kontrol adayları · Oyuna henüz kurulmadı</p><p>Videoyu bütün olarak izleyebilir veya repliğin zamanına atlayabilirsin. WAV oynatıcı temiz ses kesimini çalar. Kararlar bu tarayıcıda saklanır; dışa aktar düğmesiyle dosyaya kaydedebilirsin.</p><select id="sel"></select><button id="export">Kararları dışa aktar</button><video id="player" controls preload="metadata"></video><p id="links"></p><div id="lines"></div>
<script>const DATA=PAYLOAD;
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let decisions=JSON.parse(localStorage.getItem('sc-fmv-r001-review')||'{}');
function save(key,value){decisions[key]={...decisions[key],...value,updated:new Date().toISOString()};localStorage.setItem('sc-fmv-r001-review',JSON.stringify(decisions));}
DATA.forEach((v,i)=>$('#sel').add(new Option(v.name,i)));function show(){const v=DATA[$('#sel').value];$('#player').src=v.preview;$('#links').innerHTML=`<a href="${esc(v.mix)}">48 kHz kayıpsız miks WAV</a> · ${v.rows.length} replik`;$('#lines').innerHTML='<table><thead><tr><th>Replik / görüntü zamanı</th><th>Temiz kesim</th><th>Karar</th></tr></thead><tbody>'+v.rows.map((r,i)=>{let key=v.name+'/'+r.id,d=decisions[key]||{};return `<tr><td><b>${esc(r.id)} · ${esc(r.speaker)}</b> <button data-seek="${r.timeline_start}">${r.timeline_start.toFixed(2)} sn</button><p>${esc(r.expected)}</p><details><summary>Kontrol ayrıntıları</summary><p>Whisper: ${esc(r.cut_transcript)}</p><small>Kaynak kesimi ${r.source_start.toFixed(3)}–${r.source_end.toFixed(3)} sn · Tempo ${r.tempo.toFixed(3)}×</small><p class="warn">${esc(r.flags.join(', ')||'Otomatik ek uyarı yok; dinleme bekliyor.')}</p></details></td><td><audio controls preload="none" src="${esc(r.master)}"></audio></td><td><select data-key="${esc(key)}"><option value="">İncelenmedi</option>${['Doğru','Düzeltilecek','Atla'].map(x=>`<option ${d.decision===x?'selected':''}>${x}</option>`).join('')}</select><textarea data-note="${esc(key)}" placeholder="Not">${esc(d.note||'')}</textarea></td></tr>`}).join('')+'</tbody></table>';document.querySelectorAll('[data-seek]').forEach(b=>b.onclick=()=>{$('#player').currentTime=Number(b.dataset.seek);$('#player').play()});document.querySelectorAll('[data-key]').forEach(s=>s.onchange=()=>save(s.dataset.key,{decision:s.value}));document.querySelectorAll('[data-note]').forEach(s=>s.onchange=()=>save(s.dataset.note,{note:s.value}));}$('#sel').onchange=show;$('#export').onclick=()=>{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(decisions,null,2)],{type:'application/json'}));a.download='fmv_dinleme_kararlari.json';a.click();URL.revokeObjectURL(a.href)};show();</script></html>'''.replace('PAYLOAD',payload)
 (RUN/'index.html').write_text(page)
 print(len(rows),'rows;',sum(bool(r['flags']) for r in rows),'need targeted review')
if __name__=='__main__':main()
