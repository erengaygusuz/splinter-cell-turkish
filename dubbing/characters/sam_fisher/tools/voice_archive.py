#!/usr/bin/env python3
"""Sam Fisher voice archive: report status, validate sources, optionally approve a reviewed take."""
import argparse, csv, hashlib, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load(kind):
    with (ROOT / kind / 'catalog.tsv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))

def takes(kind):
    return sorted((ROOT / kind / 'takes').glob('*.wav'))

def show_status():
    for kind, label in [('gameplay','OYUN ICI'),('fmv','FMV')]:
        lines=load(kind)
        known={r['id'] for r in lines}
        candidates=takes(kind)
        map_={}
        bad=[]
        for p in candidates:
            m = re.fullmatch(r'(u\d{6}|fmv\d{2}-\d{4})_v(\d{2})\.wav',p.name)
            if m is None or m.group(1) not in known:
                bad.append(p.name)
            else:
                map_.setdefault(m.group(1),[]).append('v'+m.group(2))
        approved=list((ROOT/kind/'approved').glob('*.wav'))
        print(f'{label}: katalog={len(lines)}, seslendirilmis={len(map_)}, eksik={len(lines)-len(map_)}, take dosyasi={len(candidates)}, onayli WAV={len(approved)}')
        if bad:
            print('  KATALOG DISI / AD HATASI: '+', '.join(bad))
        pending=[r['id'] for r in lines if r['id'] in map_ and not any(q.name.startswith(r['id']+'_') for q in approved)]
        if pending:
            print('  Dinleme bekleyen kayitlar: '+', '.join(pending))
        print()
    return True

def approve(kind, id_, version, note):
    known={r['id'] for r in load(kind)}
    if id_ not in known:
        sys.exit('HATA: katalogda bulunmayan replik ID: '+id_)
    if not re.fullmatch(r'v\d{2}',version):
        sys.exit('HATA: take formati v01 / v02 olmali')
    src=ROOT/kind/'takes'/f'{id_}_{version}.wav'
    if not src.is_file():
        sys.exit('HATA: kaynak bulunamadi: '+str(src))
    dst=ROOT/kind/'approved'/src.name
    sha=hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists():
        if hashlib.sha256(dst.read_bytes()).hexdigest()!=sha:
            sys.exit('HATA: onayli kayit farkli; ustune yazilmiyor: '+str(dst))
        print('Zaten onayli: '+str(dst)); return
    shutil.copy2(src,dst)
    with (ROOT/kind/'approved_log.tsv').open('a',encoding='utf-8',newline='') as f:
        csv.writer(f,delimiter='\t').writerow([id_,version,sha,datetime.now(timezone.utc).isoformat(),note])
    print('Onaylandi (ham WAV kopyalandi, oyun formatina DONUSTURULMEDI):',dst)

parser=argparse.ArgumentParser(description='Sam Fisher ses arşivi kontrolü')
sub=parser.add_subparsers(dest='cmd',required=True)
sub.add_parser('status')
ap=sub.add_parser('approve',help='yalnizca dinleyip onayladiktan sonra kullan')
ap.add_argument('kind',choices=['gameplay','fmv'])
ap.add_argument('id')
ap.add_argument('version',help='v01 gibi')
ap.add_argument('--note',default='Kullanici dinleme onayi')
args=parser.parse_args()
if args.cmd=='status': show_status()
else: approve(args.kind,args.id,args.version,args.note)
