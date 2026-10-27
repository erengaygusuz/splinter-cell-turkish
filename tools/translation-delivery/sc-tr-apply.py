#!/usr/bin/env python3
"""Apply fully reviewed Splinter Cell gameplay translation batches without touching audio files."""
import argparse
import csv
import re
import subprocess
import tempfile
import os
from pathlib import Path
from collections import Counter

ROOT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
AUDIT = ROOT / "manifests/full-game-voice-audit"
WORK = AUDIT / "translation-work"
MAIN = AUDIT / "final-turkish-production-voices.csv"
SUMMARY = AUDIT / "final-turkish-production-summary.md"
WORK_SUMMARY = WORK / "translation-work-summary.md"
PIN = "22308b9cf7d1738a92c7ca97e645dd0017542200"
BRANCH = "fisher-audio-qa"
PLAN = [
    ("010-014", range(10, 15), 250, (482,776), (732,526)),
    ("015-019", range(15, 20), 250, (732,526), (982,276)),
    ("020-025", range(20, 26), 276, (982,276), (1258,0)),
]
TR_ASCII = str.maketrans({"ç":"c","Ç":"C","ğ":"g","Ğ":"G","ı":"i","İ":"I","ö":"o","Ö":"O","ş":"s","Ş":"S","ü":"u","Ü":"U"})

def norm(text):
    return re.sub(r"\\s+", " ", text.strip()).lower().rstrip(" .!?")

def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rd = csv.DictReader(f)
        return list(rd.fieldnames or []),list(rd)

def dump_csv(fields,rows):
    import io
    buf=io.StringIO(newline="")
    writer=csv.DictWriter(buf,fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()

def write_atomic(path,contents):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".sc-tr-",dir=str(path.parent),text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="") as f:
            f.write(contents)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def counts(rows):
    c=Counter(r["translation_status"] for r in rows)
    return c["FINAL_TR"],c["NEEDS_TR_TRANSLATION"]

def group_key(row):
    return "OTHER_DIALOGUE" if row.get("translation_category") == "OTHER_DIALOGUE" else row.get("translation_subgroup","")

def load_dictionary(path):
    assert path.is_file(),path
    mapping={}
    group=None
    with path.open(encoding="utf-8-sig") as f:
        for line_no,line in enumerate(f,1):
            line=line.rstrip("\n\r")
            if not line.strip() or line.lstrip().startswith("#"): continue
            if line.startswith("[") and line.endswith("]"):
                group=line[1:-1].strip()
                assert group, (path,line_no)
                mapping.setdefault(group,{})
                continue
            if " || " not in line or not group:
                raise ValueError(f"{path}:{line_no}: geçersiz kayıt")
            src,tr=line.split(" || ",1)
            src,tr=src.strip(),tr.strip()
            assert src and tr,(path,line_no)
            key=norm(src)
            prior=mapping[group].get(key)
            assert prior is None or prior == tr, (path,line_no,src,prior,tr)
            mapping[group][key]=tr
    return mapping

def prepare(name,indices,expected_rows,main_by):
    path=Path(__file__).resolve().parent / f"sc-tr-{name}.txt"
    mapping=load_dictionary(path)
    selected=[]
    by_batch={}
    fields=None
    distribution=Counter()
    for number in indices:
        path=WORK / f"translation-batch-{number:03d}.csv"
        assert path.is_file(),path
        hdr,rows=read_csv(path)
        assert len(rows)==(26 if number==25 else 50),(number,len(rows))
        if fields is None:fields=hdr
        else: assert fields==hdr
        by_batch[number]=rows
        selected.extend(rows)
    assert len(selected)==expected_rows,(name,len(selected),expected_rows)
    assert len({r["new_id"] for r in selected})==expected_rows
    results={}
    missing=[]
    for row in selected:
        uid=row["new_id"]
        source=row["source_text_final"].strip()
        group=group_key(row)
        distribution[group]+=1
        tr=mapping.get(group,{}).get(norm(source))
        if tr is None:
            missing.append((uid,group,source))
            continue
        assert uid in main_by,uid
        current=main_by[uid]
        assert current["source_text_final"].strip()==source,(uid,"kaynak değişti")
        assert current["translation_status"] in ("NEEDS_TR_TRANSLATION","FINAL_TR"),(uid,current["translation_status"])
        results[uid]=tr
    if missing:
        for item in missing:print("EKSİK:",*item)
        raise AssertionError(f"{name}: {len(missing)} çeviri eksik; hiçbir dosya yazılmadı")
    # Source collision / coverage QA.
    assert len(results)==expected_rows
    return fields,by_batch,results,distribution

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true",help="Verify all three groups without writing files")
    args=ap.parse_args()
    assert ROOT.is_dir(),ROOT
    assert subprocess.check_output(["git","-C",str(ROOT),"branch","--show-current"],text=True).strip()==BRANCH
    assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==PIN
    for path in (MAIN,SUMMARY,WORK_SUMMARY):assert path.is_file(),path
    main_fields,all_rows=read_csv(MAIN)
    assert len(all_rows)==1258
    main_by={r["new_id"]:r for r in all_rows}
    assert len(main_by)==1258
    state=counts(all_rows)
    allowed={(482,776),(732,526),(982,276),(1258,0)}
    assert state in allowed,("Beklenmeyen manifest durumu",state)
    staged=[]
    for name,indices,size,before,after in PLAN:
        fields,batches,translated,dist=prepare(name,indices,size,main_by)
        staged.append((name,fields,batches,translated,before,after))
        print("PREFLIGHT PASS:",name,size,"satır",dict(dist))
    if args.preflight:
        print("PASS: 776/776 kaynak kapsanıyor; hiçbir dosya yazılmadı")
        return
    for name,fields,batches,translated,before,after in staged:
        cur=counts(all_rows)
        if cur==after:
            print("SKIP:",name,"zaten uygulanmış")
            continue
        assert cur==before,("Beklenmeyen adım sırası",name,cur,before)
        assert all(main_by[uid]["translation_status"]=="NEEDS_TR_TRANSLATION" for uid in translated)
        summary=SUMMARY.read_text(encoding="utf-8")
        old1,old2=f"- FINAL_TR: {before[0]}",f"- NEEDS_TR_TRANSLATION: {before[1]}"
        new1,new2=f"- FINAL_TR: {after[0]}",f"- NEEDS_TR_TRANSLATION: {after[1]}"
        assert summary.count(old1)==1 and summary.count(old2)==1,(name,"özet uyumsuz")
        summary=summary.replace(old1,new1,1).replace(old2,new2,1)
        work=WORK_SUMMARY.read_text(encoding="utf-8")
        work=work.split("\n## Progress\n",1)[0].rstrip()
        work+=(
            "\n\n## Progress\n"
            f"- Completed batches: 001-{name[-3:]}\n"
            f"- Batch translations completed: {after[0]-32}\n"
            f"- Current FINAL_TR: {after[0]}\n"
            f"- Current NEEDS_TR_TRANSLATION: {after[1]}\n"
        )
        macro=[]
        resolved={}
        for number,rows in batches.items():
            out=[]
            for old in rows:
                r=dict(old)
                tr=translated[r["new_id"]]
                r["turkish_final"]=tr
                r["turkish_game_text"]=tr.translate(TR_ASCII)
                r["translation_status"]="FINAL_TR"
                out.append(r);macro.append(r)
            resolved[number]=out
        # Validate every output before writing.
        assert len(macro)==len(translated)
        candidate=[dict(r) for r in all_rows]
        for row in candidate:
            uid=row["new_id"]
            if uid not in translated:continue
            tr=translated[uid]
            row["turkish_final"]=tr
            row["turkish_game_text"]=tr.translate(TR_ASCII)
            row["translation_status"]="FINAL_TR"
        assert counts(candidate)==after
        # Generated sidecars are written before the main manifest.
        for number,rows in resolved.items():
            write_atomic(WORK/f"translation-batch-{number:03d}-resolved.csv",dump_csv(fields,rows))
        write_atomic(WORK/f"translation-macro-{name}-resolved.csv",dump_csv(fields,macro))
        write_atomic(MAIN,dump_csv(main_fields,candidate))
        # Commit recovery state after main, and verify.
        write_atomic(SUMMARY,summary)
        write_atomic(WORK_SUMMARY,work)
        all_rows=candidate
        main_by={r["new_id"]:r for r in all_rows}
        assert counts(read_csv(MAIN)[1])==after
        print("PASS:",name,"translated",len(translated),"FINAL_TR",after[0],"pending",after[1])
    assert counts(all_rows)==(1258,0)
    for row in all_rows:
        assert row["turkish_final"].strip(),row["new_id"]
        assert row["turkish_game_text"]==row["turkish_final"].translate(TR_ASCII),row["new_id"]
    print("ALL PASS: 1258 FINAL_TR, 0 pending")

if __name__=="__main__":
    main()
