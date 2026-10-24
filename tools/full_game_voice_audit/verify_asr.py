#!/usr/bin/env python3
"""Independent English medium.en pass without VAD for short/suppressed speech."""
import argparse,time
from inventory import PROJECT,OUT,csv_read,json_write

def run():
    p=argparse.ArgumentParser();p.add_argument('--device',default='cuda');args=p.parse_args()
    from faster_whisper import WhisperModel
    dest=OUT/'asr-medium-en-no-vad';dest.mkdir(parents=True,exist_ok=True)
    rows=[r for r in csv_read(OUT/'all-unique-audio-resources.csv') if r['classification']=='PENDING_ASR' and not (dest/f'{r["new_id"]}.json').exists()]
    rows.sort(key=lambda r:(r['new_id']!='v_e066ee2c634b8938',r['new_id']))
    print('Independent medium.en no-VAD queue',len(rows),flush=True)
    model=WhisperModel('medium.en',device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=2,local_files_only=True)
    for i,r in enumerate(rows,1):
        start=time.monotonic()
        segments,info=model.transcribe(str(PROJECT/r['wav_path']),language='en',beam_size=5,word_timestamps=True,
             condition_on_previous_text=False,vad_filter=False,temperature=0,max_new_tokens=160)
        segments=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                       words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in segments]
        text=' '.join(s['text'].strip() for s in segments).strip()
        json_write(dest/f'{r["new_id"]}.json',dict(new_id=r['new_id'],pcm_sha256=r['pcm_sha256'],model='medium.en',device=args.device,
                    vad_filter=False,text=text,segments=segments,avg_logprob=sum(s['avg_logprob'] for s in segments)/len(segments) if segments else None,
                    no_speech_prob=max((s['no_speech_prob'] for s in segments),default=None)))
        if i%20==0:print(f'{i}/{len(rows)} {r["new_id"]} {text} {time.monotonic()-start:.2f}s',flush=True)
if __name__=='__main__':run()
