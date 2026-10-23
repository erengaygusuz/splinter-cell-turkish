#!/usr/bin/env python3
from pipeline import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(stage):
 rows=tsv(Q/f'boundaries_{stage}.tsv');sources={s['key']:s for s in load(Q/'sources.json')}
 out=Q/'plots'/stage;out.mkdir(parents=True,exist_ok=True);cache={}
 for page in range((len(rows)+19)//20):
  subset=rows[page*20:(page+1)*20];fig,axes=plt.subplots(10,2,figsize=(14,16))
  for ax,r in zip(axes.flat,subset):
   key=r['source_key']
   if key not in cache:cache[key]=common.decode(ROOT/sources[key]['path'])
   pcm=cache[key];t=float(r['time']);a=max(0,round((t-.6)*RATE));b=min(len(pcm),round((t+.6)*RATE));hop=110
   x=pcm[a:b];x=x[:len(x)//hop*hop].astype(float).reshape(-1,hop)/32768
   rms=20*np.log10(np.maximum(np.sqrt(np.mean(x*x,axis=1)),1e-5));times=(a+np.arange(len(rms))*hop)/RATE-t
   ax.plot(times,rms,lw=.8);ax.axvline(0,color='red',lw=1);ax.set_ylim(-95,0);ax.set_title(r['left']+' | '+r['right']+' '+f'{t:.3f}s',fontsize=8)
  for ax in list(axes.flat)[len(subset):]:ax.axis('off')
  fig.tight_layout();fig.savefig(out/f'boundaries_{page+1:02d}.png',dpi=100);plt.close(fig)
 print('Boundary pages',stage,(len(rows)+19)//20)
if __name__=='__main__':
 import sys
 plot(sys.argv[1])
