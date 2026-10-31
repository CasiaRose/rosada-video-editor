# Covers

Cover layout is a field on the style profile, not a fixed crop.

`cover.layout` is `full_frame` or `center_band`.

- `full_frame` keeps the whole 1080×1920 still. `covers/cover.py` writes that still.
- `center_band` also writes a crop. Set `crop_top` and `crop_bottom` (or pass `--crop-top` and `--crop-bottom`). A common center 3:4 band is y 240–1680, but only when the profile asks for it.

`cover.badge` is optional text. Empty means no badge. `covers/make_cover.py` draws `COVER_BADGE` only when that variable is set.

`cover.text_top` and `cover.text_bottom` are optional limits. Pass them as `--text-top` and `--text-bottom` and the tool rejects type outside the band. Without them, type may sit at the top, the middle, or the lower third, matching `hook.placement`.

```bash
python covers/cover.py frame.jpg out/cover --line1 "Small line" --line2 "THE LINE" --y0 240
python covers/cover.py frame.jpg out/cover --line1 "Small line" --line2 "THE LINE" \
  --y0 400 --crop-top 240 --crop-bottom 1680 --text-top 300 --text-bottom 1100
```

Colors come from the profile (`accent`, `ink`, `paper`). The panel kit uses the same neutral defaults until a profile replaces them.
