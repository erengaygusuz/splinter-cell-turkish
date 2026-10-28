"""Isolated helpers; never run the old 678 inventory or installation commands."""
import csv,hashlib,importlib.util,json,re,subprocess,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'dubbing/full-game-new-voices'
QA=BASE/'qa/R001_20261028'
BUILD=ROOT/'build/new1258/R001_20261028'
RATE=44100
GAME=Path('/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell')
INDEX=Path('/home/ereng/Downloads/SplinterCell-ElevenLabs')
spec=importlib.util.spec_from_file_location('vd001_alignment',ROOT/'dubbing/characters/sam_fisher/gameplay/voice_versions/VD001/tools/vd001_audio_qa.py')
alignment=importlib.util.module_from_spec(spec);spec.loader.exec_module(alignment)

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,obj,immutable=False):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if immutable and p.exists():assert read(p)==obj,f'Immutable evidence changed: {p}';return
    t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def table(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in data for k in r)),lineterminator='\n');w.writeheader();w.writerows(data)
def rel(p):return str(Path(p).relative_to(ROOT))

def pcm(path):
    import numpy as np
    raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-vn','-ac','1','-ar',str(RATE),'-f','s16le','-'])
    return np.frombuffer(raw,dtype='<i2')

def wav(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        with wave.open(str(path)) as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,RATE)
            assert w.readframes(w.getnframes())==data.tobytes(),f'Use a new revision: {path}'
        return
    with path.open('xb') as f:
        with wave.open(f,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(data.tobytes())
