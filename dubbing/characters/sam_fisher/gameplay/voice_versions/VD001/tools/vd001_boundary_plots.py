#!/usr/bin/env python3
"""Render source waveforms around every selected inter-line cut; no audio changes."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import vd001_audio_qa as qa


def main():
    qa.check_protected()
    _, sources = qa.load_inputs()
    cuts = qa.selected_cuts()
    pcm = {s['key']: qa.decode(s['path']) for s in sources}
    boundaries = []
    for s in sources:
        rows = sorted((r for r in cuts if r['source_key'] == s['key']), key=lambda r: int(r['start_sample']))
        for left, right in zip(rows, rows[1:]):
            assert left['end_sample_exclusive'] == right['start_sample']
            boundaries.append((s['key'], left['id'], right['id'], int(right['start_sample'])))
    folder = qa.QA / 'boundary_plots'
    folder.mkdir(exist_ok=True)
    manifest = []
    for page in range((len(boundaries)+19)//20):
        fig, axes = plt.subplots(10, 2, figsize=(14, 16), constrained_layout=True)
        for ax, item in zip(axes.flat, boundaries[page*20:(page+1)*20]):
            key, left, right, cut = item
            data = pcm[key]
            a, b = max(0, cut-qa.RATE), min(len(data), cut+qa.RATE)
            # Peak envelopes preserve brief consonants; fixed dB scale exposes low-level tails.
            edges = np.arange(a, b, 44)
            peak = np.array([max(1, np.max(np.abs(data[x:min(b,x+44)].astype(float)))) for x in edges])
            ax.plot((edges-cut)/qa.RATE, 20*np.log10(peak/32768), lw=.55)
            ax.axvline(0, color='red', lw=1)
            ax.axhline(-55, color='grey', lw=.4, linestyle=':')
            ax.set(xlim=(-1, 1), ylim=(-92, 0), title=f'{left} | {right}  {key[-6:]}  {cut/qa.RATE:.3f}s')
            ax.tick_params(labelsize=7)
            ax.title.set_fontsize(9)
            manifest.append(dict(left_id=left, right_id=right, source_key=key,
                boundary_sample=cut, boundary_sec=cut/qa.RATE, page=f'boundaries_{page+1:02d}.png'))
        for ax in list(axes.flat)[len(boundaries[page*20:(page+1)*20]):]:
            ax.set_visible(False)
        path = folder / f'boundaries_{page+1:02d}.png'
        fig.savefig(path, dpi=110)
        plt.close(fig)
    qa.write_tsv(folder / 'index.tsv', manifest)
    fig, axes = plt.subplots(len(sources), 2, figsize=(13, 6), constrained_layout=True)
    for i, source in enumerate(sources):
        data = pcm[source['key']]
        for j, (a, b) in enumerate([(0, qa.RATE), (len(data)-qa.RATE, len(data))]):
            edges = np.arange(a,b,44)
            peak = np.array([max(1,np.max(np.abs(data[x:min(b,x+44)].astype(float)))) for x in edges])
            ax = axes[i,j]
            ax.plot(edges/qa.RATE,20*np.log10(peak/32768),lw=.65)
            ax.set(ylim=(-92,0), title=source['key']+(' START' if j == 0 else ' END'))
    fig.savefig(folder / 'source_edges.png', dpi=110)
    plt.close(fig)
    print(len(boundaries), 'boundaries on', page+1, 'pages')


if __name__ == '__main__':
    main()
