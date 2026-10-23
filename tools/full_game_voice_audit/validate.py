#!/usr/bin/env python3
"""Cross-check parsed identities against live vgmstream and original manifests."""
import collections,json,random,subprocess
from inventory import PROJECT,GAME,OUT,csv_read,json_write,sha
from extract import pcm_identity

def run():
    refs=csv_read(OUT/'audio-resource-references.csv');decoded=csv_read(OUT/'decoded-unique-resources.csv')
    assert len(refs)==13738 and all(r['status']=='OK' for r in refs)
    assert len(decoded)==3780 and all(r['status']=='OK' for r in decoded)
    # The original catalog was built independently. All native UAX records
    # must agree, including their exact serialization offsets/editor IDs.
    old=csv_read(PROJECT/'manifests/uax-editor-id-catalog.csv');new=csv_read(OUT/'uax-events.csv')
    index={(r['package'],r['event_name']):r for r in new}
    for r in old:
        x=index[(r['package'],r['sound_object'])]
        assert int(x['editor_id'],16)==int(r['editor_id'])
        assert x['serial_offset']==r['serial_offset'] and x['serial_size']==r['serial_size']
    checked=[]
    for bank in sorted({r['bank'] for r in refs}):
        choices=[r for r in refs if r['bank']==bank and not r.get('source_resolution')]
        for r in random.Random(20261023).sample(choices,min(3,len(choices))):
            cmd=[str(OUT/'vgmstream-cli'),'-m','-I','-s',r['stream_index'],str(GAME/bank)]
            meta=json.loads(subprocess.check_output(cmd,text=True))
            assert meta['sampleRate']==int(r['sample_rate']) and meta['channels']==int(r['channels'])
            assert meta['numberOfSamples']==int(r['sample_count'])
            # A null/silence fallback is never acceptable for a decoded source.
            assert '(missing)' not in meta['streamInfo']['name']
            checked.append(dict(bank=bank,stream_index=r['stream_index'],resource_header_id=r['editor_id']))
    links=csv_read(OUT/'event-resource-links.csv')
    # Regression: 005A0003 event = CombatMove, same numeric resource ID =
    # GCPAWA_1 (BeAware). A naive ID equality join silently assigns wrong audio.
    rows=[r for r in links if r['event_editor_id']=='005A0003']
    assert rows and all('CMO_' in r['resource_name'] for r in rows)
    assert not csv_read(OUT/'unresolved-event-links.csv')
    result=dict(native_uax_objects_verified=len(old),decoded_leaf_resources=len(decoded),
                exact_resource_references=len(refs),independent_decoder_probes=checked,
                event_namespace_collision_regression='PASS',all_event_links_resolved=True)
    json_write(OUT/'validation.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':run()
