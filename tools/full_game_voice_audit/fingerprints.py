#!/usr/bin/env python3
"""Conservative lossy-codec duplicate detection using complete PCM waveforms.

Equal format/sample count only narrows the search; it NEVER establishes a
match. Full signal correlation and residual SNR are required as well.
"""
import collections, json, math, wave
import numpy as np
from inventory import PROJECT,OUT,csv_read,csv_write,json_write


def samples(path):
    with wave.open(str(path),'rb') as w:
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)


def compare(a,b):
    a=a-a.mean();b=b-b.mean();aa=float(a@a);bb=float(b@b)
    if aa<1 or bb<1:return 0.0,0.0
    dot=float(a@b);corr=dot/math.sqrt(aa*bb)
    residual=max(aa-dot*dot/bb,1e-12);snr=10*math.log10(aa/residual)
    return corr,snr


def run():
    original=csv_read(OUT/'original-corpus-pcm.csv');decoded=csv_read(OUT/'decoded-unique-resources.csv')
    names={r['new_id']:r['resource_name'] for r in csv_read(OUT/'all-unique-audio-resources.csv')}
    corpus=collections.defaultdict(list);groups=collections.defaultdict(list)
    fmt=lambda r:(r['sample_rate'],r['channels'],r['sample_count'])
    for r in original:corpus[fmt(r)].append(r)
    for r in decoded:groups[fmt(r)].append(r)
    matches=[];cache={}
    def pcm(r):
        key=r['wav_path']
        if key not in cache:cache[key]=samples(PROJECT/key)
        return cache[key]
    for key,rows in groups.items():
        for r in rows:
            for c in corpus[key]:
                if r['pcm_sha256']==c['pcm_sha256']:continue
                corr,snr=compare(pcm(r),pcm(c))
                if corr>=0.995 and snr>=20:
                    matches.append(dict(new_id=r['new_id'],matched_id=c['id'],match_kind='ORIGINAL_CORPUS_WAVEFORM',
                        correlation=corr,residual_snr_db=snr,sample_rate=key[0],channels=key[1],sample_count=key[2]))
        for i,r in enumerate(rows):
            for other in rows[:i]:
                if r['pcm_sha256']==other['pcm_sha256']:continue
                corr,snr=compare(pcm(r),pcm(other))
                a_name=names[r['new_id']];b_name=names[other['new_id']]
                named_reencode=(a_name.rsplit('.',1)[0]==b_name.rsplit('.',1)[0] and {a_name.rsplit('.',1)[-1],b_name.rsplit('.',1)[-1]}=={'wav','ima'})
                if (corr>=0.995 and snr>=20) or (named_reencode and corr>=0.985 and snr>=15):
                    matches.append(dict(new_id=r['new_id'],matched_id=other['new_id'],match_kind='NAMED_WAV_IMA_WAVEFORM' if named_reencode else 'CROSS_CODEC_WAVEFORM',
                        correlation=corr,residual_snr_db=snr,sample_rate=key[0],channels=key[1],sample_count=key[2]))
        cache.clear()
    csv_write(OUT/'waveform-matches.csv',matches,['new_id','matched_id','match_kind','correlation','residual_snr_db','sample_rate','channels','sample_count'])
    print('Signal-supported lossy matches',len(matches),dict(collections.Counter(x['match_kind'] for x in matches)),flush=True)
if __name__=='__main__':run()
