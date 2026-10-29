"""Create browser review proxies; the source BIK video is never modified."""
import json,subprocess
from concurrent.futures import ThreadPoolExecutor
from catalog import ROOT,QA,write,sha
from cut import RUN

def render(pair):
 v,m=pair;out=RUN/'review_pending'/v['video']/'preview_v01.mp4';meta=out.with_suffix('.json')
 stamp=dict(bik_sha256=v['bik_sha256'],mix_sha256=m['mix_sha256'],preset='h264-crf22-aac192-review-only')
 if out.exists() and meta.exists():
  assert json.loads(meta.read_text())==stamp
  return str(out.relative_to(ROOT))
 temp=out.with_name('preview_v01.partial.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/v['bik']),'-i',str(ROOT/m['mix']),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',str(temp)],check=True)
 temp.rename(out);write(meta,stamp);print(v['video'],'preview ready',flush=True)
 return str(out.relative_to(ROOT))
def main():
 inv=json.loads((QA/'inventory.json').read_text());mixes=json.loads((QA/'mixes_v01.json').read_text());mm={m['video']:m for m in mixes}
 with ThreadPoolExecutor(max_workers=2) as pool:paths=list(pool.map(render,[(v,mm[v['video']]) for v in inv['videos']]))
 write(QA/'previews_v01.json',paths)
if __name__=='__main__':main()
