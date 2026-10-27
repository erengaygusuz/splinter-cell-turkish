#!/usr/bin/env python3
"""Generate ElevenLabs v3 copy-paste prompts from the already approved full-game Turkish voice manifest.

READ-ONLY on repository content. Does not generate audio, modify DLLs, rename WAVs, or touch V27.
"""
import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

REL_MANIFEST = "manifests/full-game-voice-audit/final-turkish-production-voices.csv"
REL_SCRIPT = "manifests/full-game-voice-audit/event-source-text.csv"
DEFAULT_ROOT = "/run/media/ereng/files/projects/splinter-cell-turkish"
SPEAKER_ALIASES = {
    "GRIMSTODDIR": "GRIMSDOTTIR",
    "GRIMSDOTTIR": "GRIMSDOTTIR",
    "EX-SPETSNAZ 1": "EX-SPETSNAZ-1",
    "EX-SPETSNAZ 2": "EX-SPETSNAZ-2",
}
EMOTION_BY_BARK = {
    "BARK_HeardFoot": "curious",
    "BARK_HeardGunShot": "nervous",
    "BARK_BeAware": "urgently",
    "BARK_BegForLife": "fearful",
    "BARK_CombArea": "shouts",
    "BARK_DogHasScent": "excited",
    "BARK_DogLostTrail": "frustrated",
    "BARK_DropHim": "angry",
    "BARK_GroupScatter": "shouts",
    "BARK_InvestigationGreeting": "curious",
    "BARK_LightShot": "surprised",
    "BARK_LightsOut": "frustrated",
    "BARK_LookingForYou": "shouts",
    "BARK_LostPlayer": "frustrated",
    "BARK_Mystified": "curious",
    "BARK_NormalGreeting": "",
    "BARK_PlayerKilled": "excited",
    "BARK_SearchFailedOther": "calmly",
    "BARK_SearchFailedPlayer": "frustrated",
    "BARK_SeeBrokenCamera": "concerned",
    "BARK_SeeCorpse": "shocked",
    "BARK_SeeHackedTurret": "concerned",
    "BARK_SeePlayer": "shouts",
    "BARK_SeeSomethingMove": "curious",
    "BARK_SeeUnconscious": "concerned",
    "BARK_ShootHim": "shouts",
    "BARK_SurprisedByPlayer": "shocked",
    "BARK_UnderFire": "shouts",
}

def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def slug(s):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_").lower()

def speaker_reference_map(rows):
    seen = defaultdict(set)
    for r in rows:
        speaker = SPEAKER_ALIASES.get(r["speaker_reference"].strip(), r["speaker_reference"].strip())
        if speaker:
            seen[r["event_name"]].add(speaker)
    return {k: sorted(v) for k,v in seen.items()}

def locate(row, story_ref):
    speaker = row["speaker_or_archetype"]
    switch = row["switch_values"]
    if "BARK_" in switch:
        return speaker, "BARK", re.search(r"BARK_[A-Za-z0-9_]+", switch).group(0), "CONFIRMED_ARCHETYPE"
    if speaker == "WalkieTallkie":
        faction = re.match(r"TAW[A-Z]+", row["resource_name"])
        return "RADIO_"+(faction.group(0) if faction else "OTHER"), "RADIO", "", "ARCHETYPE_NOT_INDIVIDUAL"
    if speaker == "Camera":
        source = row["resource_name"].replace("Music_","").replace(".LS0","")
        return "CAMERA_"+source.upper(), "CAMERA", "", "ARCHETYPE_NOT_INDIVIDUAL"
    if re.match(r"^S\d.*Voice$", speaker):
        matched = story_ref.get(row["event_name"], [])
        if len(matched) == 1:
            return "STORY_"+matched[0], "STORY", "", "SCRIPT_SPEAKER"
        return "", "STORY", "", "NEEDS_CHARACTER_ASSIGNMENT"
    return speaker, "SHORT_COMMAND", "", "CONFIRMED_ARCHETYPE"

def emotion(row, kind, bark):
    s = row["turkish_final"].lower()
    if kind == "BARK":
        if bark == "BARK_ShootHim" and any(x in s for x in ("beni vurma","ateş etme","yardım et","beni öldürme","lütfen")):
            return "fearful"
        if bark == "BARK_DropHim" and any(x in s for x in ("konuş","ateş etmeyece","zorlaştırma")):
            return "calmly"
        return EMOTION_BY_BARK.get(bark, "calmly")
    if kind in ("RADIO", "CAMERA"):
        return "urgently" if ("!" in s or "alarm" in s or "düşman" in s) else "calmly"
    if kind == "STORY":
        if any(x in s for x in ("ölmek istemiyorum", "zarar verme", "yalvar")):return "fearful"
        if any(x in s for x in ("çabuk", "dikkat", "hemen", "takviye")):return "urgently"
        if "?" in s:return "curious"
        return "calmly"
    if s.endswith("!"):return "shouts"
    return "calmly"

def write_rows(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def write_chunks(rows, out, prefix, limit):
    chunks=[]
    current=[]
    current_chars=0
    for r in rows:
        tag = "["+r["emotion"]+"] " if r["emotion"] else ""
        # Spoken material only; do not insert IDs into the prompt.
        line = tag+r["turkish_final"].strip()
        if len(line) > limit:
            raise ValueError("Tek replik limitten uzun: "+r["new_id"])
        overhead = len("\n\n[short pause]\n\n") if current else 0
        if current and current_chars+overhead+len(line)>limit:
            chunks.append(current)
            current=[];current_chars=0
        current.append((r,line))
        current_chars += overhead+len(line)
    if current:chunks.append(current)
    outputs=[]
    for i,chunk in enumerate(chunks,1):
        name=f"{prefix}_part{i:03d}"
        (out/f"{name}.txt").write_text(
            "\n\n[short pause]\n\n".join(line for _,line in chunk)+"\n",
            encoding="utf-8"
        )
        for j,(r,line) in enumerate(chunk,1):
            outputs.append({
                "mp3_target":name+".mp3",
                "line_in_mp3":j,
                "new_id":r["new_id"],
                "voice_group":r["voice_group"],
                "emotion":r["emotion"],
                "turkish_final":r["turkish_final"],
                "event_name":r["event_name"],
                "map":r["map"],
                "duration_sec":r["duration_sec"],
                "source_pcm_sha256":r["source_pcm_sha256"],
            })
    return outputs

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=DEFAULT_ROOT)
    p.add_argument("--out",default=str(Path.home()/"Downloads"/"SplinterCell-ElevenLabs"))
    p.add_argument("--max-chars",type=int,default=2200)
    args=p.parse_args()
    if args.max_chars < 300 or args.max_chars > 2800:
        raise SystemExit("--max-chars must be between 300 and 2800 for this export")
    root=Path(args.root).expanduser()
    rows=load_csv(root/REL_MANIFEST)
    refs=speaker_reference_map(load_csv(root/REL_SCRIPT))
    assert len(rows)==1258, len(rows)
    assert len({r["new_id"] for r in rows})==1258
    assert all(r["translation_status"]=="FINAL_TR" and r["turkish_final"].strip() for r in rows)
    out=Path(args.out).expanduser()
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Output directory must be empty: "+str(out))
    out.mkdir(parents=True, exist_ok=True)
    ready=defaultdict(list)
    unresolved=[]
    used_ids=set()
    for r in rows:
        actor,kind,bark,certainty=locate(r,refs)
        er={**r,"voice_group":actor,"kind":kind,"bark":bark,"cast_evidence":certainty,"emotion":emotion(r,kind,bark)}
        if not actor:
            unresolved.append(er)
        else:
            ready[actor].append(er)
            used_ids.add(r["new_id"])
    assert len(used_ids)+len(unresolved)==1258
    assert len(unresolved)==94, ("Review role count changed",len(unresolved))
    index=[]
    groups_summary=[]
    for group,group_rows in sorted(ready.items()):
        group_rows.sort(key=lambda r:(r["map"],r["event_name"],r["new_id"]))
        records=write_chunks(group_rows,out,slug(group),args.max_chars)
        index.extend(records)
        groups_summary.append({"voice_group":group,"lines":len(group_rows),"mp3_parts":len(set(r["mp3_target"] for r in records)),"cast_evidence":group_rows[0]["cast_evidence"]})
    fields=["mp3_target","line_in_mp3","new_id","voice_group","emotion","turkish_final","event_name","map","duration_sec","source_pcm_sha256"]
    write_rows(out/"00_production_index.csv",fields,index)
    write_rows(out/"00_voice_groups.csv",["voice_group","lines","mp3_parts","cast_evidence"],groups_summary)
    write_rows(out/"00_story_needs_character_assignment.csv",
        ["new_id","speaker_or_archetype","event_name","map","source_text_final","turkish_final","emotion","duration_sec"],
        unresolved)
    # Two previous 678-source gaps, not in this 1258 new-source list.
    (out/"legacy_S126_01_officer.txt").write_text("[annoyed] Avtandil, şu köpeğinin pisliğini temizlesene.\n",encoding="utf-8")
    (out/"legacy_S126_02_subordinate.txt").write_text("[respectfully] Emredersiniz.\n",encoding="utf-8")
    (out/"legacy_S126_mapping.csv").write_text(
        "new_id,voice_group,order,turkish_final\n"
        'u000972,S126_OFFICER,1,"Avtandil, şu köpeğinin pisliğini temizlesene."\n'
        'u000975,S126_SUBORDINATE,1,"Emredersiniz."\n',
        encoding="utf-8"
    )
    (out/"README.txt").write_text(
        "YENI DUBLAJ URETIMI — 1258 yeni ses kaydi\n"
        f"Sesi tanimlanabilir ve sirali: {len(index)}\n"
        f"Senaryodaki karakteri henuz atanamayan: {len(unresolved)}\n"
        "Bunlar tek bir karakter sanilmaz; 00_story_needs_character_assignment.csv icinde ayrica tutulur.\n"
        "Onceki oyun ici corpus'un kaynak MP3'u eksik iki replik: legacy_S126_01/02.\n"
        "Kullanici her TXT icin ilgili karakter sesini secip tek MP3 uretir.\n"
        "MP3 adini TXT adi gibi verir; 00_production_index.csv her satiri ve ID'yi esler.\n"
        "TXT dosyalarina ID veya satir numarasi EKLEME; ses olarak okunmamali.\n"
        "[short pause] ve duygu etiketleri Eleven v3'e gore hazirlandi. Onceki V4 veya Multilingual v2 ses modu secilirse etiketlerin islenmesi farkli olabilir.\n"
        "Telsiz/kamera kayitlari temiz ses olarak uretilir; efekt sonra uygulanir.\n"
        "Otomatik kesim/oyun kurulumu bu disariya aktarmanin parcasi degildir.\n"
        "54 vocalization ayri kuyrukta, 265 FMV bu listenin disindadir.\n",
        encoding="utf-8"
    )
    print("MANIFEST 1258")
    print("ELEVENLABS READY:",len(index))
    print("STORY SPEAKER REVIEW:",len(unresolved))
    print("LEGACY MISSING AUDIO:",2)
    print("GROUPS:",len(ready))
    print("PROMPT FILES:",sum(g["mp3_parts"] for g in groups_summary))
    print("OUTPUT:",out)

if __name__=="__main__":
    main()
