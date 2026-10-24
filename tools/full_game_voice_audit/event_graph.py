#!/usr/bin/env python3
"""Trace event -> switch/random/sequence -> exact resource, with evidence offsets.

An event editor ID and a resource header ID are distinct namespaces. Numeric
collisions are common and must NEVER be joined as if they were the same sound.
"""
import collections, json, re, struct
from inventory import PROJECT,GAME,OUT,csv_read,csv_write,json_write,u32


def run():
    nodes=json.loads((OUT/'bank-event-nodes.json').read_text());events=csv_read(OUT/'uax-events.csv')
    uax=collections.defaultdict(list)
    for r in events:uax[r['editor_id']].append(r)
    banks={n['bank'] for n in nodes};data={b:(GAME/b).read_bytes() for b in banks}
    resources={(n['bank'],n['map'],n['index']):n for n in nodes if n['kind']=='resource'}
    refs={(r['bank'],r['map'],int(r['resource_index'])):r for r in csv_read(OUT/'audio-resource-references.csv')}
    uc=(PROJECT/'vendor/EnhancedSC/UnrealScript/Echelon/Classes/EPawn.uc').read_text(errors='replace')
    enum=re.search(r'enum\s+EBarkType\s*\{(.*?)\}',uc,re.S).group(1)
    bark_names=re.findall(r'\bBARK_\w+',enum)
    graph=[];unresolved=[]

    def walk(bank,mapname,index,chain,bark='',seen=frozenset()):
        key=(bank,mapname,index)
        if key in seen:
            unresolved.append(dict(bank=bank,map=mapname,index=index,reason='GRAPH_CYCLE'));return []
        n=resources.get(key)
        if n is None:
            unresolved.append(dict(bank=bank,map=mapname,index=index,reason='RESOURCE_NOT_FOUND'));return []
        typ=n['type'];seen=seen|{key};chain=chain+[index]
        if typ==1:return [(n,chain,bark)]
        if typ in {13,15}:return [] # layer handled separately, silence has no voice payload
        raw=data[bank];h=bytes.fromhex(n['data_hex']);extra=n['extra_offset']
        if typ==10:count=u32(h,28);stride=12;kind='random'
        elif typ==8:count=u32(h,28);stride=8;kind='switch'
        elif typ==12:count=u32(h,44);stride=52;kind='sequence'
        elif typ==4:count=u32(h,44);stride=4;kind='chain'
        elif typ==14:count=1;stride=4;kind='parameterized_child'
        else:
            unresolved.append(dict(bank=bank,map=mapname,index=index,type=typ,reason='CONTAINER_TYPE_UNPARSED'));return []
        if extra+count*stride>n['extra_section_start']+n['extra_section_size']:
            unresolved.append(dict(bank=bank,map=mapname,index=index,type=typ,reason='EXTRA_TABLE_OUT_OF_BOUNDS'));return []
        leaves=[]
        for j in range(count):
            off=extra+j*stride;ptr=u32(raw,off);ri=ptr&0x3fffffff
            label=bark
            if kind=='switch':
                val=u32(raw,off+4);label=f'{val}:'+ (bark_names[val] if val<len(bark_names) else 'UNKNOWN_SWITCH_VALUE')
            leaves+=walk(bank,mapname,ri,chain,label,seen)
        return leaves

    for e in nodes:
        if e['kind']!='event' or e['type']!=1:continue
        h=bytes.fromhex(e['data_hex']);ptr=u32(h,8);ri=ptr&0x3fffffff
        # Fixed global resources use bit 31 and live in the 'fix' submap.
        if ptr&0x80000000 and e['map']!='fix':
            unresolved.append(dict(bank=e['bank'],map=e['map'],index=e['index'],reason='CROSS_BANK_EVENT_REFERENCE'));continue
        for n,chain,bark in walk(e['bank'],e['map'],ri,[]):
            r=refs.get((e['bank'],e['map'],n['index']))
            if r is None:continue
            names=uax[e['editor_id']]
            if not any('Barks' in v['event_name'] for v in names):bark=bark.split(':')[0] if bark else ''
            graph.append(dict(bank=e['bank'],map=e['map'],event_editor_id=e['editor_id'],event_table_offset=e['offset'],
                event_name=';'.join(sorted(x['package']+'.'+x['event_name'] for x in names)),
                resource_index=n['index'],resource_header_id=n['editor_id'],resource_name=r['resource_name'],
                source_path=r['source_path'],stream_offset=r['stream_offset'],encoded_key=r.get('encoded_key',''),
                switch_value=bark,resource_chain='>'.join(map(str,chain))))
    used={v for r in graph for v in r['event_name'].split(';') if v}
    installed_events=collections.defaultdict(list)
    for n in nodes:
        if n['kind']=='event':installed_events[n['editor_id']].append(n)
    coverage=[]
    for e in events:
        n=installed_events[e['editor_id']]
        if e['package']+'.'+e['event_name'] in used:status='RESOLVED_LEAF_AUDIO'
        elif any(x['type']==1 for x in n):status='PLAY_TARGET_WITHOUT_LEAF_AUDIO'
        elif n:status='NON_PLAY_EVENT_PRESENT'
        else:status='EVENT_NOT_IN_INSTALLED_BANKS'
        coverage.append(dict(**e,coverage_status=status,installed_event_references=len(n),
                             bank_event_types=';'.join(map(str,sorted({x['type'] for x in n})))))
    csv_write(OUT/'uax-reference-coverage.csv',coverage)
    csv_write(OUT/'event-resource-links.csv',graph)
    csv_write(OUT/'unresolved-event-links.csv',unresolved)
    print('Proven event/leaf paths',len(graph),'unresolved graph paths',len(unresolved))
if __name__=='__main__':run()
