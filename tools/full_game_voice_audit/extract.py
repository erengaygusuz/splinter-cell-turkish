#!/usr/bin/env python3
"""Extract exact leaf resources through isolated, one-resource decoder wrappers."""
import collections, concurrent.futures, hashlib, json, struct, subprocess, wave
from inventory import PROJECT,GAME,OUT,csv_read,csv_write,json_write,sha


def pcm_identity(path):
    with wave.open(str(path),'rb') as w:
        fmt=(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())
        raw=w.readframes(w.getnframes())
    assert len(raw)==fmt[1]*fmt[2]*fmt[3]
    return fmt,hashlib.sha256(raw).hexdigest()


def wrapper(header,payload):
    """Original payload/header retained; only routing, loop and name rewritten.

    Decoding an isolated leaf avoids replaying random/sequence containers and
    double counting their contents. Original identities live in the manifest.
    """
    h=bytearray(header)
    struct.pack_into('<I',h,8,1)  # internal
    struct.pack_into('<I',h,16,0) # no extra data
    struct.pack_into('<I',h,20,0)
    struct.pack_into('<I',h,40,0) # not streamed
    if struct.unpack_from('<I',h,44)[0]&1:
        n=struct.unpack_from('<I',h,48)[0]+struct.unpack_from('<I',h,56)[0]
        struct.pack_into('<I',h,48,n)
    struct.pack_into('<I',h,44,0) # play exactly once
    codec=struct.unpack_from('<I',h,76)[0];size=len(payload)
    out=bytearray(268)
    struct.pack_into('<3I',out,0,7,12,1)
    struct.pack_into('<4I',out,12,0,0,60,208);out[28:33]=b'audit'
    struct.pack_into('<9I',out,60,0,36,0,36,1,164,1,164,0)
    out[96:224]=h
    struct.pack_into('<5I',out,224,0xffffffff,20,1,28,1)
    struct.pack_into('<2I',out,244,0,0)
    struct.pack_into('<4I',out,252,0 if codec==1 else 1,size,size,268)
    out.extend(payload)
    return out


def extract_one(item):
    key,rows=item;r=rows[0]
    uid='v_'+key[:16];wav=OUT/'original-wav'/f'{uid}_{r["editor_id"]}_{r["stream_offset"]}.wav'
    wrap=OUT/'decoder-input'/f'{uid}.sm0';report=OUT/'decoder-metadata'/f'{uid}.json'
    with (GAME/r['source_path']).open('rb') as f:
        f.seek(int(r['stream_offset']));payload=f.read(int(r['stream_size']))
    with (GAME/r['bank']).open('rb') as f:
        f.seek(int(r['resource_header_offset']));header=f.read(128)
    assert hashlib.sha256(payload).hexdigest()==r['encoded_sha256']
    wrap.write_bytes(wrapper(header,payload))
    if not wav.exists():
        run=subprocess.run([str(OUT/'vgmstream-cli'),'-i','-o',str(wav),str(wrap)],capture_output=True,text=True)
        if run.returncode:
            return dict(new_id=uid,status='DECODE_FAILED',error=run.stdout+run.stderr,encoded_key=key)
    fmt,pcmsha=pcm_identity(wav)
    expected=(int(r['sample_rate']),int(r['channels']),2,int(r['sample_count']))
    if fmt!=expected: raise RuntimeError((uid,fmt,expected))
    meta=subprocess.run([str(OUT/'vgmstream-cli'),'-m','-I',str(wrap)],capture_output=True,text=True,check=True)
    json_write(report,json.loads(meta.stdout))
    # Encoded wrappers are reproducible and not retained for thousands of files.
    wrap.unlink()
    return dict(new_id=uid,status='OK',encoded_key=key,pcm_sha256=pcmsha,wav_path=str(wav.relative_to(PROJECT)),
                sample_rate=fmt[0],channels=fmt[1],sample_count=fmt[3],duration_sec=round(fmt[3]/fmt[0],6),reference_count=len(rows))


def run():
    for name in ['original-wav','decoder-input','decoder-metadata']: (OUT/name).mkdir(parents=True,exist_ok=True)
    rows=csv_read(OUT/'audio-resource-references.csv');groups=collections.defaultdict(list)
    for r in rows:
        if r['status']!='OK':continue
        with (GAME/r['source_path']).open('rb') as f:
            f.seek(int(r['stream_offset']));payload=f.read(int(r['stream_size']))
        assert len(payload)==int(r['stream_size'])
        r['encoded_sha256']=hashlib.sha256(payload).hexdigest()
        # Different formats cannot be merged just because compressed bytes match.
        key=hashlib.sha256(('|'.join(r[k] for k in ['encoded_sha256','codec','sample_count','sample_rate','channels'])).encode()).hexdigest()
        r['encoded_key']=key;groups[key].append(r)
    csv_write(OUT/'audio-resource-references.csv',rows)
    result=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,r in enumerate(pool.map(extract_one,groups.items()),1):
            result.append(r)
            if i%100==0: print(f'Decoded {i}/{len(groups)}',flush=True)
    csv_write(OUT/'decoded-unique-resources.csv',result)
    corpus=[]
    for r in csv_read(PROJECT/'manifests/corpus.csv'):
        p=PROJECT/'corpus/wav/original-en'/r['wav_file']
        fmt,pcmsha=pcm_identity(p)
        corpus.append(dict(id=r['id'],pcm_sha256=pcmsha,sample_rate=fmt[0],channels=fmt[1],sample_count=fmt[3],
                           wav_path=str(p.relative_to(PROJECT)),installed_turkish=int((GAME/'system/sc-tr-audio'/f'{r["id"]}.wav').exists())))
    csv_write(OUT/'original-corpus-pcm.csv',corpus)
    print('Decoded',len(result),'status',dict(collections.Counter(r['status'] for r in result)),flush=True)
if __name__=='__main__':run()
