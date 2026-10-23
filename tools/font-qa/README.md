# Turkish font POC / first safety gate

**Source branch:** experiment/turkish-font-readonly-probe, forked from fisher-audio-qa (not main).

No modifications to the installed game, Unreal packages, voice overrides, subtitles, or EnhancedSC are made in this phase.

## Why this probe?

Our earlier CP1254 test showed some Turkish characters but not others. The six codepage-specific Turkish characters in Windows-1254 have different meanings if treated as Windows-1252:

| TR | CP1254 byte | Same byte as Windows-1252 |
| --- | --- | --- |
| Ğ | D0 | Ð |
| İ | DD | Ý |
| Ş | DE | Þ |
| ğ | F0 | ð |
| ı | FD | ý |
| ş | FE | þ |

This proves a possible explanation, **not** the actual game decoder or Unicode support. Source inspection also identified older disabled TrueTypeFontFactory localized-font code and PCX Font IMPORT lines in EnhancedSC. Both issues must be tested separately.

## Run on the game PC (read-only)

From the local repository, without changing branch or pulling:

~~~bash
cd "/run/media/ereng/files/projects/splinter-cell-turkish" || exit 1
git fetch origin experiment/turkish-font-readonly-probe
git show origin/experiment/turkish-font-readonly-probe:tools/font-qa/probe.py > /tmp/sc-font-probe.py
python3 /tmp/sc-font-probe.py --output "$HOME/Downloads/sc-font-audit.json"
~~~

The JSON includes hashes, file existence, headers and codepage diagnostic counts, not the full game files. Send the JSON to inspect local sources before attempting a separate-font UCC build.

To run the test suite while working in this experiment branch:

~~~bash
python3 -m unittest discover -s tools/font-qa -p 'test_*.py' -v
~~~

## Next tests

1. Verify the currently installed EchelonHUD.u build and locate the last working subtitle HUD source.
2. Audit PCX sources and Engine.u / EchelonMenus.u markers without modifying them.
3. In a disposable UCC build environment, try a separately named TrueType font covering all Turkish codepoints.
4. Validate package exports and engine loading first. Install only with hash-checked backup and rollback.

**Compatibility warning:** a previously rebuilt EnhancedSC EchelonMenus.u caused an opening General Protection Fault. Avoid menu-package rebuilding until the isolated HUD path is tested.

References:
- https://github.com/Joshhhuaaa/EnhancedSC/blob/master/UnrealScript/Engine/Classes/Canvas.uc
- https://github.com/Joshhhuaaa/EnhancedSC/blob/master/UnrealScript/EchelonMenus/Classes/EPCMainMenuRootWindow.uc
- https://wiki.beyondunreal.com/TrueTypeFontFactory_/_UFontMaterial
