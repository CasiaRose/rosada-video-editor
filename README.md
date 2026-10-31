# Short-form editor

New here? Start with [Getting started](docs/GETTING_STARTED.md). It shows how to download this folder and the first message to paste to an AI assistant. Assistants should follow [AGENTS.md](AGENTS.md). The code is [MIT licensed](LICENSE).

A talking-head pipeline for vertical video (1080×1920). Each creator brings a style profile. The same tools cut, caption, cover, mix, and check the file, and the picture and the sound follow that profile rather than a built-in look.

## What you need

| Tool | Used for |
|---|---|
| ffmpeg and ffprobe, with libass and libx264 | cuts, captions, loudness |
| DejaVu (`fonts-dejavu`) | the neutral caption and panel fonts |
| Any other font you name in the profile | set `VEDIT_FONT_TEXT`, `VEDIT_FONT_DISPLAY`, `INTER_FONT`, or `PK_FONT_DIR` |
| Python 3 | `pip install -r requirements.txt` |
| Optional Chrome | HTML panels. Set `CHROME` if it is not on `PATH` |
| Optional `ELEVENLABS_API_KEY` | generated music and effects. With no key, a local synthesizer is used |

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium   # only for HTML panels
```

Paths:

| Variable | Default |
|---|---|
| `VEDIT_ROOT` | this repo |
| `VEDIT_WORK` | the current directory |
| `VEDIT_MUSIC` | `assets/music` |
| `VEDIT_SFX` | `assets/sfx` |
| `VEDIT_HOTWORDS` | empty |
| `VEDIT_NAMES` | empty |

Footage and renders stay in the working directory. They are gitignored. Do not put API keys in files. The sound provider reads `ELEVENLABS_API_KEY` from the environment.

## Style

A profile is JSON or YAML. It covers fonts, colors, caption mode and animation, hook placement, pacing, b-roll density, border on or off, cover layout, and sound preferences. The schema and the merge rules are in `style/profile.py`. Three starters live in `style/presets/`:

- `plain.yaml` — natural pace, block captions, no border
- `steady.json` — slower, sparse b-roll
- `punchy.json` — faster, karaoke captions, border on

Build one from questions:

```bash
python style/questionnaire.py my-style.yaml --answers answers.json
# or run it with no --answers and answer the prompts
```

Or draft one from a reference reel (cut rate, a sampled accent color, and where high-contrast rows sit). The draft is yours to edit. Frames and audio from the reference are not copied.

```bash
python style/from_reference.py reference.mp4 my-style.yaml
```

## Workflow

1. Copy the raw file. Probe it with `pipeline/probe.sh` and put audio on the video clock with `pipeline/extract_audio.sh`.
2. Transcribe: `python pipeline/transcribe.py audio.wav medium words_raw.json` from a directory that has `config.json` (start from `examples/config.example.json`).
3. Cut: `python pipeline/cut_vo.py raw.mov words_raw.json keeps.json build/ --style my-style.yaml`. Joins snap into silence. Speed is the profile's `pacing.speed` (1.0 in the plain preset).
4. Copy `examples/recipe.example.json`, point `style` at your profile, and fill the picture.
5. `pipeline/make_edit.sh recipe.json` builds graphics, generates a bed and effects into `build/cache/sound/`, mixes, and runs checks.
6. Read the check summary. A failed check or a check that did not run means the file is not deliverable. The summary names those checks.
7. Notes and receipts live next to the edit. See below.

## Sound

`sound/generate.py` reads the profile's `sound` section: mood, genre, energy, tempo, intensity, and which moments get an effect.

- `ELEVENLABS_API_KEY` set and `--provider auto` or `elevenlabs`: music and sound-effects API calls. The key is never written into the project.
- No key, or the call fails: a local procedural bed and short effects, so a render still finishes.
- Output is cached under `<project>/cache/sound/<hash>/`. The same preferences and provider reuse the files.

## Checks

`qa/verify.py` (same report as `qa/report.py`) is the checker. Targets for loudness and true peak come from the profile's `audio` section. The plain preset starts at −14 LUFS and −1.0 dBTP with a ±1 LU window. Change those numbers in the profile.

On by default:

- loudness and true peak
- audio/video duration
- black frames
- frozen or repeated frames
- captions inside the safe zone from the profile
- overlapping text boxes

Anything else, including optional color and orientation samples, is off until `examples/checks.example.json` enables it. If an enabled check has nothing to measure, its status is `not_run` and the file is not deliverable. Disabled checks are left out of the report.

## Notes and receipts

```bash
python project/notes.py add project_dir --time 4.2 --issue "caption covers the subject"
python project/notes.py fix project_dir n1 --still stills/fix.jpg
python project/notes.py summary project_dir
```

Each note stores a timestamp, the issue, a status (`open` or `fixed`), and a path to a still.

```bash
python project/receipts.py record project_dir --stage cut --input raw=raw.mov --output cut=cut.mov --params '{"speed": 1.0}'
```

A receipt stores input hashes, a hash of the parameters, and output paths. `project/receipts.py plan` lists stages to re-run. A changed input marks that stage stale, and stages that depend on it (the finish depends on the cut and on the sound; sound does not depend on the cut). Fresh stages stay as they are.

## Layout

| Path | What it is |
|---|---|
| `style/` | Profile loader, presets, questionnaire, reference draft |
| `sound/` | ElevenLabs client and the local fallback |
| `pipeline/` | Transcribe, cut, punch-ins, b-roll, `make_edit`, finish |
| `captions/` | ASS captions from the profile |
| `covers/`, `graphics/`, `border/` | Stills, panels, optional progress stroke |
| `qa/` | Configurable checks |
| `project/` | Review notes and stage receipts |
| `examples/` | Recipe, config, and a short invented transcript |
| `docs/` | Workflow, checks, covers, and a comparison |
| `tests/` | Profile loading, local sound, skipped checks, staleness |

## Tests

```bash
python3 -m unittest tests.test_style tests.test_sound tests.test_checks tests.test_receipts
```
