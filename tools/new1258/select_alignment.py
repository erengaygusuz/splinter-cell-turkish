#!/usr/bin/env python3
"""Compare two full-source passes; prefer complete coverage over model size."""
from common import *

def run():
    expected=read(QA/'resolved_expected.json');report=[]
    for source in read(QA/'sources.json'):
        subset=[r for r in expected if r['source_key']==source['source_key']];choices=[]
        for name in ('medium','large-v3'):
            p=QA/('source_asr_'+name)/(source['source_key']+'.json');d=read(p)
            assert d['sha256']==source['decoded_sha256']
            matched,unknown=alignment.match_words([dict(id=r['new_id'],expected_text=r['expected_text']) for r in subset],d['words'])
            scores=[alignment.score(r['expected_text'],' '.join(w['text'] for w in matched[r['new_id']])) for r in subset]
            stats=dict(source_key=source['source_key'],model=name,missing_lines=sum(not matched[r['new_id']] for r in subset),
                low_match_lines=sum(s<85 for s in scores),mean_line_score=sum(scores)/len(scores),
                whole_text_score=alignment.score(' '.join(r['expected_text'] for r in subset),d['text']),cache_sha256=sha(p),cache_path=rel(p))
            choices.append((stats,d));report.append(stats)
        best=min(choices,key=lambda pair:(pair[0]['missing_lines'],pair[0]['low_match_lines'],-pair[0]['mean_line_score']))
        for stats,_ in choices:stats['selected']=stats is best[0]
        save(QA/'source_asr_selected'/(source['source_key']+'.json'),dict(best[1],selection_evidence=best[0]),True)
    table(QA/'source_asr_comparison.csv',report)
    print('Selected complete source alignment for',len(report)//2,'MP3s')

if __name__=='__main__':run()
