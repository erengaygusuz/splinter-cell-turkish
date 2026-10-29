"""Validate generated media and immutable inputs, without starting Wine or a game."""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from catalog import ROOT,QA,sha,probe,write

def check_video(v):
 m=next(m for m in MIXES if m['video']==v['video']);p=ROOT/m['mix'];md=probe(p);a=md['streams'][0]
 assert a['sample_rate']=='48000' and a['channels']==2 and a['codec_name']=='pcm_s24le'
 assert abs(float(md['format']['duration'])-float(v['metadata']['format']['duration']))<1/48000+.000001
 x=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-']),dtype='<f4')
 peak=float(np.max(np.abs(x)));assert peak<=.971 and np.isfinite(x).all()
 preview=ROOT/'work/fmv-dub/R001_20261029/review_pending'/v['video']/'preview_v01.mp4';pm=probe(preview)
 vv=next(s for s in pm['streams'] if s['codec_type']=='video');sv=next(s for s in v['metadata']['streams'] if s['codec_type']=='video')
 assert int(vv['nb_frames'])==int(sv.get('nb_frames',sv['duration_ts'])), (v['video'],vv['nb_frames'],sv.get('nb_frames',sv['duration_ts']))
 subprocess.run(['ffmpeg','-v','error','-xerror','-threads','2','-i',str(preview),'-f','null','-'],check=True,capture_output=True)
 return dict(video=v['video'],audio_rate=48000,channels=2,peak=peak,mix_sha256=sha(p),preview_frames=int(vv['nb_frames']),source_frames=int(sv.get('nb_frames',sv['duration_ts'])),preview_decode='PASS',listened=False,watched=False,game_tested=False)
if __name__=='__main__':
 inv=json.loads((QA/'inventory.json').read_text());MIXES=json.loads((QA/'mixes_v01.json').read_text())
 sources=[]
 for s in inv['sources']:
  actual=sha(ROOT/s['path']);assert actual==s['sha256'];sources.append(dict(source=s['path'],hash_unchanged=True))
 for v in inv['videos']:
  assert sha(ROOT/v['bik'])==v['bik_sha256'];assert sha(v['background'])==v['background_sha256']
 with ThreadPoolExecutor(max_workers=2) as pool:media=list(pool.map(check_video,inv['videos']))
 rows=json.loads((QA/'qa_decisions_v01.json').read_text());assert len(rows)==len({(r['video'],r['id']) for r in rows})==192
 for r in rows:assert sha(ROOT/r['master'])==r['master_sha256']
 write(QA/'validation.json',dict(sources=sources,videos=media,masters_verified=192,original_biks_unchanged=17,backgrounds_unchanged=17,wine_started=False,game_started=False))
 print('PASS: 18 raw MP3 hashes; 17 original BIKs; 192 selected masters; 17 complete preview decodes and 48 kHz stereo mixes')
