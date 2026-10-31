# Editing with a style profile

Use this when a raw vertical take should become a finished short. The look and the sound come from the creator's style profile (`style/presets/` or one they built). There is no house style and no house posting schedule.

1. Work on a copy of the raw file. Note its sha256.
2. Probe and align audio (`pipeline/probe.sh`, `pipeline/extract_audio.sh`).
3. Transcribe with faster-whisper. Hotwords come from `VEDIT_HOTWORDS` or `config.json`.
4. Agree the profile before cutting if the creator has not already written one. `style/questionnaire.py` or `style/from_reference.py` makes a draft. They edit it.
5. Cut with `pipeline/cut_vo.py --style their.yaml`. Pace, silence, and the minimum face-shot length are fields in that file.
6. Fill a recipe (`examples/recipe.example.json`) and run `pipeline/make_edit.sh`. It generates sound into the project cache unless a bed path is already set.
7. Run checks. Ship only when the summary says deliverable. If it lists checks that did not run, provide the missing measurement (a layout file, a loudness read) and run again.
8. Keep review notes in `review_notes.json` and stage receipts in `receipts.json`.

Caption mode, colors, hook placement, border, cover crop, and effect moments are all profile fields. See [README](../README.md) and [QA](QA.md).
