"""Render review-only 48 kHz mixes. Masters remain unprocessed and immutable."""
import json, math, subprocess
from pathlib import Path
import numpy as np
from catalog import ROOT, QA, write, sha
from cut import RUN, RATE, audio

def run_audio(path,filters):
 cmd=['ffmpeg','-v','error','-i',str(path),'-af',filters,'-ar',str(RATE),'-ac','1','-f','f32le','-']
 return np.frombuffer(subprocess.check_output(cmd),dtype='<f4').copy()
def active_edges(x):
 hop=240;n=len(x)//hop
 levels=np.sqrt(np.mean(x[:n*hop].reshape(n,hop)**2,axis=1))
 active=np.flatnonzero(levels>max(0.0015,float(levels.max())*0.015))
 if not len(active):return 0,len(x)/RATE
 return max(0,(active[0]*hop)/RATE-0.06),min(len(x)/RATE,((active[-1]+1)*hop)/RATE+0.10)
def loudness(path):
 p=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af','loudnorm=I=-20:TP=-1:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 return json.JSONDecoder().raw_decode(p.stderr[p.stderr.rfind('{'):])[0]
def main():
 cuts=json.loads((QA/'cuts_v01.json').read_text());inv=json.loads((QA/'inventory.json').read_text());report=[]
 revisions=QA/'cut_revisions_v02.json'
 if revisions.exists():
  rr={(r['video'],r['id']):r for r in json.loads(revisions.read_text())}
  cuts=[rr.get((r['video'],r['id']),r) for r in cuts]
 for v in inv['videos']:
  video=v['video'];out=RUN/'review_pending'/video/'mix_v01';out.mkdir(parents=True,exist_ok=True)
  rows=[r for r in cuts if r['video']==video];provenance=dict(background_sha256=v['background_sha256'],masters=[r['master_sha256'] for r in rows],settings='mix_v01-atempo_max_1.20-voice_-20LUFS-background_duck_-4dB')
  checkpoint=out/'mix.json'
  if checkpoint.exists():
   prior=json.loads(checkpoint.read_text());assert prior['provenance']==provenance, 'Inputs changed; use a new mix version'
   report.append(prior);continue
  bg=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',v['background'],'-ar',str(RATE),'-ac','2','-f','f32le','-']),dtype='<f4').reshape(-1,2).copy()
  frames=round(float(v['metadata']['format']['duration'])*RATE);bg=bg[:frames]
  if len(bg)<frames:bg=np.pad(bg,((0,frames-len(bg)),(0,0)))
  voices=np.zeros_like(bg);duck=np.zeros(len(bg),np.float32);details=[]
  for r in rows:
   x=audio(ROOT/r['master']);a,b=active_edges(x);body=b-a;slot=r['end']-r['start'];needed=max(1,body/(slot+0.25));tempo=min(1.2,needed)
   if tempo<1.03:tempo=1.0
   name=r['speaker'].lower();fx='highpass=f=70,lowpass=f=12000';kind='natural'
   if 'lambert' in name:fx='highpass=f=230,lowpass=f=4200';kind='radio'
   elif 'sarah' in name and video[:2] in ('07','10','16'):fx='highpass=f=270,lowpass=f=3900';kind='phone'
   elif 'pilot' in name:fx='highpass=f=260,lowpass=f=4300';kind='intercom'
   y=run_audio(ROOT/r['master'],f'atrim=start={a}:end={b},asetpts=PTS-STARTPTS,atempo={tempo},{fx}')
   tmp=out/(r['id']+'_fx.wav')
   if tmp.exists():
    old=audio(tmp);assert len(old)==len(y) and np.max(np.abs(old-y))<1e-7
   else:subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar',str(RATE),'-ac','1','-i','-','-c:a','pcm_f32le',str(tmp)],input=y.astype('<f4').tobytes(),check=True)
   measure=loudness(tmp);integrated=float(measure['input_i'])
   if not math.isfinite(integrated):
    active=y[np.abs(y)>max(0.002,float(np.max(np.abs(y)))*.025)]
    integrated=20*math.log10(max(1e-8,float(np.sqrt(np.mean(active**2))))) - 0.7
    measure['short_clip_fallback']='active_RMS_minus_0.7dB'
   gain=np.clip(-20-integrated,-14,14);y*=10**(gain/20)
   # Constant gain, not per-line limiting; the final mix limiter handles rare peaks.
   start=round(r['start']*RATE);end=start+len(y);clipped=end>frames
   if start>=frames:raise ValueError((video,r['id'],'Starts after video'))
   end=min(end,frames);voices[start:end]+=y[:end-start,None]
   ramp=round(.25*RATE);lo=max(0,start-ramp);hi=min(frames,end+ramp)
   env=np.ones(hi-lo,np.float32)
   if start>lo:env[:start-lo]=np.linspace(0,1,start-lo)
   if hi>end:env[end-lo:]=np.linspace(1,0,hi-end)
   duck[lo:hi]=np.maximum(duck[lo:hi],env)
   late=r['start']+len(y)/RATE-r['end'];flags=[]
   if late>.5:flags.append('END_OVERHANG_REVIEW')
   if needed>1.2:flags.append('TEMPO_CAP_REACHED')
   if clipped:flags.append('VIDEO_END_TRUNCATION')
   details.append(dict(id=r['id'],master=r['master'],master_sha256=r['master_sha256'],trim_start=a,trim_end=b,tempo=tempo,needed_tempo=needed,effect=kind,gain_db=float(gain),loudness_measurement=measure,start=r['start'],end=r['start']+len(y)/RATE,reference_end=r['end'],overhang=late,flags=flags))
  mix=bg*(10**(-4*duck/20))[:,None]+voices
  final=out/'turkish_mix_48k.wav'
  subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar',str(RATE),'-ac','2','-i','-','-af','alimiter=limit=0.97:level=false:latency=true','-c:a','pcm_s24le',str(final)],input=mix.astype('<f4').tobytes(),check=True)
  flac=out/'turkish_mix_48k.flac'
  subprocess.run(['ffmpeg','-v','error','-n','-i',str(final),'-c:a','flac',str(flac)],check=True)
  result=dict(video=video,provenance=provenance,mix=str(final.relative_to(ROOT)),mix_sha256=sha(final),duration=frames/RATE,prelimit_peak=float(np.max(np.abs(mix))),units=details,listened=False,watched=False,game_tested=False,status='REVIEW_PENDING')
  write(checkpoint,result);report.append(result);write(QA/'mixes_v01.json',report)
  print(video,len(rows),'lines; flags',sum(bool(r['flags']) for r in details),flush=True)
 write(QA/'mixes_v01.json',report)
if __name__=='__main__':main()
