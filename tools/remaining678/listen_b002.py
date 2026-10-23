#!/usr/bin/env python3
"""Local, review-only B002 dialogue listening UI. Python stdlib; no game changes.

Reads the immutable 393 B002 mapping and corrected source-constrained WAV cuts.
Adapted from the team listening tool in Downloads; original v01 remains untouched.
Writes ONLY dubbing/figurants/gameplay/batches/B002_20261022/qa_review/*.json[l]/tsv.
'Correct' is a human listening opinion, NEVER approval for game-ready cutting.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import threading
import urllib.parse
import webbrowser
from collections import Counter
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

REL = Path('dubbing/figurants/gameplay/batches/B002_20261022')
GOOD = {'STRONG_ANCHOR_REVIEW', 'PARTIAL_ANCHOR_REVIEW'}
UNCERTAIN = {'NO_MATCH', 'WEAK_ANCHOR_REVIEW', 'CROSS_FILE_REVIEW'}
STATUS = GOOD | UNCERTAIN
KEYS = ('take_order', 'voice_id', 'take', 'line_in_voice', 'gameplay_id', 'expected_text', 'channel')
DECISIONS = {'DOGRU', 'YANLIS', 'ATLA'}


def load_tsv(path: Path) -> list[dict]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def make_entries(batch: Path) -> list[dict]:
    project=batch.parents[4]
    qa=project/'dubbing/qa/remaining678_v1_20261023'
    rows=load_tsv(batch/'reference/05_KESIM_ZAMANLARI_393_KAYIT_ADAYI_DOLDUR.tsv')
    cuts={r['candidate_key']:r for r in load_tsv(qa/'cuts_C.tsv')}
    plans={r['candidate_key']:r for r in json.loads((qa/'alignment_C.json').read_text())}
    ledger={r['candidate_key']:r for r in load_tsv(qa/'candidate_qa_714.tsv')}
    old_path=batch/'qa_review/b002_dinleme_kararlari_v01.json'
    previous=json.loads(old_path.read_text()) if old_path.exists() else {}
    entries=[]
    assert len(rows)==393
    for row in rows:
        key=f"{row['voice_id']}|{row['gameplay_id']}|{row['take']}"
        ck=row['gameplay_id']+'_'+row['take'].lower()
        c=cuts.get(ck);plan=plans[ck];qa_row=ledger[ck];clips=[]
        flags=[f for f in qa_row['flags'].split(';') if f]
        if c:
            wav=(project/c['wav_path']).resolve()
            assert wav.is_relative_to(batch) and wav.is_file() and not wav.is_symlink()
            assert sha256(wav)==c['sha256']
            assert c['source_sha256']==plan['source_sha256']
            assert c['speaker']==row['voice_id'] and c['take']==row['take'] and c['id']==row['gameplay_id']
            assert float(c['start_sec'])==plan['start_sec'] and float(c['end_sec'])==plan['end_sec']
            clips=[dict(rel=str(wav.relative_to(batch)),sha256=c['sha256'],kind='CORRECTED_CUT',duration=round(float(c['end_sec'])-float(c['start_sec']),3),source_index=int(plan['source_key'].rsplit('file',1)[1]),source_filename=Path(c['source_path']).name)]
        entries.append(dict(key=key,voice_id=row['voice_id'],id=row['gameplay_id'],take=row['take'],
            line_in_voice=row['line_in_voice'],role_order=row['take_order'],text=row['expected_text'],channel=row['channel'],original_slot=row['original_slot_seconds'],
            anchor_status='SOURCE_NOT_LOCATED' if not c else qa_row['qa_status'],flags=flags,suspicious=bool(flags),
            priority=bool(previous.get(key)) or bool(flags),context_only=False,clips=clips,
            notes=qa_row['isolated_asr'],previous=previous.get(key),revision=c['version'] if c else 'unmapped'))
    assert len({e['key'] for e in entries})==393
    return entries


class ReviewStore:
    def __init__(self,batch:Path,entries:list[dict]):
        self.root=batch/'qa_review'
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'b002_dinleme_kararlari_v02.json'
        self.tsv=self.root/'b002_dinleme_kararlari_v02.tsv'
        self.events=self.root/'b002_dinleme_gecmisi_v02.jsonl'
        self.bykey={e['key']:e for e in entries}
        self.allowed=set(self.bykey)
        keys=self.allowed
        self.lock=threading.Lock()
        self.data={}
        if self.path.is_file():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or any(k not in keys for k in data):
                raise RuntimeError('Eski karar dosyasındaki anahtarlar yeni envanterle uyumsuz.')
            self.data={k:v for k,v in data.items() if v.get('audio_sha256')==self.fingerprint(k)}

    def fingerprint(self,key):
        return ','.join(c['sha256'] for c in self.bykey[key]['clips'])

    def snapshot(self):
        with self.lock:return dict(self.data)

    @staticmethod
    def replace_atomic(path:Path,text:str):
        fd,tmp=tempfile.mkstemp(prefix='.qa-save-',dir=path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
                f.write(text);f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def set_decision(self,key:str,decision:str,note:str):
        if key not in self.allowed or decision not in DECISIONS:
            raise ValueError('Bilinmeyen kayıt veya karar')
        if not isinstance(note,str) or len(note)>900:
            raise ValueError('Not 900 karakteri aşamaz')
        if decision=='DOGRU' and not self.bykey[key]['clips']:
            raise ValueError('Kaynak bulunamadı; başka kayıtla onaylanamaz')
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry={'decision':decision,'note':note.strip(),'reviewed_at':now,
               'status':'USER_LISTENING_CORRECTED_CUT_NOT_GAME_APPROVAL',
               'audio_sha256':self.fingerprint(key)}
        with self.lock:
            event={'key':key,**entry}
            # Append-only log is written first; if snapshot fails, it can be recovered.
            with self.events.open('a',encoding='utf-8') as f:
                f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
            self.data[key]=entry
            self.replace_atomic(self.path,json.dumps(self.data,ensure_ascii=False,indent=2)+'\n')
            stream=io.StringIO(newline='')
            fields=['key','decision','note','reviewed_at','status','audio_sha256']
            writer=csv.DictWriter(stream,fieldnames=fields,delimiter='\t',lineterminator='\n')
            writer.writeheader()
            for k,v in sorted(self.data.items()):writer.writerow({'key':k,**v})
            self.replace_atomic(self.tsv,stream.getvalue())
        return entry


HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Splinter Cell · Ses dinleme kontrolü</title>
<style>
:root{color-scheme:dark;font:16px system-ui,-apple-system,Segoe UI,sans-serif;background:#0e1217;color:#e8edf3}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top left,#172735 0%,#0e1217 55%);min-height:100vh}
main{max-width:970px;margin:auto;padding:22px 18px 55px}.head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
h1{font-size:1.5rem;letter-spacing:-.03em;margin:.5rem 0}h2{font-size:1.35rem;margin:0}.muted{color:#abb5c2}small{font-size:.78rem}
.panel{background:#17202b;border:1px solid #293849;border-radius:15px;padding:21px;margin-top:16px;box-shadow:0 9px 30px #0003}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.grow{flex:1}.pill{display:inline-flex;border:1px solid #39495a;background:#22303f;color:#c8d4e3;border-radius:99px;padding:4px 10px;font-size:.82rem}
select,textarea,button{font:inherit;color:inherit;border-radius:9px;border:1px solid #526273;background:#243244;padding:10px 13px}
select{min-width:200px}button{cursor:pointer}button:hover{filter:brightness(1.18)}button:disabled{opacity:.45;cursor:not-allowed}
button.primary{background:#167c66;border-color:#269a80}button.reject{background:#983e48;border-color:#bc5864}button.secondary{background:#2d3d50}
button.active{outline:2px solid #e1c375} .buttons{display:flex;gap:9px;flex-wrap:wrap}.buttons button{flex:1;min-width:145px;padding:13px 12px;font-weight:650}
.progress{height:7px;background:#354352;border-radius:20px;overflow:hidden;margin-top:12px}.fill{height:100%;background:#3cb798;width:0;transition:width .15s}
.quote{white-space:pre-wrap;line-height:1.7;font-size:1.24rem;padding:18px 20px;background:#0e161f;border-left:3px solid #7bbaac;border-radius:5px;margin:16px 0}
audio{width:100%;margin:12px 0 3px}textarea{width:100%;min-height:72px;resize:vertical;background:#111a25}
.clip{border:1px solid #304356;border-radius:11px;padding:12px 14px;margin:10px 0}.warning{color:#ffcf80}
label.toggle{display:inline-flex;gap:7px;align-items:center;color:#bdc9d6}input[type=checkbox]{width:16px;height:16px;accent-color:#22ab8d}
.info{line-height:1.5;padding:11px 13px;background:#222e3b;border-radius:9px}.tiny{font-size:.79rem}
@media(max-width:600px){.buttons button{min-width:calc(50% - 9px)}.quote{font-size:1.08rem}.panel{padding:15px}}
</style></head>
<body><main>
<div class="head"><h1>🎧 Splinter Cell · Türkçe ses kontrolü</h1><span class="pill">B002 · Sadece dinleme QA</span></div>
<p class="muted">Metni oku, kaydı dinle, <strong>Doğru / Yanlış / Atla</strong> seç. Kararlar yerel projeye kaydedilir. Oyuna kurulum veya kesim onayı yapılmaz.</p>
<div class="panel">
  <div class="row"><label for="scope">Göster</label><select id="scope"><option value="uncertain">Düzeltilenler ve inceleme gerekenler</option><option value="suspicious">Tüm şüpheli / sınır riski</option><option value="all">Tüm 393 kayıt</option></select><label class="toggle"><input type="checkbox" id="unreviewed"/>Yalnız incelenmemiş</label><label class="toggle"><input type="checkbox" id="advance" checked/>Karardan sonra ilerle</label></div>
  <div class="row" style="justify-content:space-between;margin-top:15px"><strong id="progressText">Yükleniyor…</strong><small class="muted" id="global"></small></div><div class="progress"><div class="fill" id="fill"></div></div>
</div>
<section class="panel" id="card" hidden>
 <div class="row"><span class="pill" id="id"></span><span class="pill" id="take"></span><span class="pill" id="status"></span><span class="grow"></span><span class="muted" id="position"></span></div>
 <div style="margin-top:17px"><h2 id="who"></h2><div class="muted tiny" id="meta"></div></div>
 <div class="quote" id="text"></div>
 <div class="info" id="warn"></div>
 <div id="audioClips"></div>
 <div class="row" style="margin:10px 0"><label for="speed">Hız</label><select id="speed" style="min-width:90px"><option value="0.8">0,8×</option><option value="1" selected>1,0×</option><option value="1.2">1,2×</option></select><span class="grow"></span><small class="muted">Boşluk: oynat/durdur · D: Doğru · Y: Yanlış · S: Atla</small></div>
 <label for="note" class="muted">İsteğe bağlı not (kesik hece, yanlış ses, eksik replik vb.)</label><textarea id="note" maxlength="900" placeholder="Sorun varsa yazabilirsin..."></textarea>
 <div class="buttons" style="margin-top:15px"><button id="good" class="primary">✓ Doğru (D)</button><button id="bad" class="reject">✕ Yanlış (Y)</button><button id="skip" class="secondary">↪ Atla (S)</button></div>
 <div class="row" style="justify-content:space-between;margin-top:15px"><button id="prev">← Önceki</button><span id="saved" class="tiny muted">Henüz karar yok</span><button id="next">Sonraki →</button></div>
</section>
<section class="panel" id="empty" hidden><h2>Bu grupta gösterilecek kayıt kalmadı.</h2><p>Diğer kayıtları incelemek için üstteki filtreyi değiştirebilirsin. Kararlar proje içinde korunuyor.</p></section>
<p class="muted tiny">Güvenlik: Bu arayüz yalnız 127.0.0.1 üzerinde çalışır. Dinleme kararı, konuşmacı kimliği ve kesim sınırları için resmi QA onayı değildir. Bu sürüm yalnız kaynak eşlemesi bulunan replik kesimlerini oynatır. Eski kararlar v01 dosyalarında korunur; yeni kararlar ses hash’iyle v02 dosyalarına kaydedilir.</p>
</main>
<script>
const $ = id=>document.getElementById(id);
let entries=[], decisions={}, shown=[], pointer=0, saving=false;
function key(e){return e.key}
function sortPriority(a,b){
  const ranks={SOURCE_NOT_LOCATED:0,REVIEW_REQUIRED:1,TECHNICAL_PASS_PENDING_GAME_TEST:2};
  if(Boolean(a.previous)!==Boolean(b.previous))return a.previous?-1:1;
  return (ranks[a.anchor_status]-ranks[b.anchor_status])||Number(a.role_order)-Number(b.role_order)||Number(a.line_in_voice)-Number(b.line_in_voice);
}
function decideClass(e){const d=decisions[e.key]?.decision;return d==='DOGRU'?'Doğru':d==='YANLIS'?'Yanlış':d==='ATLA'?'Atlandı':''}
function filterData(keepKey){
  const type=$('scope').value, un=$('unreviewed').checked;
  shown=entries.filter(x=>type==='all'||(type==='uncertain'?x.priority:x.suspicious)).filter(x=>!un||!decisions[x.key]);
  shown.sort(sortPriority);
  let found=shown.findIndex(x=>x.key===keepKey);
  pointer=found>=0?found:Math.min(pointer,Math.max(0,shown.length-1));
  show();
}
function stats(){
  const done=Object.keys(decisions).length, n=shown.length;
  $('progressText').textContent=n?`${pointer+1} / ${n} · ${$('scope').selectedOptions[0].text}`:'Bu filtrede kayıt yok';
  $('global').textContent=`Toplam ${done} / ${entries.length} karar · ${Object.values(decisions).filter(x=>x.decision==='YANLIS').length} yanlış`;
  $('fill').style.width=`${Math.round(100*done/Math.max(1,entries.length))}%`;
}
function show(){
  stats();
  const e=shown[pointer]; $('card').hidden=!e; $('empty').hidden=!!e;if(!e)return;
  $('id').textContent=e.id; $('take').textContent=e.take==='FX_FIRST'?'EFECTLİ kayıt':'TEMİZ kayıt';
  $('status').textContent=e.anchor_status; $('position').textContent=`${pointer+1}/${shown.length}`;
  $('who').textContent=`${e.voice_id} · ${e.id}`;
  $('meta').textContent=`Rol sırası ${e.role_order} · Karakter içi ${e.line_in_voice}. replik · Orijinal slot ${e.original_slot} sn · ${e.channel}`;
  $('text').textContent=e.text;
  $('warn').textContent=e.clips.length?`Kaynak ve karakter bölümünden ayrılan ${e.revision} kesimi. ${e.flags.length?'Kontrol: '+e.flags.join(' · '):'Metin ve sınır kontrolleri tamamlandı.'}`:'Kaynak bölümü bulunamadı. Başka karakter veya MP3 sesi oynatılmaz.';
  if(e.previous)$('warn').textContent+=' Önceki sürümdeki notun: '+e.previous.note+' (Yeni kesime otomatik uygulanmaz.)';
  if(e.notes)$('warn').textContent+=' Whisper: '+e.notes;
  $('warn').className='info '+(e.suspicious?'warning':'');
  const box=$('audioClips');box.replaceChildren();
  if(!e.clips.length){const p=document.createElement('p');p.className='warning';p.textContent='Bu kayıt için dinleme klibi bulunamadı. “Atla” seçebilir veya not bırakabilirsin.';box.append(p);}
  for(let i=0;i<e.clips.length;i++){
   const c=e.clips[i],div=document.createElement('div'); div.className='clip';
   const name=document.createElement('div'); name.className='tiny muted';
   name.textContent=`${i+1}. Düzeltilmiş replik kesimi · MP3 #${c.source_index} · ${c.duration} sn · ${c.source_filename||''}`;
   const a=document.createElement('audio');a.controls=true;a.preload='none'; a.src=`/audio?key=${encodeURIComponent(e.key)}&part=${i}`;a.playbackRate=Number($('speed').value);
   div.append(name,a);box.append(div);
  }
  $('note').value=decisions[e.key]?.note||'';
  $('saved').textContent=decisions[e.key]?`Son karar: ${decideClass(e)} · ${new Date(decisions[e.key].reviewed_at).toLocaleString('tr-TR')}`:'Henüz karar yok';
  for(const [id,v] of [['good','DOGRU'],['bad','YANLIS'],['skip','ATLA']]) $(''+id).classList.toggle('active',decisions[e.key]?.decision===v);
  $('good').disabled=!e.clips.length;
  $('prev').disabled=pointer===0;$('next').disabled=pointer>=shown.length-1;
}
async function save(decision){
  const e=shown[pointer];if(!e||saving||(decision==='DOGRU'&&!e.clips.length))return; saving=true;
  for(const id of ['good','bad','skip'])$(id).disabled=true;
  try {
    const response=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:e.key,decision,note:$('note').value})});
    if(!response.ok)throw Error(await response.text());
    const obj=await response.json();decisions[e.key]=obj.saved;
    if($('unreviewed').checked){filterData();}
    else if($('advance').checked && pointer<shown.length-1){pointer++;show();}
    else show();
  }catch(err){alert('Kaydedilemedi: '+err.message)}
  finally{saving=false;for(const id of ['good','bad','skip'])$(id).disabled=false;$('good').disabled=!shown[pointer]?.clips.length;}
}
function navigation(delta){pointer=Math.max(0,Math.min(shown.length-1,pointer+delta));show()}
$('scope').addEventListener('change',()=>filterData());$('unreviewed').addEventListener('change',()=>filterData());
$('good').onclick=()=>save('DOGRU');$('bad').onclick=()=>save('YANLIS');$('skip').onclick=()=>save('ATLA');
$('prev').onclick=()=>navigation(-1);$('next').onclick=()=>navigation(1);
$('speed').onchange=()=>document.querySelectorAll('audio').forEach(a=>a.playbackRate=Number($('speed').value));
window.addEventListener('keydown',e=>{
 if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;
 if(e.key===' '){e.preventDefault();const a=document.querySelector('audio');if(a){a.paused?a.play():a.pause()}}
 else if(e.key==='d'||e.key==='D')save('DOGRU');else if(e.key==='y'||e.key==='Y')save('YANLIS');
 else if(e.key==='s'||e.key==='S')save('ATLA');else if(e.key==='ArrowLeft')navigation(-1);else if(e.key==='ArrowRight')navigation(1);
});
Promise.all([fetch('/api/entries').then(x=>x.json()),fetch('/api/decisions').then(x=>x.json())]).then(([a,d])=>{
 entries=a.entries;decisions=d.decisions;filterData();
}).catch(err=>{const p=document.createElement('p');p.textContent='Başlatma hatası: '+err.message;document.querySelector('main').append(p)});
</script></body></html>'''


def handler_factory(batch,entries,store):
    bykey={e['key']:e for e in entries}
    safe_audio={e['key']:e['clips'] for e in entries}

    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,fmt,*args):
            if not self.path.startswith('/api/'):
                return
            print('%s %s' %(self.address_string(),fmt%args))
        def reply(self, data:bytes, code=200, typ='application/json; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type',typ)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; media-src 'self'; connect-src 'self'; object-src 'none'")
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(data)
        def send_json(self,doc,code=200):
            self.reply(json.dumps(doc,ensure_ascii=False).encode('utf-8'),code)
        def do_HEAD(self):self.do_GET()
        def do_GET(self):
            url=urllib.parse.urlsplit(self.path)
            if url.path=='/':return self.reply(HTML.encode('utf-8'),typ='text/html; charset=utf-8')
            if url.path=='/api/entries':return self.send_json({'entries':entries})
            if url.path=='/api/decisions':return self.send_json({'decisions':store.snapshot()})
            if url.path=='/audio':
                query=urllib.parse.parse_qs(url.query)
                key=query.get('key',[''])[0]
                try:part=int(query.get('part',['-1'])[0])
                except ValueError:part=-1
                if key not in bykey or not 0<=part<len(safe_audio[key]):return self.send_json({'error':'Unknown clip'},404)
                clip=safe_audio[key][part]
                wav=batch/clip['rel']
                if wav.is_symlink() or not wav.is_file() or not wav.resolve().is_relative_to(batch):
                    return self.send_json({'error':'Unsafe audio path'},404)
                if sha256(wav)!=clip['sha256']:
                    return self.send_json({'error':'Audio SHA mismatch'},409)
                size=wav.stat().st_size
                rng=self.headers.get('Range','')
                start=0;end=size-1;partial=False
                if rng:
                    match=re.fullmatch(r'bytes=(\d+)-(\d*)',rng)
                    if not match:return self.send_json({'error':'Invalid range'},416)
                    start=int(match.group(1))
                    end=int(match.group(2)) if match.group(2) else end
                    if start>=size or end<start:return self.send_json({'error':'Range outside audio'},416)
                    end=min(end,size-1);partial=True
                self.send_response(206 if partial else 200)
                self.send_header('Content-Type','audio/wav')
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Length',str(end-start+1))
                if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                if self.command=='HEAD':return
                try:
                    with wav.open('rb') as f:
                        f.seek(start)
                        left=end-start+1
                        while left:
                            x=f.read(min(65536,left))
                            if not x:break
                            self.wfile.write(x);left-=len(x)
                except (ConnectionResetError,BrokenPipeError):pass
                return
            return self.send_json({'error':'Not found'},404)
        def do_POST(self):
            if urllib.parse.urlsplit(self.path).path!='/api/decision':return self.send_json({'error':'Not found'},404)
            origin=self.headers.get('Origin','')
            host=self.headers.get('Host','')
            if origin and not (origin == 'http://'+host):
                return self.send_json({'error':'Unsupported origin'},403)
            if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
                return self.send_json({'error':'Use localhost'},403)
            try:
                n=int(self.headers.get('Content-Length','-1'))
                if not 0<n<=8192 or not self.headers.get('Content-Type','').startswith('application/json'):
                    raise ValueError('Invalid request size/type')
                obj=json.loads(self.rfile.read(n))
                if not isinstance(obj,dict):raise ValueError('Expected JSON object')
                entry=store.set_decision(obj['key'],obj['decision'],obj.get('note',''))
                return self.send_json({'ok':True,'saved':entry})
            except (ValueError,KeyError,TypeError,UnicodeError) as exc:
                return self.send_json({'error':str(exc)},400)
    return Handler


def main(argv=None):
    ap=argparse.ArgumentParser(description='Localhost GUI to listen to 393 B002 candidate recordings (no automatic approval).')
    ap.add_argument('--project',default='/run/media/ereng/files/projects/splinter-cell-turkish')
    ap.add_argument('--batch',help='Override B002 directory, for isolated tests only')
    ap.add_argument('--port',type=int,default=8766)
    ap.add_argument('--no-open',action='store_true',help='Print URL without opening browser')
    args=ap.parse_args(argv)
    if not 1<=args.port<=65535:ap.error('Port must be 1..65535')
    batch=(Path(args.batch) if args.batch else Path(args.project)/REL).expanduser().resolve()
    if not batch.is_dir():ap.error('Batch folder not found: '+str(batch))
    entries=make_entries(batch)
    store=ReviewStore(batch,entries)
    try:
        http=ThreadingHTTPServer(('127.0.0.1',args.port),handler_factory(batch,entries,store))
    except OSError as e:
        ap.error(f'Local port unavailable ({e}); try --port 8766')
    http.daemon_threads=True
    url=f'http://127.0.0.1:{args.port}/'
    print('\nDinleme ekranı:',url)
    print('Karar dosyaları:',store.root)
    print('Yalnız localhost; hiçbir oyun sesi/DLL veya kaynak kesim onayı değişmeyecek.')
    print('Çıkış: Ctrl+C\n',flush=True)
    if not args.no_open:threading.Timer(0.45,lambda:webbrowser.open(url)).start()
    try:http.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:print('\nDinleme ekranı kapatıldı.')
    finally:http.server_close()
    return 0

if __name__=='__main__':sys.exit(main())
