# Effects

Effects are generated with the bed. `sound/generate.py` writes one file per name in `sound.sfx_moments` and a `cue_map.json` next to them. The finisher reads that map from the project cache.

`make_sfx.py` is an older standalone synthesizer. The command the pipeline calls is `python sound/generate.py <project_dir> --style <profile> --provider auto`.
