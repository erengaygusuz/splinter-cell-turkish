#!/usr/bin/env python3
"""Join explicit UnrealScript Sound/Localize pairs, never fuzzy event names.

Commented restored/cut-level calls are retained as historical text evidence,
not evidence that a script executes in this installation.
"""
import collections,re
from inventory import PROJECT,OUT,csv_read,csv_write

CALL=re.compile(r'''Speech\(Localize\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\),\s*Sound'([^']+)' ''',re.X)

def run():
    lookup=collections.defaultdict(list)
    for r in csv_read(PROJECT/'manifests/enhanced-localization-audit/english-localization-strings.csv'):
        if r['key'].startswith('Speech') and r['english'].strip().lower() not in {'','(null)','null'}:
            lookup[(r['file'].lower(),r['section'].lower(),r['key'].lower())].append(r)
    rows=[]
    root=PROJECT/'vendor/EnhancedSC/UnrealScript/EchelonPattern/Classes'
    for p in sorted(root.glob('*.uc')):
        for n,line in enumerate(p.read_text(encoding='utf-8-sig',errors='replace').splitlines(),1):
            for m in CALL.finditer(line):
                section,key,file,event=m.groups();file=re.split(r'[/\\]+',file)[-1]+'.int'
                for loc in lookup[(file.lower(),section.lower(),key.lower())]:
                    text=loc['english'];speaker=''
                    prefix=re.match(r'^([A-Z][A-Z0-9 _.-]{1,35})\s+-\s+(.*)$',text)
                    if prefix:speaker,text=prefix.groups()
                    rows.append(dict(event_name=event,english_reference=text,speaker_reference=speaker,
                        script_path=str(p.relative_to(PROJECT)),script_line=n,script_commented=int(line.lstrip().startswith('//')),
                        localization_layer=loc['layer'],localization_file=loc['file'],section=section,key=key,
                        localization_path=loc['path'],localization_line=loc['line']))
    csv_write(OUT/'event-source-text.csv',rows)
    print(f'{len(rows)} explicit script/localization links, {len({r["event_name"] for r in rows})} events')

if __name__=='__main__':run()
