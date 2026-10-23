#!/usr/bin/env python3
"""Read-only installed audio inventory and version-7 DARE resource index.

Offsets/layout are taken from vgmstream src/meta/ubi_sb.c. Never infer a
physical audio match from text, duration, or an event name alone.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, json, re, struct, wave

PROJECT = Path(__file__).resolve().parents[2]
GAME = Path('/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell')
OUT = PROJECT / 'build/full-game-voice-audit'
LANGS = {'english', 'french', 'german', 'italien', 'spanish'}


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def csv_read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def csv_write(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(dict.fromkeys(k for r in rows for k in r))
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def language(path):
    return next((s for s in path.parts if s.lower() in LANGS), 'common')


def mission(path):
    p = str(path).lower()
    if 'kolacell' in p: return 'BONUS_KOLA_CELL'
    if 'vselkainfiltration' in p: return 'BONUS_VSELKA_INFILTRATION'
    if 'vselka' in p: return 'BONUS_VSELKA'
    return 'MAIN_GAME'


def inventory(game, out):
    rows=[]
    for p in sorted((game/'Sounds').rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(game)
        rows.append(dict(relative_path=str(rel), size=p.stat().st_size, sha256=sha(p),
                         type=p.suffix.lower(), mission=mission(rel), language=language(rel),
                         role='event_reference' if p.suffix.lower() in {'.uax','.sp0','.int','.lip','.bin'} else 'audio_container',
                         map_hint=p.parent.name))
    csv_write(out/'full-game-audio-inventory.csv', rows)
    # Separate immutable baseline; a rerun must not silently replace it.
    protected=[game/'system/SNDDSound3DDLL_VBR.dll',game/'system/SNDDSound3DDLL_VBR_orig.dll']
    protected+=sorted((game/'system/sc-tr-audio').rglob('*.wav'))
    baseline={str(p.relative_to(game)):sha(p) for p in protected}
    baseline.update({r['relative_path']:r['sha256'] for r in rows})
    path=out/'protected-installation-baseline.json'
    if path.exists():
        old=json.loads(path.read_text())
        if baseline != old: raise RuntimeError('Installed files changed since audit baseline; investigate before continuing')
    else: json_write(path,baseline)
    installed={p.stem for p in protected if p.suffix.lower()=='.wav'}
    assert len(installed)==1086, f'Expected V27 1086 WAV IDs, got {len(installed)}'
    preflight=json.loads((PROJECT/'build/snd-waveout-all1086-trial-v27/preflight.json').read_text())
    assert baseline['system/SNDDSound3DDLL_VBR.dll']==preflight['dll_sha256']
    json_write(out/'installation-verification.json',dict(wav_ids=len(installed),dll_sha256=preflight['dll_sha256'],
                protected_files=len(baseline),audio_files=len(rows),extensions=dict(collections.Counter(r['type'] for r in rows))))
    return rows


def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def cstr(b,o,n): return b[o:o+n].split(b'\0')[0].decode('latin1')


def compact(b, off):
    c=b[off];off+=1;negative=c&0x80;v=c&0x3f;shift=6
    more=c&0x40
    while more:
        c=b[off];off+=1;v|=(c&0x7f)<<shift;shift+=7;more=c&0x80
        if shift>34: raise ValueError('invalid compact index')
    return (-v if negative else v),off


def parse_uax(path):
    b=path.read_bytes()
    assert u32(b,0)==0x9e2a83c1
    nc,no,ec,eo,ic,io=struct.unpack_from('<6I',b,12)
    names=[];p=no
    for _ in range(nc):
        n,p=compact(b,p);assert n>0
        names.append(b[p:p+n-1].decode('latin1'));p+=n+4
    p=eo;rows=[]
    for i in range(ec):
        cls,p=compact(b,p);sup,p=compact(b,p);package=struct.unpack_from('<i',b,p)[0];p+=4
        name,p=compact(b,p);flags=u32(b,p);p+=4;size,p=compact(b,p)
        off=0
        if size: off,p=compact(b,p)
        payload=b[off:off+size]
        # SC sound serialization: None property terminator, editor id, four
        # reserved bytes, compact external BIN string (normally empty).
        none,pos=compact(payload,0)
        assert names[none]=='None', (path,i,names[none])
        eid=u32(payload,pos);pos+=8
        ext=''
        if pos<len(payload):
            n,pos=compact(payload,pos)
            if n>0: ext=payload[pos:pos+n-1].decode('latin1')
        rows.append(dict(package=path.stem,event_name=names[name],editor_id=f'{eid:08X}',
                         external_bin_path=ext,serial_offset=off,serial_size=size,source_path=str(path.relative_to(GAME))))
    return rows


def parse_bank(path, game):
    b=path.read_bytes()
    assert u32(b,0)==7,(path,'unsupported bank version')
    start,count=u32(b,4),u32(b,8)
    assert start+count*48<=len(b)
    rows=[];nodes=[];subsong=0
    for mi in range(count):
        d=start+mi*48;m=u32(b,d+8);mapname=cstr(b,d+16,32)
        s1=m+u32(b,m+4);n1=u32(b,m+8)
        s2=m+u32(b,m+12);n2=u32(b,m+16)
        s3=m+u32(b,m+20);n3=u32(b,m+24);sx=m+u32(b,m+28);nx=u32(b,m+32)
        assert s2+n2*128<=len(b)
        internal=collections.defaultdict(list)
        for j in range(n3):
            t=s3+j*20;ta=s3+u32(b,t+4);na=u32(b,t+8);tb=s3+u32(b,t+12);nb=u32(b,t+16)
            blocks={u32(b,tb+k*16):u32(b,tb+k*16+12) for k in range(nb)}
            for k in range(na):
                ri=u32(b,ta+k*8)&0x3fffffff;ro=u32(b,ta+k*8+4)
                internal[ri].append((ro,blocks))
        for j in range(n1):
            x=s1+j*88
            nodes.append(dict(bank=str(path.relative_to(game)),map=mapname,map_index=mi,kind='event',index=j,
                              offset=x,editor_id=f'{u32(b,x):08X}',type=u32(b,x+4),data_hex=b[x:x+88].hex()))
        for ri in range(n2):
            x=s2+ri*128;typ=u32(b,x+4);eid=u32(b,x)
            if typ in {1,5,6,12,13}: subsong+=1
            node=dict(bank=str(path.relative_to(game)),map=mapname,map_index=mi,kind='resource',index=ri,
                      offset=x,editor_id=f'{eid:08X}',type=typ,stream_index=subsong if typ in {1,5,6,12,13} else '',data_hex=b[x:x+128].hex(),
                      extra_offset=sx+u32(b,x+16),extra_section_start=sx,extra_section_size=nx)
            nodes.append(node)
            if typ!=1: continue
            streamed=bool(u32(b,x+40)&1);codec=u32(b,x+76);internalflag=u32(b,x+8)
            size=u32(b,x+12);offset=u32(b,x+20);samples=u32(b,x+48);rate=u32(b,x+68);ch=u16(b,x+74)
            loop=u32(b,x+44)&1
            if loop:samples+=u32(b,x+56)
            name=cstr(b,x+80,40);external=streamed or not internalflag;status='OK';src=path
            if external:
                matches=[p for p in path.parent.iterdir() if p.name.lower()==name.lower()]
                if len(matches)==1: src=matches[0]
                else:status='EXTERNAL_SOURCE_MISSING';src=path.parent/name
            else:
                sb=0 if codec==1 else 1
                offsets={ro+blocks[sb] for ro,blocks in internal[ri] if sb in blocks}
                if len(offsets)!=1:status='INTERNAL_OFFSET_UNRESOLVED'
                else:offset=offsets.pop()
            if status=='OK' and offset+size>src.stat().st_size:status='OUT_OF_BOUNDS'
            rows.append(dict(bank=str(path.relative_to(game)),map=mapname,map_index=mi,mission=mission(path.relative_to(game)),
                        language=language(path.relative_to(game)),stream_index=subsong,resource_index=ri,resource_header_offset=x,
                        editor_id=f'{eid:08X}',resource_name=name,source_path=str(src.relative_to(game)),
                        stream_offset=offset,stream_size=size,sample_count=samples,sample_rate=rate,channels=ch,
                        duration_sec=round(samples/rate,6) if rate else '',codec={1:'PCM16LE',2:'UBI_ADPCM',4:'UBI_IMA'}.get(codec,str(codec)),
                        codec_id=codec,external=int(external),loop=loop,status=status))
    return rows,nodes,subsong


def run(game=GAME,out=OUT,index_only=False):
    files=csv_read(out/'full-game-audio-inventory.csv') if index_only else inventory(game,out)
    events=[]
    for r in files:
        if r['type']=='.uax':events+=parse_uax(game/r['relative_path'])
    csv_write(out/'uax-events.csv',events)
    rows=[];nodes=[];banks=[]
    for r in files:
        if r['type'] not in {'.sm0','.lm0'}:continue
        if r['language'].lower() not in {'english','common'}:continue
        a,n,total=parse_bank(game/r['relative_path'],game);rows+=a;nodes+=n
        banks.append(dict(bank=r['relative_path'],physical_resource_references=len(a),vgmstream_subsongs=total,
                          mission=r['mission'],language=r['language']))
    # Bonus maps explicitly reuse common music descriptors. Resolve only when
    # the exact resource ID, offset, size and format also occur in a root bank.
    keys=['editor_id','resource_name','stream_offset','stream_size','codec_id','sample_count','sample_rate','channels']
    shared={tuple(r[k] for k in keys):r for r in rows if r['bank']=='Sounds/MAPS.SM0' and r['status']=='OK'}
    for r in rows:
        if r['status']=='EXTERNAL_SOURCE_MISSING':
            other=shared.get(tuple(r[k] for k in keys))
            if other:
                r['source_path']=other['source_path'];r['status']='OK'
                r['source_resolution']='EXACT_SHARED_DESCRIPTOR_IN_ROOT_BANK'
    csv_write(out/'audio-resource-references.csv',rows)
    csv_write(out/'bank-index.csv',banks)
    json_write(out/'bank-event-nodes.json',nodes)
    print(json.dumps(dict(files=len(files),uax_events=len(events),banks=banks,resources=len(rows),statuses=dict(collections.Counter(r['status'] for r in rows))),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index-only',action='store_true');a=p.parse_args();run(index_only=a.index_only)
