#!/usr/bin/env python3
"""Build a private decoder; never modify the source checkout or installed game."""
import subprocess
from inventory import PROJECT, OUT, sha, json_write


def run():
    src=PROJECT/'tools/vgmstream-src'; build=OUT/'vgmstream-debug'
    OUT.mkdir(parents=True,exist_ok=True)
    options=['-DBUILD_CLI=ON','-DBUILD_AUDACIOUS=OFF','-DBUILD_V123=OFF','-DBUILD_VLC=OFF']
    options += ['-DUSE_'+codec+'=OFF' for codec in ['FFMPEG','MPEG','VORBIS','ATRAC9','CELT','G719','G7221','SPEEX']]
    with (OUT/'build-decoder.log').open('w') as log:
        subprocess.run(['cmake','-S',str(src),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release',*options],stdout=log,stderr=log,check=True)
        subprocess.run(['cmake','--build',str(build),'-j','4'],stdout=log,stderr=log,check=True)
    original=src/'src/meta/ubi_sb.c';fixed=OUT/'ubi_sb_fixed.c'
    text=original.read_text();before='sb->cfg.resource_name_size >= sizeof(sb->resource_name)';after='sb->cfg.resource_name_size > sizeof(sb->resource_name)'
    assert text.count(before)==1,'Reinspect source version before applying decoder patch'
    # read_string accepts the capacity including its terminating NUL. Equality
    # is valid; the previous check rejected every v7 sound (40 >= 40).
    fixed.write_text(text.replace(before,after))
    obj=OUT/'ubi_sb_fixed.o'
    subprocess.run(['cc','-O2','-DVGM_LOG_OUTPUT','-I',str(src/'src/meta'),'-I',str(src/'src'),'-I',str(src/'ext_includes'),'-c',str(fixed),'-o',str(obj)],check=True)
    cli=build/'cli/CMakeFiles/vgmstream_cli.dir'
    objects=[cli/(n+'.c.o') for n in ['vgmstream_cli','vgmstream_cli_utils','wav_utils','windows_utils']]
    subprocess.run(['cc',*map(str,objects),str(obj),str(build/'src/libvgmstream.a'),'-lm','-o',str(OUT/'vgmstream-cli')],check=True)
    json_write(OUT/'decoder-build.json',dict(source=str(original.relative_to(PROJECT)),original_sha256=sha(original),
        patched_sha256=sha(fixed),binary_sha256=sha(OUT/'vgmstream-cli'),patch_before=before,patch_after=after))
if __name__=='__main__':run()
