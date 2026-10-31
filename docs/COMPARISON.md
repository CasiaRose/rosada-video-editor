# This package and the public editor pack

Compared on 31 Oct 2026 with the public repository [mrpaidsocial/mrpaidsocial-video-editor-agent](https://github.com/mrpaidsocial/mrpaidsocial-video-editor-agent) (`main`). That repository has no license. None of its code or wording is copied here. This note describes both projects in original language, from that repo's public README, architecture, setup, and skill list, and from this package as it stands now.

## Architecture

This package is one vertical talking-head lane. A style profile (JSON or YAML) plus a recipe drive Python and ffmpeg: cut, captions, optional border, generated sound, and a check report. Personal names and the provider key stay in the environment or in an untracked project file.

The other project is a skill pack with a router and many lanes (branded spots, a cloned reel look, recaps, hook batches, synthetic-actor audio, and others). Procedures live in skill documents. Composition usually goes through an HTML renderer. A separate tool keeps project receipts and a footage catalog. Media is meant to live outside the pack, and brand details live in a gitignored context file.

## Editing

**Cuts.** Here, joins snap into silence and the speed, silence length, and minimum shot length are profile fields. The plain preset is 1.0×. Their pack also tightens silences, and it can remap a whole timeline, split one recording into many hooks, and join hook variants without re-encoding the body.

**Captions.** Here they are burned ASS. The profile chooses block, karaoke, or none, plus font, size, colors, and whether emphasis words pop. Their pack puts karaoke in the HTML composition and also has a path that lifts native phone-app text. Both time words from a transcript. The engines differ (faster-whisper here, whisper.cpp there, with a paid API as a fallback).

**B-roll.** Density (sparse, medium, dense) is a profile field, and a reference measurement can set it from cut rate. Their pack can capture a real site or generate picture through external services. Generated picture is not part of this pipeline.

**Motion graphics.** Panels, a two-line hook, and an optional progress border take their colors and placement from the profile. Hook placement may be top, middle, or lower third. Their pack treats the look as per brand and can write a style guide by studying a reference reel, then build card-per-line graphics, or stack image overlays on an uncut take.

**Music and effects.** A profile states mood, genre, energy, tempo, and which moments get an effect. ElevenLabs is used when `ELEVENLABS_API_KEY` is set. Otherwise a local synthesizer writes a bed and short effects into a per-project cache. Their pack generates effects and music through the same vendor and also rebuilds ambience on synthetic-actor audio. Both mix by levels. Theirs assumes the key. This package still renders without one.

**Covers.** Layout is `full_frame` or an optional center crop the profile defines. There is no required badge and no required text band. Their public docs describe review frames and contact sheets. They do not describe a profile-grid cover rule.

## Checks

Both sides measure the rendered file.

Here the enabled set is configurable. Loudness and true peak use the profile's targets. Sync, black frames, repeated frames, caption safe zone, and text overlap are on by default. Further checks are opt-in. A check that cannot run is `not_run`, the summary lists it, and the file is not deliverable. A skip is not a pass.

Their pack splits checking into layers: technical facts, a transcript of the render, an optional watch-and-listen model, and a frame inspection (safe-zone type, a graphic over a face, a caption over a face). Storyboard coverage is separate from what the pixels show. Exit status distinguishes pass, pass with warnings, and fail. A skipped optional layer is not called a clean pass. Some joins on a Mac are checked with another decoder. Several layers need API keys. The net is wider. It does not read this package's style profile.

## Workflow

Here the creator owns the profile. Notes are a JSON file: time, issue, status, and a still path. Receipts hash inputs and parameters so a changed file marks that stage and the stages that depend on it stale. Fresh stages are not redone.

Their agent picks a lane, can study a reference, builds, runs checks, and puts the cut on a review page with comments tied to times. Revisions read those notes, attach a frame, and write a new file per version. Approvals can sit in the project receipt. Shared review needs an external host. A local review works without one. There is an optional handoff into a CapCut draft, described there as unfinished.

## Setup

This package needs ffmpeg, the Python list in `requirements.txt`, and fonts. HTML panels need a browser. The first transcript downloads a whisper model. Sound needs no key. There is no one-command synthetic demo of a full picture edit. The unit tests cover the profile, the local synthesizer, the not-deliverable rule, and staleness without footage.

Their first-run command can install checker dependencies and build a synthetic edit, catalog, and review page without API keys, given Python, ffmpeg, and Node 20. The full set of lanes adds a composition tool, whisper.cpp, a sound key, optional vision and transcription keys, browser capture, and a review host.

## What each is good at

This package keeps one talking-head path and lets every visual and sonic choice live in a file the creator edits. It still finishes when there is no sound-vendor key. The check report refuses to treat a missing measurement as a pass. Notes and receipts are plain files.

Their pack covers many edit shapes, separates plan from pixels across several layers, and keeps a review thread and a footage catalog that outlive one chat. The demo runs before anyone has footage.

## Ideas already taken, in this package's own form

These were directions, not code.

1. A check that did not run blocks delivery, and the summary names it. That is `qa/engine.py`.
2. Notes with a time, a status, and a still path. That is `project/notes.py`.
3. Receipts with input hashes and parameters, so only stale stages re-run. That is `project/receipts.py`. Sound does not depend on the picture cut. Finish depends on both.

A reference reel can still seed a profile (`style/from_reference.py`): cut rate, one sampled color, and a vertical contrast hint. The creator edits the draft. The reference's pictures and words are not reused.
