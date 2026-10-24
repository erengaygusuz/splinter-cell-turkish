#!/usr/bin/env python3
"""Resume isolated English ASR. No translations or audio installation."""
import argparse, json, time
from inventory import PROJECT,OUT,csv_read,json_write


def run():
    p=argparse.ArgumentParser();p.add_argument('--device',choices=['cpu','cuda'],default='cpu');p.add_argument('--threads',type=int,default=4);p.add_argument('--limit',type=int);p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);args=p.parse_args()
    from faster_whisper import WhisperModel
    dest=OUT/'asr-large-v3';dest.mkdir(parents=True,exist_ok=True)
    rows=[r for r in csv_read(OUT/'all-unique-audio-resources.csv') if r['classification']=='PENDING_ASR']
    rows.sort(key=lambda r:(not ('GeorgianCop' in r['speaker_or_archetype']),not ('Tbilisi' in r['map']),r['new_id']))
    rows=[r for i,r in enumerate(rows) if i%args.shards==args.shard and not (dest/f'{r["new_id"]}.json').exists()]
    if args.limit:rows=rows[:args.limit]
    print(f'ASR queue {len(rows)}; large-v3 {args.device}/int8 threads={args.threads}',flush=True)
    model=WhisperModel('large-v3',device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=args.threads,local_files_only=True)
    for i,r in enumerate(rows,1):
        t=time.monotonic();segments,info=model.transcribe(str(PROJECT/r['wav_path']),language='en',beam_size=5,word_timestamps=True,
                    condition_on_previous_text=False,vad_filter=True,temperature=0)
        segs=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                    words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in segments]
        text=' '.join(s['text'].strip() for s in segs).strip()
        json_write(dest/f'{r["new_id"]}.json',dict(new_id=r['new_id'],wav_path=r['wav_path'],pcm_sha256=r['pcm_sha256'],model='large-v3',device=args.device,language='en',
                    text=text,segments=segs,avg_logprob=sum(s['avg_logprob'] for s in segs)/len(segs) if segs else None,
                    no_speech_prob=max((s['no_speech_prob'] for s in segs),default=None),elapsed_sec=round(time.monotonic()-t,3)))
        print(f'{i}/{len(rows)} {r["new_id"]} {r["resource_name"]} {text} ({time.monotonic()-t:.1f}s)',flush=True)
if __name__=='__main__':run()
