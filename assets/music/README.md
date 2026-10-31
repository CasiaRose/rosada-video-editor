# Music

Beds are generated per project by `sound/generate.py` and cached under that project's `cache/sound/` directory. This folder is only a place to drop a bed you already have. Point the recipe `song` field at the file, or set `VEDIT_MUSIC` to another directory.

Nothing in this folder is required to render. With no `ELEVENLABS_API_KEY`, the local synthesizer writes a short tonal bed from the style profile (mood, genre, energy, tempo).
