#!/usr/bin/env python3
"""Separate cut QA, model disagreement, approval and runtime test status."""
from common import *
from collections import Counter

ONES=['sıfır','bir','iki','üç','dört','beş','altı','yedi','sekiz','dokuz']
TENS=['','on','yirmi','otuz','kırk','elli','altmış','yetmiş','seksen','doksan']
def number(m):
    n=int(m[0])
    if n<10:return ONES[n]
    if n<100:return TENS[n//10]+(' '+ONES[n%10] if n%10 else '')
    return m[0]
def norm(text):return alignment.norm(re.sub(r'\d+',number,text.replace('-',' ')))
def score(a,b):
    from rapidfuzz.fuzz import ratio
    return round(ratio(norm(a),norm(b)),2)

def run():
    cuts={r['new_id']:r for r in read(QA/'cuts.json')};expected=read(QA/'resolved_expected.json');result=[]
    for r in expected:
        c=cuts.get(r['new_id']);row=dict(r,qa_status='NOT_CUT',runtime_status='NOT_INTEGRATED',game_test_status='NOT_PERFORMED',manual_listening='NOT_PERFORMED')
        if c:
            row.update(c);row['alignment_flags']=';'.join(c['alignment_flags'])
            cache=QA/'clips_asr_large-v3'/(r['new_id']+'_'+c['version']+'.json')
            if not cache.exists():row['qa_status']='CLIP_ASR_PENDING'
            else:
                d=read(cache);assert d['sha256']==c['output_wav_sha256']
                match=score(r['expected_text'],d['text']);flags=[]
                second=QA/'clips_asr_medium'/(r['new_id']+'_'+c['version']+'.json')
                second_score=0
                if second.exists():
                    other=read(second);assert other['sha256']==c['output_wav_sha256'];second_score=score(r['expected_text'],other['text'])
                    row.update(second_clip_asr=other['text'],second_clip_match=second_score,second_asr_evidence=rel(second))
                if max(match,second_score)<95:flags.append('CLIP_TEXT_MISMATCH')
                if c['source_score']<90:flags.append('SOURCE_TEXT_MISMATCH')
                # A 15 ms guard within a measured low-energy gap is sufficient;
                # absolute source edges cannot contain another source utterance.
                if (c['start_method']!='SOURCE_START' and c['leading_quiet_ms']<15) or (c['end_method']!='SOURCE_END' and c['trailing_quiet_ms']<15):flags.append('SHORT_EDGE_MARGIN')
                if 'NO_QUIET_BOUNDARY' in c['alignment_flags']:flags.append('NO_QUIET_BOUNDARY')
                if 'UNASSIGNED_WORDS' in c['alignment_flags']:flags.append('UNASSIGNED_WORDS')
                row.update(clip_asr=d['text'],clip_match=match,qa_flags=';'.join(flags),qa_status='REVIEW_REQUIRED' if flags else 'AUTO_TEXT_AND_BOUNDARY_PASS',
                    approval_status='NOT_MANUALLY_APPROVED',asr_evidence=rel(cache),asr_evidence_sha256=sha(cache))
                if match<95<=second_score:row['text_resolution']='SECOND_ISOLATED_ASR_SUPPORTS_EXPECTED_TEXT; FIRST_HYPOTHESIS_RETAINED'
        result.append(row)
    table(QA/'qa_1258.csv',result)
    table(QA/'review_required.csv',[r for r in result if r['qa_status']=='REVIEW_REQUIRED'])
    summary=dict(total_ids=len(result),cut_ids=len(cuts),qa_counts=dict(Counter(r['qa_status'] for r in result)),
        integrated_ids=0,in_game_tested_ids=0,manual_listening='NOT_PERFORMED',approved_ids=0,
        source_order_correction='Kola recorded group permutation applied; handoff order retained separately')
    save(QA/'qa_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
