"""Inventory immutable FMV inputs and resolve production order from supplied text."""
from pathlib import Path
import csv, hashlib, json, re, subprocess, unicodedata
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'dubbing/fmv-production'
QA = BASE / 'qa/R001_20261029'
BIKS = ['0_0_2_Training','1_1_0Tbilisi','1_1_0Tbilisi_Osprey','1_2_1DefenseMinistry','1_3_2CaspianOilRefinery','2_1_0CIA','2_1_0CIA_Osprey','2_2_1_Kalinatek','3_2_1_PowerPlant','3_2_1_PowerPlant_Osprey','4_1_1ChineseEmbassy','4_1_1ChineseEmbassy_Osprey','4_2_1_Abattoir','4_3_0ChineseEmbassy','5_1_1_PresidentialPalace','5_1_1_PresidentialPalace_Osprey','Sam&Shara']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def norm(s):
 s=s.lower().replace('ı','i')
 return ''.join(c for c in unicodedata.normalize('NFD',s) if c.isalnum())
def seconds(s):
 if ':' not in s:return float(s)
 h,m,x=s.replace(',','.').split(':'); return int(h)*3600+int(m)*60+float(x)
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def build():
 units=[]; videos=[]; errors=[]
 manifest=list(csv.DictReader((BASE/'SOURCE_MANIFEST.tsv').open(),delimiter='\t'))
 for m in manifest:
  p=BASE/'raw-elevenlabs'/m['video']/m['project_file']
  actual=sha(p)
  if actual!=m['sha256'] or p.stat().st_size!=int(m['bytes']):raise ValueError(f'Source changed: {p}')
  m.update(path=str(p.relative_to(ROOT)),verified_sha256=actual,metadata=probe(p))
 for n,stem in enumerate(BIKS,1):
  key=f'{n:02}'; ref=BASE/'reference'/key
  source=next(m for m in manifest if m['video'].startswith(key+'_') and m['project_file']=='source.mp3')
  csvfile=next(ref.glob('*HARITASI.csv')) if n!=1 else next(ref.glob('*.csv'))
  rr=rows(csvfile); grouped={}
  for r in rr:
   uid=r.get('unit_id') or r.get('elevenlabs_birimi') or r.get('elevenlabs_unit') or r.get('id') or 'TR-'+r['replik_no']
   a,b=r['time'].split(' --> ') if 'time' in r else (r.get('start',r.get('baslangic',r.get('videoya_giris_s'))),r.get('end',r.get('bitis',r.get('videoda_bitis_s'))))
   txt=next(r[k] for k in ['uretim_tam_metni','turkish_dubbing','turkish_text','turkish','tr','metin'] if k in r)
   if uid in grouped:
    u=grouped[uid];u['end']=max(u['end'],seconds(b));u['start']=min(u['start'],seconds(a))
    if n==10:u['text']+=' '+txt
    elif u['text']!=txt:raise ValueError((key,uid,'Conflicting texts'))
   else:
    grouped[uid]=dict(video=source['video'],id=uid,text=txt,start=seconds(a),end=seconds(b),speaker=next(r[k] for k in ['speaker_name','speaker','konusmaci','karakter'] if k in r),environment=next((r[k] for k in ['environment','audio_environment','channel','medium','iletisim_ortami'] if k in r),''),reference=str(csvfile.relative_to(ROOT)),source=source['path'])
   if n==1:grouped[uid].update(source_start=float(r['mp3_kesim_baslangic_s']),source_end=float(r['mp3_kesim_bitis_s']),production_order=int(r['tek_mp3_parca_no']),boundary_method='provided_training_map')
  if n!=1:
   txtfile=next(ref.glob('*ELEVENLABS_TR.txt'));txt=txtfile.read_text(encoding='utf-8-sig')
   blocks=re.findall(r'--- ELEVENLABS KOPYALA (?:BAŞLANGIÇ|BASLANGIC) ---\s*(.*?)\s*--- ELEVENLABS KOPYALA (?:BİTİŞ|BITIS) ---',txt,re.S)
   explicit_ids=[]
   if n==10:
    for ids in re.findall(r'ÜRETİM BİRİMLERİ: ([^\n]+)',txt):explicit_ids.extend(re.findall(r'[A-Z]+-\d+',ids))
   production=[]
   for block in blocks:
    for para in re.split(r'\n\s*\n',block.strip()):
     t=re.sub(r'\[[^\]]*\]','',para).strip()
     if t:production.append(t)
   matched=set()
   for order,t in enumerate(production,1):
    candidates=[grouped[explicit_ids[order-1]]] if explicit_ids else [u for u in grouped.values() if norm(u['text'])==norm(t) and u['id'] not in matched]
    if len(candidates)!=1:
     errors.append(dict(video=key,order=order,text=t,candidates=[u['id'] for u in candidates]));continue
    u=candidates[0];matched.add(u['id'])
    if norm(u['text'])!=norm(t):u['subtitle_reference_text']=u['text'];u['text_resolution']='Explicit production ID; ElevenLabs text takes precedence over subtitle wording'
    u.update(text=t,production_order=order,production_reference=str(txtfile.relative_to(ROOT)))
   if len(matched)!=len(grouped):errors.append(dict(video=key,unmapped=list(set(grouped)-matched),production_count=len(production)))
  if n==7:
   grouped['GR-03']['source']=next(m['path'] for m in manifest if m['project_file']=='source_patch_GR-03.mp3')
   xml=BASE/'07_CIA_Osprey_manual_split_reference.kdenlive'
   tree=ET.parse(xml);entries=tree.findall(".//playlist[@id='playlist0']/entry")
   ordered=sorted(grouped.values(),key=lambda u:u['production_order'])
   assert len(entries)==len(ordered)==26
   for u,e in zip(ordered,entries):
    assert (e.attrib['producer']=='chain3')==(u['id']=='GR-03')
    u.update(source_start=seconds(e.attrib['in']),source_end=seconds(e.attrib['out'])+0.04,boundary_method='user_manual_kdenlive_25fps_inclusive_out',boundary_reference=str(xml.relative_to(ROOT)))
  units.extend(grouped.values())
  bik=ROOT/'staging/ps2-fmvs/Videos'/f'{stem}.bik'
  bg=list((ROOT/'work/fmv-dialogue-clean-v2-strong'/f'{key}_{stem}').glob('*48k.wav'))
  if not bg:bg=list((ROOT/'work/fmv-dialogue-clean'/f'{key}_{stem}').glob('*48k.wav'))
  if n==1:bg=[Path('/home/ereng/Downloads/SC_FMV_01_Training_diyalog_bastirilmis_v2_Alarm_48k.wav')]
  if len(bg)!=1:raise ValueError((key,'Background missing/ambiguous',bg))
  videos.append(dict(video=source['video'],bik=str(bik.relative_to(ROOT)),bik_sha256=sha(bik),metadata=probe(bik),background=str(bg[0]),background_sha256=sha(bg[0]),background_metadata=probe(bg[0]),unit_count=len(grouped)))
 write(QA/'inventory.json',dict(sources=manifest,videos=videos));write(QA/'catalog.json',units);write(QA/'catalog_errors.json',errors)
 print(json.dumps(dict(sources=len(manifest),videos=len(videos),units=len(units),errors=errors),ensure_ascii=False,indent=2))
if __name__=='__main__':build()
