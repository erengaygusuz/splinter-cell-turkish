"""Cache source-bound Turkish word timestamps; never treat ASR as listening approval."""
import argparse, json, os
from pathlib import Path
from catalog import ROOT, QA, sha, write

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',default='medium');p.add_argument('--device',default='cuda');p.add_argument('--videos',nargs='*');args=p.parse_args()
 from faster_whisper import WhisperModel
 model=WhisperModel(args.model,device=args.device,compute_type='int8_float16' if args.device=='cuda' else 'int8',cpu_threads=8)
 inv=json.loads((QA/'inventory.json').read_text())
 for source in inv['sources']:
  if args.videos and source['video'][:2] not in args.videos:continue
  path=ROOT/source['path'];digest=sha(path)
  out=ROOT/'work/fmv-dub/R001_20261029/asr'/source['video']/(path.stem+'_'+args.model+'.json')
  if out.exists() and json.loads(out.read_text()).get('sha256')==digest:continue
  segs,info=model.transcribe(str(path),language='tr',word_timestamps=True,beam_size=5,vad_filter=False,condition_on_previous_text=False)
  result=[]
  for s in segs:result.append(dict(start=s.start,end=s.end,text=s.text,words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words]))
  write(out,dict(source=source['path'],sha256=digest,model=args.model,language='tr',segments=result))
  print(source['video'],path.name,len(result),'segments',flush=True)
if __name__=='__main__':main()
