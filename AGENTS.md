# Instructions for AI assistants

This repository is a free short-form talking-head editor. Use it for whoever is sitting with you: a creator, not a built-in brand. These instructions apply to Grok, Claude Code, Cursor, Codex, and any other coding assistant.

Read this file before you edit, render, or install anything. The same text is in `CLAUDE.md`. A short copy lives in `.cursor/rules/` so Cursor loads it automatically.

## What this repo is

Vertical 1080×1920 video. A **style profile** decides fonts, colors, captions, hook placement, pace, b-roll density, border, and cover layout. Sound is generated from that profile. Checks are configurable. There is no fixed house look.

Useful docs: `docs/GETTING_STARTED.md` (for the creator), `README.md`, `docs/QA.md`, `docs/COVERS.md`.

## Order of work

Do these in order. Do not skip ahead to rendering.

1. **Check the computer.** `ffmpeg` and `ffprobe` must run. Python must be 3.10 or newer (`python3 --version`). If either is missing, give the creator the install step for their system and stop until it works.
2. **Install Python packages** in a virtual environment:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

   Install Playwright and Chromium only if you will render HTML panels.
3. **Style profile first.** Do not cut yet. Either walk `python style/questionnaire.py their-style.yaml` or measure a reference reel they provide with `python style/from_reference.py reference.mp4 their-style.yaml`. Show them the profile in plain language. Change it until they agree. Starter presets in `style/presets/` are only starting points.
4. **Sound preferences.** Read the `sound` section of the profile (mood, genre, energy, tempo, which moments get effects). Explain that with no key, a local synthesizer is used and that is fine. If they want ElevenLabs, they set `ELEVENLABS_API_KEY` in their own environment. Never ask them to paste a key into the chat, and never write a key into a file in this repo.
5. **Raw footage.** Copy it into the project folder. Do not edit the original. Probe it (`pipeline/probe.sh`) and align audio (`pipeline/extract_audio.sh`). Transcribe with `pipeline/transcribe.py`.
6. **Plan, then wait.** Write a short edit plan: what you will cut, the pace from their profile, where captions and the hook sit, what b-roll you will use, and how the sound will be made. Show the plan. **Do not render until they say yes.**
7. **Edit.** Cut with `pipeline/cut_vo.py` and their `--style`. Fill a recipe from `examples/recipe.example.json`. Run `pipeline/make_edit.sh recipe.json` only after the yes.
8. **Checks.** Run `qa/verify.py` on the rendered file with their style and the layout file. The summary must say the file is deliverable. If any check failed or did not run, say which ones and fix or supply the missing measurement. Do not call a skip a pass.
9. **Review notes.** Record their comments with `project/notes.py` (time, issue, status, still path). When they accept a fix, mark the note fixed and point at the still.
10. **Export.** Give them the finished file path, the cover if they asked for one, and the check summary. Receipts in `project/receipts.py` should record what was hashed so a later change only re-runs stale stages.

## Hard rules for the assistant

- The creator's profile wins over any default in `style/presets/`.
- Show the plan and get an OK before the first render, and again before you replace a file they have already watched.
- Keys stay in the environment. `ELEVENLABS_API_KEY` is read by `sound/elevenlabs.py` and nowhere else.
- Do not commit footage, renders, `.env` files, or real names that belong only to one client. Examples stay generic.
- Do not invent a posting schedule, a hashtag ban list, or a personal approval ritual. The creator decides when something is finished.
- If ffmpeg, Python, or a package is missing, stop and fix that. Do not improvise a different editor.
