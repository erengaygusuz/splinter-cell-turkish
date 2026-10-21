#!/usr/bin/env python3
"""Render source waveforms and selected boundaries. Requires matplotlib/numpy."""
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import fisher_boundary_qa_v3 as qa


def main():
    qa.check_inputs()
    clips, sources = qa.load_archive()
    old = {c['id']: c for c in clips}
    pcm = {batch: qa.decode(path).astype(float) / 32768 for batch, path in sources.items()}
    rows = qa.read_tsv(qa.OUT / 'fisher_qa_decisions.tsv')
    dest = qa.OUT / 'waveforms'
    dest.mkdir(exist_ok=True)
    groups = [('all', rows, 20), ('recut', [r for r in rows if r['selected_version'] == 'v03_candidate'], 9)]
    links = []
    for group, group_rows, size in groups:
        for offset in range(0, len(group_rows), size):
            page = group_rows[offset:offset + size]
            columns = 2 if group == 'all' else 1
            nrows = (len(page) + columns - 1) // columns
            fig, axes = plt.subplots(nrows, columns, figsize=(16, nrows * 1.75), squeeze=False)
            for ax, r in zip(axes.flat, page):
                start, end = float(r['source_start_sec']), float(r['source_end_sec'])
                x = pcm[r['batch']]
                lo, hi = max(0, round((start-.20)*qa.RATE)), min(len(x), round((end+.20)*qa.RATE))
                # Min/max envelope preserves short bursts when downsampling for display.
                hop = max(1, (hi-lo)//1600)
                segment = x[lo:hi]
                segment = segment[:len(segment)//hop*hop].reshape(-1, hop)
                time = (lo + np.arange(len(segment))*hop) / qa.RATE
                ax.fill_between(time, segment.min(axis=1), segment.max(axis=1), color='#28628a', lw=.2)
                ax.axvline(start, color='#008000', lw=1)
                ax.axvline(end, color='#008000', lw=1)
                ax.axvspan(time[0], start, alpha=.12, color='grey')
                ax.axvspan(end, time[-1], alpha=.12, color='grey')
                if group == 'recut':
                    for boundary in [old[r['id']]['start'], old[r['id']]['end']]:
                        if time[0] < boundary < time[-1]:
                            ax.axvline(boundary, color='#c02020', linestyle='--', lw=.9)
                title = f"{r['id']}  {r['selected_version']}  {start:.3f}–{end:.3f} s | {r['expected_text']}"
                ax.set_title('\n'.join(textwrap.wrap(title, width=105 if columns == 1 else 73)), fontsize=8, loc='left')
                peak = max(.04, float(np.max(np.abs(x[lo:hi])))*1.1)
                ax.set(xlim=(time[0], time[-1]), ylim=(-peak, peak))
                ax.tick_params(labelsize=6)
                ax.grid(alpha=.2)
            for ax in list(axes.flat)[len(page):]:
                ax.axis('off')
            fig.suptitle('Source waveform — green: selected bounds; red dashed: old v01 bounds. NOT listening approval.', fontsize=10)
            fig.tight_layout(rect=(0, 0, 1, .98))
            name = f'{group}_{offset//size+1:02d}.png'
            fig.savefig(dest / name, dpi=115)
            plt.close(fig)
            links.append(f'<h2>{name}</h2><img style="max-width:100%" src="{name}">')
    (dest / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Fisher source waveforms</title>'
        '<h1>201 source waveforms and 27 recuts</h1><p>Visual evidence only; no listening approval.</p>'
        + ''.join(links), encoding='utf-8')
    print(f'{len(links)} waveform sheets rendered.')


if __name__ == '__main__':
    main()
