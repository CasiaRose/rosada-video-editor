# Graphics

`templates.html` is a set of panel scenes. Colors in the file are the neutral preset. A real edit passes its own params JSON.

```bash
python3 graphics/capture.py graphics/params/label.json build/label.mov
```

`bg: none` writes a transparent movie. Each capture also writes a `.cues.json`.

`hooks.py` draws a two-line hook. Pass `bounds` when the profile limits the vertical band. `gfx.py` builds cards and a grade that does not push a color channel.

`pipeline/pk.py` is the PIL panel kit used by the chunk compositor. Fonts come from `PK_FONT_DIR` (DejaVu by default).
