#!/usr/bin/env python3
"""Resumable CPU Whisper and conservative, source-preserving candidate segmentation."""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, subprocess, time, wave
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
Q=ROOT/'dubbing/qa/remaining678_v1_20261023'
B1=ROOT/'dubbing/figurants/gameplay/batches/B001_20261022'
B2=ROOT/'dubbing/figurants/gameplay/batches/B002_20261022'
_spec=importlib.util.spec_from_file_location('existing_alignment',ROOT/'dubbing/characters/sam_fisher/gameplay/voice_versions/VD001/tools/vd001_audio_qa.py')
common=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(common)
RATE=44100

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def tsv(p):return common.tsv(p)
def save(p,obj):common.save_json(p,obj)
def table(p,rows,fields=None):common.write_tsv(p,rows,fields)
def load(p):return json.loads(Path(p).read_text())
def immutable_json(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert load(p)==obj, f'Existing evidence differs: {p}'
 else:
  with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def probe(p):
 d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]));s=next(s for s in d['streams'] if s['codec_type']=='audio')
 return dict(duration=float(d['format']['duration']),rate=int(s['sample_rate']),channels=s['channels'],codec=s['codec_name'])
def inventory():
 sources=[];rows=[];checks=[]
 chars=[('anna_grimsdottir',29),('junior_wilkes',23),('kombayn_nikoladze',37),('kong_feirong',23),('vyacheslav_grinko',13),('frances_coen',10),('varlam_cristavi',9)]
 for character,count in chars:
  base=next((ROOT/'dubbing/characters'/character/'gameplay/voice_versions').iterdir())
  manifest=next(base.glob('batches/*/source_manifest.json'));raw=load(manifest)
  primary=next(p for p in manifest.parent.glob('*.mp3') if 'preview' not in p.name)
  digest=sha(primary);assert digest in json.dumps(raw),f'Unknown source hash: {primary}'
  checks.append(dict(path=rel(primary),sha256=digest,reference=rel(manifest)))
  source=next(manifest.parent.glob('*minus16lufs_v02_master.wav')) if character=='varlam_cristavi' else primary
  if source!=primary:checks.append(dict(path=rel(source),sha256=sha(source),reference='User handoff selects v02 master; no published master hash in earlier manifest'))
  catalog=next(p for p in base.glob('production_source/*id_order.tsv') if not p.name.startswith('original_'))
  lines=tsv(catalog);assert len(lines)==count
  key='A_'+character
  sources.append(dict(key=key,stage='A',path=rel(source),sha256=sha(source),**probe(source)))
  for i,r in enumerate(lines,1):
   assert int(r.get('sequence',r.get('production_sequence',r.get('sira'))))==i
   rows.append(dict(candidate_key=r['gameplay_id'],id=r['gameplay_id'],stage='A',group=key,speaker=character,take='NORMAL',order=i,expected_text=common.spoken(r.get('elevenlabs_text',r.get('expected_prompt',r.get('expected_text')))),source_hint=key,output_dir=rel(base/'review_pending'/manifest.parent.name),speaker_hold=r['gameplay_id'] in ['u000486','u000489'],excluded=False))
 manifest=load(B1/'source_manifest.json')
 for s in manifest['physical_mp3s']:
  p=B1/'audio_original'/s['filename'];assert sha(p)==s['sha256'] and p.stat().st_size==s['bytes']
  key=f'B_file{s["index"]:02d}';sources.append(dict(key=key,stage='B',path=rel(p),sha256=s['sha256'],**probe(p)));checks.append(dict(path=rel(p),sha256=s['sha256'],reference=rel(B1/'source_manifest.json')))
 lines=tsv(B1/'00_177_ID_QA_PENDING.tsv')
 for section in tsv(B1/'00_23_SOURCE_SECTIONS_1_REPLACED.tsv'):
  group=[r for r in lines if r['role_number']==section['role_number']]
  assert len(group)==int(section['expected_replicas'])
  reject=section['use_for_production']!='YES'
  for r in group:
   rows.append(dict(candidate_key=r['gameplay_id']+('_rejected_male' if reject else ''),id=r['gameplay_id'],stage='B',group='B_all',speaker='B001_role'+r['role_number'].zfill(2),take='REJECTED_MALE' if reject else 'NORMAL',order=len(rows),expected_text=common.spoken(r['expected_text']),source_hint=f'B_file{int(section["file_number"]):02d}',output_dir=rel(B1/'review_pending'/('role'+r['role_number'].zfill(2))),speaker_hold=r['role_number']=='12',excluded=reject))
 for s in tsv(B2/'reference/03_48_MP3_TARIH_SAAT_SHA256_ENVANTERI.tsv'):
  p=B2/'audio_original'/s['uploaded_filename'];assert sha(p)==s['sha256'] and p.stat().st_size==int(s['bytes'])
  sources.append(dict(key=f'C_file{int(s["chronological_file_index"]):02d}',stage='C',path=rel(p),sha256=s['sha256'],**probe(p)));checks.append(dict(path=rel(p),sha256=s['sha256'],reference=rel(B2/'reference/03_48_MP3_TARIH_SAAT_SHA256_ENVANTERI.tsv')))
 for r in tsv(B2/'reference/05_KESIM_ZAMANLARI_393_KAYIT_ADAYI_DOLDUR.tsv'):
  rows.append(dict(candidate_key=r['gameplay_id']+'_'+r['take'].lower(),id=r['gameplay_id'],stage='C',group='C_all',speaker=r['voice_id'],take=r['take'],order=len(rows),expected_text=common.spoken(r['expected_text']),source_hint='',output_dir=rel(B2/'review_pending'/r['voice_id']),speaker_hold=False,excluded=False))
 expected=tsv(B2/'reference/06_678_HENUZ_KESILMEYEN_OYUN_REPLIGI.tsv');authority={r['gameplay_id']:r for r in expected}
 assert len(authority)==len(expected)==678
 assert len(rows)==len({r['candidate_key'] for r in rows})
 assert {r['id'] for r in rows}==set(authority)
 for r in rows:assert common.norm(r['expected_text'])==common.norm(authority[r['id']]['expected_text']),r['id']
 assert len([r for r in rows if r['stage']=='A'])==144
 assert len([r for r in rows if r['stage']=='B' and not r['excluded']])==177
 assert len([r for r in rows if r['stage']=='C'])==393
 assert len({r['id'] for r in rows if r['stage']=='C'})==357
 immutable_json(Q/'sources.json',sources);immutable_json(Q/'expected_candidates.json',rows)
 table(Q/'source_integrity.tsv',checks)
 print('Inventory verified:',len(sources),'working sources;',Counter(r['stage'] for r in rows),flush=True)

def get_model():
 from faster_whisper import WhisperModel
 return WhisperModel('medium',device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
def transcribe_one(model,p,digest,out):
 if out.exists():
  d=load(out);assert d['sha256']==digest;return d
 start=time.monotonic();segments,info=model.transcribe(str(p),language='tr',beam_size=5,word_timestamps=True,condition_on_previous_text=False,vad_filter=False)
 d=dict(path=str(p),sha256=digest,model='medium',device='cpu',compute_type='int8',cpu_threads=4,language='tr',word_timestamps=True,condition_on_previous_text=False,vad_filter=False,initial_prompt=None,segments=[],words=[])
 for s in segments:
  d['segments'].append(dict(start=s.start,end=s.end,text=s.text,no_speech_prob=s.no_speech_prob))
  d['words'].extend(dict(text=w.word,start=w.start,end=w.end,probability=w.probability) for w in s.words or [])
  save(out.with_suffix('.partial.json'),d)
 d.update(text=' '.join(s['text'] for s in d['segments']),elapsed_seconds=round(time.monotonic()-start,2))
 immutable_json(out,d)
 print('ASR complete',p.name,len(d['words']),'words',d['elapsed_seconds'],'s',flush=True)
 return d

def source_asr(stage):
 model=None
 for s in load(Q/'sources.json'):
  if stage!='all' and s['stage']!=stage:continue
  p=ROOT/s['path'];assert sha(p)==s['sha256']
  out=Q/'source_asr'/(s['key']+'.json')
  if out.exists():assert load(out)['sha256']==s['sha256'];continue
  if model is None:model=get_model()
  print('ASR start',s['key'],s['duration'],'seconds',flush=True)
  transcribe_one(model,p,s['sha256'],out)

def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['inventory','source_asr']);a.add_argument('--stage',default='A',choices=['A','B','C','all']);args=a.parse_args()
 if args.mode=='inventory':inventory()
 else:source_asr(args.stage)
if __name__=='__main__':main()
