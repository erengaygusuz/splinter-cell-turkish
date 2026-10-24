#!/usr/bin/env python3
"""Publish deduplicated decisions without equating ASR confidence with approval."""
import collections,difflib,json,re
from pathlib import Path
from inventory import PROJECT,OUT,csv_read,csv_write,json_write
from catalog import FIELDS

VOCALS={'ah','aah','aaah','argh','agh','ugh','urgh','ow','ooh','oh','uh','uhh','huh','hmm','hm','mm','mmm','ha','hah','haha','eh','aw','wah','oof','cough','coughing','sigh','sighing','sniff','sniffing','sneeze','sneezing','snoring','grunting','groaning','screaming','whistling','laughing','gasp','gasping','aargh','aagh','grr','hum','humming','hoo','ho','bam','bum','ahh','ughh','gah','heh','uhuh','bleh','h','n','u','a'}
PURE_VOCAL={'BARK_HitByBullet','BARK_HitElectric','BARK_KnockedOut','BARK_Cough','BARK_InFire','BARK_Dying','BARK_ChokeGrab'}
SOURCE_TEXT=collections.defaultdict(list)


def tokens(text):
    return re.findall(r"[0-9]+|[a-z]+(?:'[a-z]+)?",text.lower().replace('’',"'"))


def normalize(text):return ' '.join(tokens(text))


def vocal_token(t):
    return t in VOCALS or (len(t)>1 and set(t)<=set('aouhgrwmez') and len(set(t))<=3 and any(t.count(c)>2 for c in t))


def info(obj):
    if not obj:return dict(text='',norm='',words=[],lexical=[],reliable=False)
    text=obj.get('text','');ts=tokens(text);lex=[x for x in ts if not vocal_token(x)]
    repetitive=len(ts)>10 and len(set(ts))/len(ts)<0.2
    reliable=bool(lex) and obj.get('avg_logprob') is not None and obj['avg_logprob']>=-.85 and (obj.get('no_speech_prob') or 0)<.7 and not repetitive
    return dict(text=text,norm=' '.join(ts),words=ts,lexical=lex,reliable=reliable)


def read_asr(folder,uid):
    p=OUT/folder/f'{uid}.json'
    return json.loads(p.read_text()) if p.exists() else None


def decide(r):
    r=dict(r);uid=r['new_id'];a=read_asr('asr-large-v3',uid);b=read_asr('asr-medium-en-no-vad',uid);c=read_asr('asr-large-v3-no-vad',uid)
    r['english_asr']=a['text'] if a else '';r['verification_asr']=b['text'] if b else ''
    r['focused_asr']=c['text'] if c else ''
    r['english_final']='';r['text_qa']='NOT_APPLICABLE';r['qa_reason']='';r['manual_listening']='NOT_PERFORMED'
    if r['classification'] in {'ALREADY_DUBBED','NON_SPEECH'}:return r
    if r['classification']=='EXISTING_CORPUS':
        r['classification']='VOCALIZATION';r['qa_reason']='Seven previously identified corpus vocalizations; not new dialogue';return r
    if not a or not b:
        r['classification']='ASR_PENDING';r['qa_reason']='Two independent passes not yet complete';return r
    assert a['pcm_sha256']==r['pcm_sha256']==b['pcm_sha256']
    x,y=info(a),info(b);similar=difflib.SequenceMatcher(None,x['norm'],y['norm']).ratio() if x['norm'] or y['norm'] else 1
    if c:assert c['pcm_sha256']==r['pcm_sha256']
    z=info(c)
    r['asr_agreement']=round(similar,4)
    r['large_avg_logprob']=a.get('avg_logprob');r['medium_avg_logprob']=b.get('avg_logprob')
    role=r.get('switch_values','');event=r['event_name'];pkg=r['speaker_or_archetype']
    vocal=any(k in role for k in PURE_VOCAL) or pkg in {'FisherVoice','GenericLife'} or 'Snor' in event
    if re.fullmatch(r'(?:CLICKS|CLICKE|NOISE)_\d+\.wav',r['resource_name']) or 'HeartBeat' in event:
        r['classification']='NON_SPEECH';r['confidence']='event_and_resource_identity';r['qa_reason']='Radio click/static component or heartbeat, not a voiced line';return r
    if pkg=='SoundEvent' and 'Snor' not in event:
        r['classification']='NON_SPEECH';r['confidence']='event_identity';r['qa_reason']='Paper/wood/bed/zipper mechanical event';return r
    if pkg=='radio':
        language=read_asr('radio-language',uid)
        if language and language['language']!='en' and language['language_probability']>=.8 and len(language['text'].split())>5:
            r['classification']='NON_ENGLISH_SPEECH';r['source_language']=language['language'];r['native_asr']=language['text'];r['confidence']='language_detection';r['qa_reason']='Background radio is not English; forced-English ASR is not a valid source transcript';return r
        r['classification']='REVIEW_REQUIRED';r['qa_reason']='Background radio/music: speech and language need listening';return r
    if pkg=='GenericLife':
        r['classification']='VOCALIZATION';r['confidence']='event_identity';r['qa_reason']='Whistle/contact-pain event; ASR lyrics/repetition rejected';return r
    if c and vocal and not z['lexical'] and (not x['lexical'] or not y['lexical']):
        r['classification']='VOCALIZATION';r['confidence']='event_and_focused_asr';r['qa_reason']='Nonverbal event and focused no-VAD pass; conflicting lexical hypothesis retained, not accepted';return r
    if vocal and (not x['lexical'] and not y['lexical']):
        r['classification']='VOCALIZATION';r['confidence']='event_and_two_asr';r['qa_reason']='Nonverbal human event, no lexical words in either model';return r
    if not x['lexical'] and not y['lexical']:
        if x['words'] or y['words']:
            r['classification']='VOCALIZATION';r['confidence']='two_asr_interjection';r['qa_reason']='Both models find only nonverbal interjections'
        else:
            r['classification']='REVIEW_REQUIRED';r['qa_reason']='Both models empty on a possible voice event'
        return r
    if vocal:
        # A decoder can hallucinate "you" or "thank you" over a grunt.
        if not (x['reliable'] and y['reliable'] and similar>=.8 and min(len(x['lexical']),len(y['lexical']))>=3):
            r['classification']='REVIEW_REQUIRED';r['qa_reason']='Lexical ASR conflicts with pain/breath/death event';return r
    strong=(x['reliable'] and y['reliable']) or ((x['reliable'] or y['reliable']) and bool(role or event))
    if (not x['lexical'] or not y['lexical']) and max(len(x['lexical']),len(y['lexical']))<2:
        # A single word opposed by silence/a grunt is not confirmed dialogue.
        strong=bool(c and z['reliable'] and z['norm']==y['norm'] and y['reliable'])
    if strong:
        r['classification']='NEW_VOICE_REQUIRED';r['confidence']='two_asr_and_event' if x['reliable'] and y['reliable'] else 'one_asr_and_event'
        if x['norm']==y['norm']:
            r['english_final']=x['text'];r['text_qa']='ASR_AGREEMENT'
        elif c and z['norm']==y['norm'] and z['reliable'] and y['reliable']:
            r['english_final']=y['text'];r['text_qa']='FOCUSED_ASR_AGREEMENT'
        else:
            r['english_final']='';r['text_qa']='TEXT_REVIEW_REQUIRED'
        r['qa_reason']='Lexical speech outside the original corpus; transcript agreement tracked separately'
    else:
        r['classification']='REVIEW_REQUIRED';r['qa_reason']='Speech/text confidence too low for an automatic decision'
    if uid=='v_e066ee2c634b8938' and r['classification']=='NEW_VOICE_REQUIRED' and r['text_qa']=='ASR_AGREEMENT':
        r['finding_tag']='POLICE_STATION_CONFIRMED_MISSING_BARK'
        r['notes']+=' Asset-level confirmation: GeorgianCitizen, Tbilisi, SeeSomethingMove. Exact player encounter not verified; phrase is Is somebody over there?'
    return r


def attach_source_text(r):
    refs=[ref for event in r['event_name'].split(';') for ref in SOURCE_TEXT[event.lower()]]
    if not refs:return r
    r['source_text_evidence']=json.dumps(refs,ensure_ascii=False,separators=(',',':'))
    r['source_text_scope']='Historical script/localization pair; not proof of installed script execution'
    compact=lambda s:re.sub('[^a-z0-9]','',s.lower())
    mapped=[ref for ref in refs if any(compact(ref['localization_file']).startswith('p'+compact(m)) for m in r['map'].split(';') if m)]
    selected=mapped or refs
    enhanced=[ref for ref in selected if ref['localization_layer']=='enhanced']
    selected=enhanced or selected
    active=[ref for ref in selected if ref['script_commented']=='0']
    selected=active or selected
    r['source_text_selection']='Matching map where available, enhanced text, uncommented call; all alternatives retained'
    texts={normalize(ref['english_reference']):ref['english_reference'] for ref in selected}
    if len(texts)!=1:
        r['source_text_qa']='CONFLICTING_REFERENCES';return r
    norm,text=next(iter(texts.items()));r['english_reference']=text
    r['reference_speaker']=';'.join(sorted({ref['speaker_reference'] for ref in selected if ref['speaker_reference']}))
    agreement=max(difflib.SequenceMatcher(None,norm,normalize(r[k])).ratio() for k in ('english_asr','verification_asr','focused_asr'))
    r['source_text_asr_similarity']=round(agreement,4)
    if r['classification']=='NEW_VOICE_REQUIRED' and agreement>=.8:
        r['english_final']=text;r['text_qa']='SOURCE_TEXT_ASR_SUPPORTED';r['source_text_qa']='EXPLICIT_EVENT_PAIR_AND_AUDIO_TEXT_SUPPORT'
    else:r['source_text_qa']='AUDIO_TEXT_REVIEW_REQUIRED'
    return r


def attach_language_review(r):
    check=read_asr('phrase-language',r['new_id'])
    if not check:return r
    assert check['pcm_sha256']==r['pcm_sha256']
    r['detected_language']=check['language'];r['language_probability']=check['language_probability'];r['native_asr']=check['text']
    r['language_qa']='REVIEW_REQUIRED_SHORT_OR_FOREIGN_PHRASE'
    r['classification']='REVIEW_REQUIRED';r['english_final']='';r['text_qa']='TEXT_AND_LANGUAGE_REVIEW_REQUIRED'
    r['qa_reason']='Flagged foreign/short phrase: automatic language detection is not conclusive; excluded from English dialogue count'
    return r


def run():
    SOURCE_TEXT.clear()
    if (OUT/'event-source-text.csv').exists():
        for ref in csv_read(OUT/'event-source-text.csv'):SOURCE_TEXT[ref['event_name'].lower()].append(ref)
    base=csv_read(OUT/'all-unique-audio-resources.csv');rows=[attach_language_review(attach_source_text(decide(r))) for r in base]
    groups=collections.defaultdict(list)
    for r in rows:groups[r['duplicate_group']].append(r)
    unique=[]
    rank={'ALREADY_DUBBED':0,'NEW_VOICE_REQUIRED':1,'NON_ENGLISH_SPEECH':2,'VOCALIZATION':3,'NON_SPEECH':4,'REVIEW_REQUIRED':5,'ASR_PENDING':6}
    for key,rs in groups.items():
        # A flagged language decision applies to the whole measured signal group.
        flagged=next((x for x in rs if x.get('language_qa')),None)
        if flagged:
            for x in rs:
                for col in ('classification','english_final','text_qa','qa_reason','language_qa','detected_language','language_probability','native_asr'):x[col]=flagged[col]
        rs.sort(key=lambda r:(rank[r['classification']],r['text_qa'] not in {'ASR_AGREEMENT','FOCUSED_ASR_AGREEMENT','SOURCE_TEXT_ASR_SUPPORTED'},not r['resource_name'].endswith('.wav'),r['new_id']))
        r=dict(rs[0]);r['alias_ids']=';'.join(x['new_id'] for x in rs);r['alias_wav_paths']=';'.join(x['wav_path'] for x in rs)
        for col in ['mission','map','event_name','editor_id','speaker_or_archetype','resource_header_id','resource_name']:
            r[col]=';'.join(sorted({v for x in rs for v in x.get(col,'').split(';') if v}))
        r['reference_count']=sum(int(x['reference_count']) for x in rs);r['event_usage_count']=sum(int(x['event_usage_count']) for x in rs)
        r['decoded_variant_count']=len(rs);unique.append(r)
    field_order=FIELDS+list(dict.fromkeys(k for r in unique+rows for k in r if k not in FIELDS))
    candidates=[r for r in rows if r['human_candidate']=='1' or r['corpus_ids']]
    fresh=[r for r in unique if r['classification']=='NEW_VOICE_REQUIRED']
    vocals=[r for r in unique if r['classification']=='VOCALIZATION']
    pending=[r for r in unique if r['classification'] in {'REVIEW_REQUIRED','ASR_PENDING'}]
    for filename,data in [('full-game-voice-candidates.csv',candidates),('full-game-new-voice-lines.csv',fresh),('full-game-vocalizations.csv',vocals),
                           ('full-game-review-required.csv',pending),('full-game-other-language-speech.csv',[r for r in unique if r['classification']=='NON_ENGLISH_SPEECH']),('all-audio-decisions.csv',unique),('full-game-transcript-review.csv',[r for r in fresh if r['text_qa']=='TEXT_REVIEW_REQUIRED'])]:
        csv_write(OUT/filename,data,field_order)
    classifications=dict(collections.Counter(r['classification'] for r in unique))
    summary=dict(installed_turkish_ids=1086,original_corpus_ids=1093,files_in_sounds=412,english_common_banks=8,
                 leaf_resource_references=13738,layer_resource_references=111,vgmstream_logical_subsongs=14284,
                 decoded_leaf_variants=len(rows),unique_signal_groups=len(unique),human_candidate_variants=len(candidates),
                 new_human_variants=1692,new_human_unique_groups=len({r['duplicate_group'] for r in candidates if not r['corpus_ids']}),
                 classifications=classifications,new_dialogue_unique=len(fresh),new_dialogue_text_review=sum(r['text_qa']=='TEXT_REVIEW_REQUIRED' for r in fresh),
                 unresolved_voice_classification=len(pending),new_nonverbal_unique=sum(not r['corpus_ids'] for r in vocals),
                 new_dialogue_text_qa=dict(collections.Counter(r['text_qa'] for r in fresh)),
                 language_review_unique=sum(bool(r.get('language_qa')) for r in unique),
                 police_station_example=dict(new_id='v_e066ee2c634b8938',english='Is somebody over there?',speaker='GeorgianCitizen',
                     event_editor_id='00610000',resource_header_id='00610036',scope='asset identity confirmed; exact player encounter unverified'),
                 exact_remaining_english_count='NOT_FINAL_WHILE_REVIEW_REQUIRED_OR_ASR_PENDING',
                 duplicate_variants_removed=len(rows)-len(unique),unresolved_bank_references=0,unresolved_event_links=0,
                 original_livedata_pcm_matches=610,modified_original_ls0_slots=483,additional_original_waveform_matches=4,
                 other_installed_language_banks='inventoried, not English ASR targets',manual_audio_listening='not performed',runtime_installation='unchanged',uax_coverage=dict(collections.Counter(r['coverage_status'] for r in csv_read(OUT/'uax-reference-coverage.csv'))))
    json_write(OUT/'summary.json',summary)
    text=f'''Splinter Cell — yeni oyun içi ses kaynakları denetimi\n\nV27 kurulumu: 1.086 Türkçe ID. Orijinal LS0 corpus: 1.093 ID.\nTarama: 412 dosya; İngilizce/ortak 8 banka; 13.738 yaprak ses referansı.\nÇıkarım: {len(rows)} WAV varyantı, sinyal karşılaştırmasıyla {len(unique)} grup.\n\nYeni İngilizce konuşma (tekilleştirilmiş, otomatik kanıt): {len(fresh)}\nBunlardan metni ayrıca incelenecek: {summary['new_dialogue_text_review']}\nYeni sözsüz insan sesi: {summary['new_nonverbal_unique']}\nSınıflandırması/dili belirsiz veya ASR bekleyen: {len(pending)}\n\nKESİN TOPLAM HENÜZ VERİLEMEZ: belirsiz kayıtlar yeni konuşma sayısına eklenmedi.\nSınıflar: {json.dumps(classifications,ensure_ascii=False)}\n\nASR_AGREEMENT iki modelin normalize metin uyumudur; manuel dinleme/onay değildir.\nTEXT_REVIEW_REQUIRED kayıtlarında english_final boş bırakıldı; iki ham transkript korunur.\nAynı metin veya süre tek başına duplicate kabul edilmedi.\nOlay editor_id ile resource_header_id farklı ad alanlarıdır; runtime denemesi yapılmadı.\nBanka/DLL/WAV kurulumu değiştirilmedi. Diğer diller envanterlendi, İngilizce ASR kapsamına alınmadı.\nBüyük WAV ve model/decoder dosyaları Git dışındadır.\n'''
    (OUT/'full-game-new-voice-summary.txt').write_text(text,encoding='utf-8')
    with (OUT/'full-game-new-voice-summary.txt').open('a',encoding='utf-8') as f:
        f.write(f'''
Kapsam ve sayım açıklamaları
--------------------------
Ana oyun, Kola Cell, Vselka Infiltration ve Vselka dahil.
FMV kapsam dışı. Sayılan birim cümle sayısı değil, benzersiz kaynak ses kaydıdır.
İnsan sesi adayları: {len(candidates)} çözülmüş varyant; mevcut corpus dışında 1.692 varyant / 1.625 sinyal grubu.
Mevcut corpus: 610 birebir PCM eşleşmesi, 483 değişmiş canlı LS0 konumu, 4 ek dalga biçimi eşleşmesi.
ALREADY_DUBBED içindeki 1.090 kaynak varyantı, 1.086 kurulu Türkçe ID'ye karşılık gelir.
Eski 7 sözsüz corpus kaydı yeni diyalog sayısına eklenmedi.
125 yinelenen çözümleme varyantı sinyal karşılaştırmasıyla birleştirildi.
Metin durumları: {json.dumps(summary['new_dialogue_text_qa'],ensure_ascii=False)}
SOURCE_TEXT_ASR_SUPPORTED: açık Sound/Localize betik eşleşmesi ve ASR desteği;
betiğin bu kurulumda çalıştığına dair runtime kanıtı değildir.
FOCUSED_ASR_AGREEMENT: VAD kapalı large-v3 ile bağımsız medium.en uyumu.
Kısa/yabancı dil şüphesiyle ayrı inceleme: {summary['language_review_unique']} kayıt.
Bir Rusça arka plan radyosu NON_ENGLISH_SPEECH olarak ayrı listelendi.
Zorlanmış İngilizce transkriptler bu radyonun İngilizce kaynak metni sayılmadı.

Police Station / Tbilisi bulgusu
-------------------------------
Etiket: POLICE_STATION_CONFIRMED_MISSING_BARK
new_id: v_e066ee2c634b8938
Metin: Is somebody over there?
Karakter: GeorgianCitizen; olay: Play_Switch_GCIBarks; BARK_SeeSomethingMove.
Map: 1_1_0Tbilisi ve 1_1_2Tbilisi.
Banka: Sounds/ENGLISH/MAPS.LM0; stream 279; offset 1927888.
Event editor_id: 00610000; resource_header_id: 00610036.
23467 örnek / 16000 Hz; 1.466687 saniye.
WAV: build/full-game-voice-audit/original-wav/v_e066ee2c634b8938_00610036_1927888.wav
Mevcut corpus dışında olduğu ve kaynak kimliği doğrulandı.
Kullanıcının duyduğu sahneyle birebir aynı olay olduğu henüz oyun içinde doğrulanmadı.

Eksiksizlik sınırları ve kalan iş
-------------------------------
13.738 yaprak kaynak referansının tamamı çözüldü; 3.780 WAV çıkarıldı.
111 katmanlı ambience referansı ayrı indekslendi; bunlar çözülüp dinlenmedi.
NON_SPEECH sınıfları banka/olay kimliğine dayanır, tüm efektler ASR'den geçirilmedi.
62 harici İngilizce/ortak LS0/SS0 dosyasında açıklanmayan büyük boşluk veya sahipsiz ADPCM başlığı bulunmadı.
UAX kapsamı: {json.dumps(summary['uax_coverage'],ensure_ascii=False)}
Bankalarda bulunmayan 872 UAX adı yeni replik veya kayıp ses dosyası sayılmadı.
Yaprak sesi olmayan 30 olay; boş/katmanlı/sessiz hedeflerdir, ayrı listede tutulur.
Manuel dinleme ve oyun içi tetikleme testi yapılmadı.
Bu nedenle {len(fresh)} otomatik olarak desteklenen yeni konuşma kaydı, kesin kalan İngilizce replik toplamı değildir.
Önce full-game-review-required.csv içindeki {len(pending)} sesin sınıfı/dili kontrol edilmeli;
sonra full-game-transcript-review.csv içindeki {summary['new_dialogue_text_review']} konuşmanın metni netleştirilmelidir.
Yanlış ASR metniyle çeviri veya ElevenLabs üretimi başlatılmadı.
Runtime entegrasyonu için olay ID'si yanında gerçek banka/kaynak kimliği kullanılmalı;
static event eşleşmesi tek başına yeni DLL kurulumu için yeterli değildir.
Son kurulum hash kontrolü: protected-installation-verification.json.
ASR cache hashleri ve model kanıtları: asr-evidence.csv; kelime zamanları yerel JSON cache dosyalarında.
''')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
if __name__=='__main__':run()
