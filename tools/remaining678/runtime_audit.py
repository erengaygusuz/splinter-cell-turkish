#!/usr/bin/env python3
"""Read-only identity audit and byte-preserving backup. Never installs a DLL."""
import csv,hashlib,json,shutil,struct,subprocess
from pathlib import Path
from pipeline import ROOT,Q,sha,load,save,table,tsv
GAME=Path('/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell')
SYSTEM=GAME/'system'
BACKUP=ROOT/'backups/remaining678_before_v1_20261023'
def csvrows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def closed():
 ps=subprocess.check_output(['ps','-eo','pid,comm,args'],text=True)
 active=[l for l in ps.splitlines() if len(l.split(None,2))>=2 and l.split(None,2)[1].casefold() in ['splintercell.exe','splintercell']]
 assert not active, 'Game process is running; snapshot deferred: '+str(active)
def backup():
 closed()
 files=[p for p in SYSTEM.iterdir() if p.is_file() and (p.name.startswith('SNDDSound3DDLL') or p.name.startswith('snd-') and p.suffix=='.log')]
 files+=list((SYSTEM/'sc-tr-audio').glob('*.wav'))
 files += [p for p in (GAME/'Sounds').rglob('*') if p.is_file() and p.suffix.lower() in ['.ls0','.ls1','.snd']]
 records=[]
 for p in sorted(files):
  dst=BACKUP/'game'/p.relative_to(GAME);h=sha(p);dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():
   with dst.open('xb') as f, p.open('rb') as src:shutil.copyfileobj(src,f)
  assert sha(dst)==h
  records.append(dict(path=str(p),backup=str(dst.relative_to(ROOT)),sha256=h,bytes=p.stat().st_size))
 for p in sorted((ROOT/'manifests').glob('fisher-lambert-runtime-v*.csv')):
  dst=BACKUP/'manifests'/p.name;dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():
   with dst.open('xb') as f:f.write(p.read_bytes())
  assert sha(p)==sha(dst)
  records.append(dict(path=str(p),backup=str(dst.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size))
 table(Q/'runtime_backup.tsv',records)
 protected=[]
 for name in ['sam_fisher','irving_lambert']:
  for p in (ROOT/'dubbing/characters'/name).rglob('*'):
   if p.is_file():protected.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size))
 table(Q/'protected_408_archive.tsv',protected)
 live=SYSTEM/'SNDDSound3DDLL_VBR.dll';h=sha(live)
 matches=[str(p.relative_to(ROOT)) for p in (ROOT/'build').glob('*/SNDDSound3DDLL_VBR.dll') if sha(p)==h]
 save(Q/'installed_runtime.json',dict(live_sha256=h,matching_builds=matches,wav_count=len(list((SYSTEM/'sc-tr-audio').glob('*.wav'))),game_closed_at_backup=True,backup_files=len(records),backup_bytes=sum(r['bytes'] for r in records),protected_archive_files=len(protected)))
 print('Backed up',len(records),'runtime/bank files; protected',len(protected),'archive files; installed',matches,flush=True)
def audit():
 corpus=csvrows(ROOT/'manifests/corpus.csv');auth=csvrows(ROOT/'manifests/runtime-dub-authoritative.csv');old=csvrows(ROOT/'manifests/fisher-lambert-runtime-v19.csv')
 new=tsv(ROOT/'dubbing/figurants/gameplay/batches/B002_20261022/reference/06_678_HENUZ_KESILMEYEN_OYUN_REPLIGI.tsv')
 old_ids={r['id'] for r in old};new_ids={r['gameplay_id'] for r in new};assert len(old_ids)==408 and len(new_ids)==678 and not old_ids&new_ids
 targets=old_ids|new_ids;assert len(targets)==1086
 by_auth={}
 for r in auth:
  if r['id'].strip():
   uid=r['id'].strip()
   if uid in by_auth:assert by_auth[uid]['editor_id']==r['editor_id'],uid
   by_auth[uid]=r
 identities=[]
 for r in corpus:
  a=by_auth.get(r['id'],{});ed=a.get('editor_id','').strip();header=int(r['header_id'],0)
  bank=(int(ed,0) if ed else header)&0xffff0000
  identities.append(dict(id=r['id'],bank=bank,bits=bits(int(r['sample_count'])/int(r['sample_rate'])),editor_id=ed,old_header=header,bank_source='uax_verified_bank' if ed else 'legacy_header_bank'))
 by_id={r['id']:r for r in identities};assert targets<=set(by_id)
 old_by={r['id']:r for r in old};results=[];tolset={int(r['tolerance_ulps']) for r in old};assert len(tolset)==1;tol=tolset.pop()
 for uid in sorted(targets):
  r=by_id[uid];matches=[x['id'] for x in identities if (not r['bank'] or x['bank']==r['bank']) and abs(x['bits']-r['bits'])<=tol]
  if uid in old_by:
   o=old_by[uid];assert int(o['original_duration_bits'],16)==r['bits'] and int(o['required_runtime_bank'],16)==r['bank']
   assert sha(SYSTEM/'sc-tr-audio'/f'{uid}.wav')==o['turkish_wav_sha256'],uid+' installed audio changed'
  results.append(dict(id=uid,scope='EXISTING_408' if uid in old_ids else 'NEW_678',old_header_id=f'{r["old_header"]:08X}',required_runtime_bank=f'{r["bank"]:08X}',editor_id=r['editor_id'],bank_source=r['bank_source'],original_duration_bits=f'{r["bits"]:08X}',tolerance_ulps=tol,corpus_matches=','.join(matches),identity_status='UNIQUE' if matches==[uid] else 'AMBIGUOUS_HOLD',audio_status='INSTALLED_EXISTING' if uid in old_ids else 'QA_PENDING',runtime_path=f'sc-tr-audio\\{uid}.wav'))
 table(Q/'runtime_identity_1086.tsv',results)
 conflicts=[r for r in results if r['identity_status']!='UNIQUE'];table(Q/'runtime_identity_conflicts.tsv',conflicts,list(results[0]))
 save(Q/'runtime_identity_summary.json',dict(corpus_rows=len(corpus),target_ids=len(targets),existing_ids=len(old_ids),new_ids=len(new_ids),overlap=0,unique=len(results)-len(conflicts),ambiguous=len(conflicts),ambiguous_ids=[r['id'] for r in conflicts],tolerance_ulps=tol,installed_408_hashes_match=True,ready_for_new_dll=False))
 print('Runtime identity:',len(results)-len(conflicts),'unique;',len(conflicts),'ambiguous. No DLL modified.',flush=True)
if __name__=='__main__':backup();audit()
