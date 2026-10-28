#!/usr/bin/env python3
"""Resumable Turkish ASR with no supplied text prompt and per-source hashes."""
from common import *
import argparse,time

def run():
    p=argparse.ArgumentParser();p.add_argument('--device',choices=['cpu','cuda'],default='cuda');p.add_argument('--model',default='medium');p.add_argument('--mode',choices=['source','clips'],default='source');p.add_argument('--only-text-review',action='store_true');args=p.parse_args()
    from faster_whisper import WhisperModel
    model=None
    if args.mode=='source':jobs=[dict(key=s['source_key'],path=s['decoded_wav'],sha256=s['decoded_sha256']) for s in read(QA/'sources.json')]
    else:jobs=[dict(key=r['new_id']+'_'+r['version'],path=r['output_wav_path'],sha256=r['output_wav_sha256']) for r in read(QA/'cuts.json')]
    if args.only_text_review:
        assert args.mode=='clips'
        wanted={r['new_id']+'_'+r['version'] for r in rows(QA/'qa_1258.csv') if 'TEXT_MISMATCH' in r.get('qa_flags','')}
        jobs=[j for j in jobs if j['key'] in wanted]
    dest=QA/(args.mode+'_asr_'+args.model)
    for i,j in enumerate(jobs,1):
        out=dest/(j['key']+'.json')
        if out.exists():assert read(out)['sha256']==j['sha256'];continue
        path=ROOT/j['path'];assert sha(path)==j['sha256']
        if model is None:model=WhisperModel(args.model,device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=4,local_files_only=True)
        start=time.monotonic();segments,info=model.transcribe(str(path),language='tr',task='transcribe',beam_size=5,
            word_timestamps=True,condition_on_previous_text=False,vad_filter=False,temperature=0)
        d=dict(**j,model=args.model,device=args.device,language='tr',initial_prompt=None,vad_filter=False,segments=[],words=[])
        for s in segments:
            d['segments'].append(dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob))
            d['words'].extend(dict(start=w.start,end=w.end,text=w.word,probability=w.probability) for w in s.words or [])
            save(out.with_suffix('.partial.json'),d)
        d['text']=' '.join(s['text'].strip() for s in d['segments']);d['elapsed_seconds']=round(time.monotonic()-start,2)
        save(out,d,True)
        print(f'{i}/{len(jobs)} {j["key"]} {len(d["words"])} words {d["elapsed_seconds"]}s',flush=True)

if __name__=='__main__':run()
