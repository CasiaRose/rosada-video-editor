"""PIL helpers for cards and a gentle grade.

The grade lifts blacks and eases contrast. It does not push a color channel.
"""
import io, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BLUSH = (244, 182, 194)
INK = (18, 6, 13)
WHITE = (255, 255, 255)
CREAM = (252, 247, 244)

def font(path, size):
    return ImageFont.truetype(path, int(size))

def frame_at(path, t):
    """One RGB frame of a clip at t seconds."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(out)).convert("RGB")

def soft_grade(im, sat=0.92, con=0.94, lift=6):
    """Slightly softer picture. No warm/yellow channel push."""
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Contrast(im).enhance(con)
    a = np.asarray(im).astype(np.float32)
    a = a * (1 - lift / 255.0) + lift
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def cover_crop(im, w, h, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))

def _round_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m

def shadow_paste(base, card, xy, rot=0, blur=22, off=(0, 14), opacity=0.45):
    """Paste an RGBA card with a soft drop shadow. Returns the card's box."""
    if rot:
        card = card.rotate(rot, Image.BICUBIC, expand=True)
    alpha = card.split()[3].point(lambda v: int(v * opacity))
    shadow = Image.new("RGBA", card.size, INK + (255,))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(blur)))
    pad = blur * 3
    big = Image.new("RGBA", (card.width + pad * 2, card.height + pad * 2), (0, 0, 0, 0))
    big.paste(shadow, (pad, pad), shadow)
    base.alpha_composite(big, (xy[0] - pad + off[0], xy[1] - pad + off[1]))
    base.alpha_composite(card, xy)
    return (xy[0], xy[1], xy[0] + card.width, xy[1] + card.height)

def photo_card(im, w, h, radius=34, border=14, label=None, label_font=None):
    """Rounded photo with a cream border. Optional label under the photo."""
    label_h = 0 if not label else 74
    card = Image.new("RGBA", (w + border * 2, h + border * 2 + label_h), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius + border, fill=CREAM + (255,))
    photo = cover_crop(im, w, h).convert("RGBA")
    photo.putalpha(_round_mask(w, h, radius))
    card.alpha_composite(photo, (border, border))
    if label and label_font is not None:
        ImageDraw.Draw(card).text((card.width // 2, h + border + label_h // 2 + 6), label, font=label_font, fill=INK, anchor="mm")
    return card
