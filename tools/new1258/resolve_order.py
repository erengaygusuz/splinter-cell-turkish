#!/usr/bin/env python3
"""Keep handoff order immutable; record the source-evidenced Kola permutation."""
from common import *

def run():
    expected=read(QA/'expected.json');key='story_kola_all_29_jason_20261028'
    order=['STORY_KOLA_MAFIOSO_1','STORY_KOLA_MAFIOSO_2','STORY_KOLA_MAFIOSO','STORY_KOLA_NIKOLAI_SPETZ','STORY_KOLA_PHONE_SPETZ',
        'STORY_KOLA_SPETSNAZ_1','STORY_KOLA_SPETSNAZ_2','STORY_KOLA_SPETSNAZ_3','STORY_KOLA_TECHNICIAN_2','STORY_KOLA_TECHNICIAN']
    cache=QA/'source_asr_medium'/f'{key}.json';asr=read(cache)
    selected=[r for g in order for r in expected if r['source_key']==key and r['voice_group']==g]
    assert len(selected)==29
    # Whole text support confirms this local permutation, not a cross-source search.
    similarity=alignment.score(' '.join(r['expected_text'] for r in selected),asr['text'])
    assert similarity>90,similarity
    replacement=[]
    for i,r in enumerate(selected,1):replacement.append(dict(r,declared_sequence_in_source=r['sequence_in_source'],sequence_in_source=i,order_basis='SOURCE_TRANSCRIPT_CONFIRMED_KOLA_GROUP_ORDER'))
    result=[]
    for source in read(QA/'sources.json'):
        if source['source_key']==key:result.extend(replacement)
        else:result.extend(dict(r,declared_sequence_in_source=r['sequence_in_source'],order_basis='HANDOFF_AND_PRODUCTION_INDEX') for r in expected if r['source_key']==source['source_key'])
    assert len(result)==len({r['new_id'] for r in result})==1258
    save(QA/'resolved_expected.json',result,True);table(QA/'resolved_physical_line_mapping.csv',result)
    save(QA/'source_order_resolution.json',dict(source_key=key,physical_source_sha256=selected[0]['physical_source_sha256'],
        transcript=rel(cache),transcript_sha256=sha(cache),observed_voice_group_order=order,whole_text_similarity=similarity,
        changed_positions=sum(r['sequence_in_source']!=r['declared_sequence_in_source'] for r in replacement),
        reason='Numbered mafioso TXT files precede unsuffixed mafioso; technician_2 precedes technician in recorded audio',
        original_mapping_preserved=True),True)
    print('Kola source order corrected; similarity',similarity)

if __name__=='__main__':run()
