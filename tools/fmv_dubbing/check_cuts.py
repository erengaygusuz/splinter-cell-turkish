"""Independent ASR of exported masters, cached by content hash."""
import json
from pathlib import Path
from catalog import ROOT,QA,sha,write,norm
from difflib import SequenceMatcher
from faster_whisper import WhisperModel

def main():
 rows=json.loads((QA/'cuts_v01.json').read_text())
 revisions=QA/'cut_revisions_v02.json'
 if revisions.exists():
  rr={(r['video'],r['id']):r for r in json.loads(revisions.read_text())}
  rows=[rr.get((r['video'],r['id']),r) for r in rows]
 model=WhisperModel('medium',device='cuda',compute_type='int8_float16')
 result=[]
 for i,r in enumerate(rows):
  p=ROOT/r['master'];out=ROOT/'work/fmv-dub/R001_20261029/cut_asr'/r['video']/(r['id']+('_medium_v02.json' if r['master'].endswith('_v02.wav') else '_medium.json'));h=sha(p)
  if out.exists() and json.loads(out.read_text()).get('sha256')==h:j=json.loads(out.read_text())
  else:
   ss,_=model.transcribe(str(p),language='tr',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
   segments=[dict(start=s.start,end=s.end,text=s.text,words=[dict(start=w.start,end=w.end,word=w.word) for w in s.words]) for s in ss]
   j=dict(sha256=h,model='medium',segments=segments);write(out,j)
  text=' '.join(s['text'].strip() for s in j['segments']);score=SequenceMatcher(None,norm(r['text']),norm(text),autojunk=False).ratio()
  result.append(dict(video=r['video'],id=r['id'],text=text,similarity=round(score,4),master_sha256=h,listened=False))
  write(QA/('cut_asr_v02.json' if revisions.exists() else 'cut_asr_v01.json'),result)
  if (i+1)%20==0:print(i+1,'/',len(rows),flush=True)
 print('complete',len(result),flush=True)
if __name__=='__main__':main()
