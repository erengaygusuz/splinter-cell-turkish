from pipeline import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main(stage):
 sources=[r for r in load(Q/'sources.json') if r['stage']==stage]
 out=Q/'plots'/stage;out.mkdir(exist_ok=True,parents=True)
 for page in range((len(sources)+6)//7):
  subset=sources[page*7:page*7+7];fig,axes=plt.subplots(len(subset),2,figsize=(14,max(3,len(subset)*2)),squeeze=False)
  for i,s in enumerate(subset):
   pcm=common.decode(ROOT/s['path']);duration=len(pcm)/RATE
   for j,a in enumerate([0,max(0,duration-1)]):
    chunk=pcm[round(a*RATE):round((a+1)*RATE)];hop=110;chunk=chunk[:len(chunk)//hop*hop].astype(float).reshape(-1,hop)/32768
    rms=20*np.log10(np.maximum(np.sqrt(np.mean(chunk*chunk,axis=1)),1e-5));axes[i,j].plot(a+np.arange(len(rms))*hop/RATE,rms,lw=.8);axes[i,j].set_ylim(-95,0);axes[i,j].set_title(s['key']+(' START' if j==0 else ' END'),fontsize=8)
  fig.tight_layout();fig.savefig(out/f'source_edges_{page+1:02d}.png',dpi=100);plt.close(fig)
if __name__=='__main__':
 import sys
 main(sys.argv[1])
