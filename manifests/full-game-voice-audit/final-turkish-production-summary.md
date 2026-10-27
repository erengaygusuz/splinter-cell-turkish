# Splinter Cell full-game Turkish voice production

- Original confirmed new speech corpus: 1245
- Original uncertain queue: 70
- User listening decisions: 229
- Final manual resolutions: 33

- FINAL SPEECH RECORDS: 1258
- VOCALIZATION RECORDS: 54
- NON-SPEECH EXCLUDED: 3

## Translation status
- FINAL_TR: 1258
- NEEDS_TR_TRANSLATION: 0

## User decision counts
- APPROVE_TEXT: 171
- NON_ENGLISH_SPEECH: 2
- NON_SPEECH: 3
- VOCALIZATION: 53

## Queue decision counts
- transcript / APPROVE_TEXT: 158
- transcript / VOCALIZATION: 1
- uncertain / APPROVE_TEXT: 13
- uncertain / NON_ENGLISH_SPEECH: 2
- uncertain / NON_SPEECH: 3
- uncertain / VOCALIZATION: 52

## Resolution sources
- AUDIT_CONFIRMED: 1086
- CONTEXT_RESOLVED: 22
- EXACT_AUDIO: 6
- FOREIGN_RESOLVED: 4
- USER_LISTENED: 140

## Policy
- Non-English speech remains in Turkish dubbing scope.
- Vocalizations are retained in a separate review manifest.
- Non-speech effects are excluded from dialogue production.
- `turkish_final` preserves natural Turkish spelling.
- `turkish_game_text` applies the project's deterministic Turkish-character conversion.
- Original audit manifests and V27 runtime are not modified.
