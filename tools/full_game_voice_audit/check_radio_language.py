#!/usr/bin/env python3
"""Do not force Russian background radio into an English transcription."""
import argparse
from inventory import PROJECT,OUT,csv_read,json_write
from faster_whisper import WhisperModel

def run():
    p=argparse.ArgumentParser();p.add_argument('--device',default='cpu',choices=['cpu','cuda']);args=p.parse_args()
    model=WhisperModel('large-v3',device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=2,local_files_only=True)
    for r in csv_read(OUT/'full-game-voice-candidates.csv'):
        if r['speaker_or_archetype']!='radio':continue
        path=OUT/'radio-language'/f'{r["new_id"]}.json'
        if path.exists():continue
        segs,info=model.transcribe(str(PROJECT/r['wav_path']),language=None,task='transcribe',beam_size=5,
                                  vad_filter=False,condition_on_previous_text=False,word_timestamps=True)
        segments=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
            words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in segs]
        result=dict(new_id=r['new_id'],pcm_sha256=r['pcm_sha256'],model='large-v3',language=info.language,language_probability=info.language_probability,
                    all_language_probs=info.all_language_probs,text=' '.join(s['text'].strip() for s in segments),segments=segments)
        json_write(path,result)
        print(r['new_id'],r['event_name'],info.language,info.language_probability,result['text'],flush=True)
if __name__=='__main__':run()
