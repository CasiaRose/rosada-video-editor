# Checks

`qa/verify.py cut.mp4 --style style.yaml --layout layout.json` measures the rendered file and judges it with `qa/engine.py`.

The report has one row per enabled check: `pass`, `fail`, or `not_run`. The file is deliverable only when every enabled check passed. The summary names every check that did not run and every check that failed.

Disabled checks are omitted. They are not treated as passes and they are not treated as skips.

## On by default

| Check | Pass |
|---|---|
| `loudness` | Integrated loudness within `audio.lufs_window` of `audio.master_lufs` |
| `true_peak` | True peak at or below `audio.true_peak_db` |
| `av_sync` | Absolute difference of the video and audio durations at or below `max_delta_s` (default 0.08 s) |
| `black_frames` | The darkest sampled frame is at least `luma_below` (default 12) |
| `frozen_or_repeated` | The share of near-duplicate frames is at or below `max_ratio` (default 0.05) |
| `caption_safe_zone` | Every caption box sits below `captions.safe_top` and above the bottom safe band |
| `text_overlap` | No two named text boxes intersect |

The plain preset's loudness target is −14 LUFS and −1.0 dBTP. Those numbers are a starting point in the profile. Change them there. They are not a fixed delivery law.

`caption_safe_zone` and `text_overlap` need boxes. `make_edit` writes `build/layout.json` from the profile. If you run the checker without a layout, those two checks are `not_run` and the file is not deliverable.

## Opt-in

`examples/checks.example.json` shows the shape. Set `"enabled": true` on a check to add it.

- `skin_cast` compares two b* samples you supply (`skin_b_star` and `skin_b_star_raw`). It does nothing until enabled and measured.
- `orientation` compares a direct frame difference with a left-right flip. It does nothing until enabled and measured.

Add further checks by extending `DEFAULT_CHECKS` and `evaluate` in `qa/engine.py`. Unknown names in a checks file are rejected.
