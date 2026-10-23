#!/usr/bin/env python3
"""Index multitrack layers and audit coverage of every English/common data file."""
import collections, concurrent.futures, hashlib, json, struct, subprocess
from inventory import GAME,OUT,csv_read,csv_write,json_write,u32,language,mission


def run():
    nodes=json.loads((OUT/'bank-event-nodes.json').read_text());layers=[]
    unique={}
    for n in nodes:
        if n['kind']!='resource' or n['type']!=13:continue
        h=bytes.fromhex(n['data_hex']);name=h[52:92].split(b'\0')[0].decode('latin1')
        src=(GAME/n['bank']).parent/name;offset=u32(h,92);size=u32(h,100)
        assert src.is_file() and offset+size<=src.stat().st_size
        with src.open('rb') as f:f.seek(offset);payload=f.read(size)
        encoded=hashlib.sha256(payload).hexdigest()
        row=dict(bank=n['bank'],map=n['map'],mission=mission(n['bank']),resource_header_id=n['editor_id'],resource_index=n['index'],stream_index=n['stream_index'],
                 source_path=str(src.relative_to(GAME)),stream_offset=offset,stream_size=size,encoded_sha256=encoded,
                 classification='NON_SPEECH_MULTITRACK_AMBIENCE',notes='Layered ambience events; indexed separately from speech leaf resources')
        layers.append(row);unique.setdefault(encoded,row)
    def probe(item):
        key,r=item
        result=subprocess.run([str(OUT/'vgmstream-cli'),'-m','-I','-s',str(r['stream_index']),str(GAME/r['bank'])],capture_output=True,text=True,check=True)
        meta=json.loads(result.stdout);json_write(OUT/'layer-metadata'/f'{key}.json',meta)
        return key,meta
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:metadata=dict(pool.map(probe,unique.items()))
    for r in layers:
        m=metadata[r['encoded_sha256']]
        r.update(sample_rate=m['sampleRate'],sample_count=m['numberOfSamples'],channels=m['channels'],codec=m['encoding'],
                 duration_sec=round(m['numberOfSamples']/m['sampleRate'],6),layer_layout=m['layout'])
    csv_write(OUT/'multitrack-resources.csv',layers)
    refs=csv_read(OUT/'audio-resource-references.csv');ranges=collections.defaultdict(list)
    for r in refs+layers:
        if r.get('status','OK')=='OK':ranges[r['source_path']].append((int(r['stream_offset']),int(r['stream_offset'])+int(r['stream_size'])))
    coverage=[];gaps=[];orphans=[]
    for p in sorted((GAME/'Sounds').rglob('*')):
        if not p.is_file() or p.suffix.lower() not in {'.ls0','.ss0'} or language(p).lower() not in {'common','english'}:continue
        rel=str(p.relative_to(GAME));intervals=sorted(set(ranges[rel]));merged=[]
        for a,b in intervals:
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        end=0;pgaps=[]
        for a,b in merged:
            if a>end:pgaps.append((end,a))
            end=b
        if end<p.stat().st_size:pgaps.append((end,p.stat().st_size))
        blob=p.read_bytes()
        for a,b in pgaps:
            block=blob[a:b]
            if len(block)>16:
                gaps.append(dict(source_path=rel,start=a,end=b,size=b-a,nonzero_bytes=sum(v!=0 for v in block)))
                # Strong ADPCM header invariants, not a loose magic-only carve.
                pos=block.find(b'\x08\0\0\0')
                while pos>=0:
                    x=a+pos
                    if x+48<=b:
                        h=struct.unpack_from('<12I',blob,x)
                        if h[1]>0 and h[3]<=1536 and h[4]<=1536 and h[5]==2 and h[6] in {16000,22050,32000,36000,44100,48000} and h[9] in {4,6} and h[11] in {1,2}:
                            orphans.append(dict(source_path=rel,stream_offset=x,gap_end=b,sample_count=h[1],sample_rate=h[6],channels=h[11],classification='ORPHAN_ADPCM_HEADER_REVIEW'))
                    pos=block.find(b'\x08\0\0\0',pos+4)
        coverage.append(dict(source_path=rel,size=len(blob),unique_referenced_ranges=len(intervals),covered_bytes=sum(b-a for a,b in merged),
                             gap_bytes=sum(b-a for a,b in pgaps),large_gaps=sum(b-a>16 for a,b in pgaps)))
    # Common/ contains PCM versions of the compressed common music banks.
    # Validate complete coverage and waveform correlation; do not claim a byte
    # duplicate between a lossy codec and its PCM source.
    import wave
    import numpy as np
    decoded={r['encoded_key']:r for r in csv_read(OUT/'decoded-unique-resources.csv')}
    comparisons=[]
    for name in ['Music_Common.SS0','Music_Georgie.SS0']:
        pcm_path=GAME/'Sounds/Common'/name
        raw=np.fromfile(pcm_path,dtype='<i2');pos=0;segments=[]
        music={int(r['stream_offset']):r for r in refs if r['source_path']=='Sounds/'+name}
        for off,r in sorted(music.items()):
            from inventory import PROJECT
            with wave.open(str(PROJECT/decoded[r['encoded_key']]['wav_path']),'rb') as w:
                wave_pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
            a=raw[pos:pos+len(wave_pcm)][::32].astype(float);b=wave_pcm[::32].astype(float)
            corr=float(np.corrcoef(a,b)[0,1]);assert corr>0.99,(name,off,corr)
            segments.append(dict(encoded_offset=off,pcm_byte_offset=pos*2,pcm_bytes=len(wave_pcm)*2,correlation=corr,encoded_key=r['encoded_key']))
            pos+=len(wave_pcm)
        assert pos==len(raw)
        comparisons.append(dict(source_path=str(pcm_path.relative_to(GAME)),total_bytes=len(raw)*2,accounted_bytes=pos*2,segments=segments))
        for r in coverage:
            if r['source_path']==str(pcm_path.relative_to(GAME)):
                r['coverage_note']='Entire raw PCM file matches compressed music segments; correlation >0.99; not a byte duplicate'
                r['pcm_fingerprint_covered_bytes']=pos*2
    json_write(OUT/'common-pcm-music-comparison.json',comparisons)
    csv_write(OUT/'external-container-coverage.csv',coverage)
    csv_write(OUT/'external-container-gaps.csv',gaps,['source_path','start','end','size','nonzero_bytes'])
    csv_write(OUT/'orphan-stream-headers.csv',orphans,['source_path','stream_offset','gap_end','sample_count','sample_rate','channels','classification'])
    print('Layers',len(layers),'unique encoded',len(unique),'external files',len(coverage),'large gaps',len(gaps),'orphan ADPCM headers',len(orphans),flush=True)
if __name__=='__main__':run()
