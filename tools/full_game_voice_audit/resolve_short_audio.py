#!/usr/bin/env python3
"""Target a third, no-VAD large-v3 pass at conflicting short voice decisions."""
import argparse
from inventory import PROJECT,OUT,csv_read,json_write
from faster_whisper import WhisperModel

def run():
    p=argparse.ArgumentParser();p.add_argument('--device',default='cpu',choices=['cpu','cuda']);args=p.parse_args()
    rows=[r for r in csv_read(OUT/'all-audio-decisions.csv') if (r['classification']=='REVIEW_REQUIRED' or r['text_qa']=='TEXT_REVIEW_REQUIRED') and r['speaker_or_archetype']!='radio']
    model=WhisperModel('large-v3',device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=2,local_files_only=True)
    print('Focused no-VAD queue',len(rows),flush=True)
    for i,r in enumerate(rows,1):
        path=OUT/'asr-large-v3-no-vad'/f'{r["new_id"]}.json'
        if path.exists():continue
        segs,info=model.transcribe(str(PROJECT/r['wav_path']),language='en',vad_filter=False,word_timestamps=True,
                condition_on_previous_text=False,temperature=0,beam_size=5,max_new_tokens=96)
        segments=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                        words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in segs]
        text=' '.join(s['text'].strip() for s in segments)
        json_write(path,dict(new_id=r['new_id'],pcm_sha256=r['pcm_sha256'],model='large-v3',vad_filter=False,text=text,segments=segments,
                 avg_logprob=sum(s['avg_logprob'] for s in segments)/len(segments) if segments else None,
                 no_speech_prob=max((s['no_speech_prob'] for s in segments),default=None)))
        print(f'{i}/{len(rows)} {r["resource_name"]} {text}',flush=True)
if __name__=='__main__':run()
