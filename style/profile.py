"""Load, validate, and build a style profile.

A profile is a JSON or YAML document. It decides type, color, captions,
pacing, b-roll density, whether a border is drawn, and how covers are framed.
Presets in style/presets/ are neutral starting points, not a personal house look.
"""
import copy, json, os

NEUTRAL = {
    "name": "plain",
    "fonts": {"caption": "DejaVu Sans", "display": "DejaVu Sans", "mono": "DejaVu Sans Mono"},
    "colors": {
        "ink": "#1C1C1C",
        "paper": "#F7F7F5",
        "accent": "#3D5A80",
        "accent_2": "#E07A5F",
        "caption": "#FFFFFF",
        "caption_active": "#F2C14E",
    },
    "captions": {
        "mode": "block",
        "size": 58,
        "margin_v": 340,
        "margin_h": 80,
        "outline": 4,
        "shadow": 1,
        "animation": "none",
        "max_words": 5,
        "max_chars": 28,
        "safe_top": 150,
        "safe_bottom": 320,
    },
    "hook": {"placement": "top", "y": 240, "safe_top": 120, "safe_bottom": 280},
    "pacing": {
        "speed": 1.0,
        "silence_min_s": 0.45,
        "silence_keep_s": 0.28,
        "min_face_shot_s": 1.5,
        "last_word_hold_s": 0.5,
        "enforce_gap_cuts": True,
    },
    "broll": {"density": "medium", "per_minute": 3},
    "border": {"enabled": False},
    "cover": {
        "layout": "full_frame",
        "badge": "",
        "text_top": 180,
        "text_bottom": 1600,
        "crop_top": 0,
        "crop_bottom": 1920,
    },
    "audio": {
        "voice_lufs": -16.0,
        "bed_under_db": 16.0,
        "gap_lift_db": 4.0,
        "master_lufs": -14.0,
        "true_peak_db": -1.0,
        "lufs_window": 1.0,
    },
    "sound": {
        "mood": "calm",
        "genre": "ambient",
        "energy": "low",
        "tempo_bpm": 90,
        "intensity": 0.35,
        "sfx_moments": ["cut"],
    },
    "rules": {"show_references": False, "glitch_on_sections": False},
}

CAPTION_MODES = {"block", "karaoke", "none"}
HOOK_PLACEMENTS = {"top", "middle", "lower_third"}
DENSITIES = {"sparse", "medium", "dense"}
COVER_LAYOUTS = {"full_frame", "center_band"}
ANIMATIONS = {"none", "pop"}

def merge_profile(base, override):
    """Deep-merge mappings. Lists and scalars in override replace the base."""
    if override is None:
        return copy.deepcopy(base)
    if not isinstance(override, dict):
        raise ValueError("style profile must be a mapping")
    out = copy.deepcopy(base)
    for key, value in override.items():
        if key not in out:
            raise ValueError(f"unknown style field {key!r}")
        if isinstance(out[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{key} must be a mapping")
            for sub, subval in value.items():
                if sub not in out[key]:
                    raise ValueError(f"unknown style field {key}.{sub}")
                out[key][sub] = subval
        else:
            out[key] = value
    return out

def validate(profile):
    if profile["captions"]["mode"] not in CAPTION_MODES:
        raise ValueError("captions.mode must be block, karaoke, or none")
    if profile["captions"]["animation"] not in ANIMATIONS:
        raise ValueError("captions.animation must be none or pop")
    if profile["hook"]["placement"] not in HOOK_PLACEMENTS:
        raise ValueError("hook.placement must be top, middle, or lower_third")
    if profile["broll"]["density"] not in DENSITIES:
        raise ValueError("broll.density must be sparse, medium, or dense")
    if profile["cover"]["layout"] not in COVER_LAYOUTS:
        raise ValueError("cover.layout must be full_frame or center_band")
    speed = float(profile["pacing"]["speed"])
    if not 0.5 <= speed <= 2.0:
        raise ValueError("pacing.speed must be between 0.5 and 2")
    profile["pacing"]["speed"] = speed
    if not isinstance(profile["border"]["enabled"], bool):
        raise ValueError("border.enabled must be true or false")
    moments = profile["sound"]["sfx_moments"]
    if not isinstance(moments, list) or any(not isinstance(m, str) for m in moments):
        raise ValueError("sound.sfx_moments must be a list of names")
    return profile

def _parse_scalar(text):
    s = text.strip()
    if s in ("true", "True", "yes"):
        return True
    if s in ("false", "False", "no"):
        return False
    if s in ("null", "~", ""):
        return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    try:
        if any(c in s for c in ".eE"):
            return float(s)
        return int(s)
    except ValueError:
        return s

def parse_simple_yaml(text):
    """Indent-based YAML subset: mappings, lists, scalars. No anchors."""
    rows = []
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        rows.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))

    def block(i, indent):
        if i >= len(rows):
            return {}, i
        if rows[i][1].startswith("- "):
            items = []
            while i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
                item = rows[i][1][2:].strip()
                if item == "":
                    val, i = block(i + 1, indent + 2)
                    items.append(val)
                    continue
                if ":" in item:
                    key, _, rest = item.partition(":")
                    node = {key.strip(): _parse_scalar(rest)}
                    i += 1
                    while i < len(rows) and rows[i][0] > indent and not rows[i][1].startswith("- "):
                        k2, _, r2 = rows[i][1].partition(":")
                        if r2.strip() == "":
                            val, i = block(i + 1, rows[i][0] + 2)
                            node[k2.strip()] = val
                        else:
                            node[k2.strip()] = _parse_scalar(r2)
                            i += 1
                    items.append(node)
                else:
                    items.append(_parse_scalar(item))
                    i += 1
            return items, i
        node = {}
        while i < len(rows) and rows[i][0] == indent and not rows[i][1].startswith("- "):
            key, _, rest = rows[i][1].partition(":")
            if rest.strip() == "":
                val, i = block(i + 1, indent + 2)
                node[key.strip()] = val
            else:
                node[key.strip()] = _parse_scalar(rest)
                i += 1
        return node, i

    value, _ = block(0, rows[0][0] if rows else 0)
    return value

def load_profile(path):
    """Read a JSON or YAML profile and merge it onto the neutral preset."""
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    if path.endswith((".yaml", ".yml")):
        data = parse_simple_yaml(raw)
    else:
        data = json.loads(raw)
    return validate(merge_profile(NEUTRAL, data))

def dump_yaml(profile):
    """Write a profile as indented YAML."""
    def emit(value, indent):
        pad = " " * indent
        if isinstance(value, dict):
            lines = []
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}{key}:")
                    lines.extend(emit(item, indent + 2))
                else:
                    lines.append(f"{pad}{key}: {_scalar(item)}")
            return lines
        if isinstance(value, list):
            lines = []
            for item in value:
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}-")
                    lines.extend(emit(item, indent + 2))
                else:
                    lines.append(f"{pad}- {_scalar(item)}")
            return lines
        return [f"{pad}{_scalar(value)}"]
    return "\n".join(emit(profile, 0)) + "\n"

def _scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if text == "" or any(c in text for c in ":#[]{}") or text.lower() in ("true", "false", "null"):
        return json.dumps(text)
    return text

def answers_to_profile(answers):
    """Build a profile from a short questionnaire.

    Accepted keys: name, pace (slow|natural|brisk), captions (block|karaoke|none),
    border (bool), accent (hex), hook (top|middle|lower_third),
    broll (sparse|medium|dense), mood, genre, energy, tempo_bpm, sfx (list).
    """
    profile = copy.deepcopy(NEUTRAL)
    if answers.get("name"):
        profile["name"] = str(answers["name"])
    pace = answers.get("pace", "natural")
    if pace == "slow":
        profile["pacing"]["speed"] = 0.95
        profile["pacing"]["silence_keep_s"] = 0.4
        profile["sound"]["energy"] = "low"
        profile["sound"]["tempo_bpm"] = 76
    elif pace == "brisk":
        profile["pacing"]["speed"] = 1.08
        profile["pacing"]["silence_keep_s"] = 0.16
        profile["pacing"]["min_face_shot_s"] = 1.0
        profile["sound"]["energy"] = "high"
        profile["sound"]["tempo_bpm"] = 118
    elif pace != "natural":
        raise ValueError("pace must be slow, natural, or brisk")
    if "captions" in answers:
        profile["captions"]["mode"] = answers["captions"]
        profile["captions"]["animation"] = "pop" if answers["captions"] == "karaoke" else "none"
    if "border" in answers:
        profile["border"]["enabled"] = bool(answers["border"])
    if answers.get("accent"):
        profile["colors"]["accent"] = answers["accent"]
        profile["colors"]["caption_active"] = answers["accent"]
    if answers.get("hook"):
        profile["hook"]["placement"] = answers["hook"]
        profile["hook"]["y"] = {"top": 220, "middle": 780, "lower_third": 1200}[answers["hook"]]
    if answers.get("broll"):
        profile["broll"]["density"] = answers["broll"]
        profile["broll"]["per_minute"] = {"sparse": 1, "medium": 3, "dense": 6}[answers["broll"]]
    for key in ("mood", "genre", "energy"):
        if answers.get(key):
            profile["sound"][key] = answers[key]
    if answers.get("tempo_bpm"):
        profile["sound"]["tempo_bpm"] = int(answers["tempo_bpm"])
    if answers.get("sfx"):
        profile["sound"]["sfx_moments"] = list(answers["sfx"])
    return validate(profile)

def profile_from_measurements(measurements, base=None):
    """Turn measurements of a reference reel into a starting profile.

    measurements keys (all optional): cuts_per_minute, accent (hex),
    caption_y_ratio (0-1, where caption-like contrast sat), mean_shot_s.
    The result is a draft. The creator edits it before a render.
    """
    profile = copy.deepcopy(base or NEUTRAL)
    cpm = measurements.get("cuts_per_minute")
    if cpm is not None:
        cpm = float(cpm)
        if cpm >= 10:
            profile["pacing"]["speed"] = 1.06
            profile["pacing"]["silence_keep_s"] = 0.16
            profile["broll"]["density"] = "dense"
            profile["broll"]["per_minute"] = 6
            profile["sound"]["energy"] = "high"
            profile["sound"]["tempo_bpm"] = 120
        elif cpm <= 4:
            profile["pacing"]["speed"] = 1.0
            profile["pacing"]["silence_keep_s"] = 0.36
            profile["broll"]["density"] = "sparse"
            profile["broll"]["per_minute"] = 1
            profile["sound"]["energy"] = "low"
            profile["sound"]["tempo_bpm"] = 80
        else:
            profile["broll"]["density"] = "medium"
            profile["broll"]["per_minute"] = 3
    if measurements.get("accent"):
        profile["colors"]["accent"] = measurements["accent"]
        profile["colors"]["caption_active"] = measurements["accent"]
    ratio = measurements.get("caption_y_ratio")
    if ratio is not None:
        ratio = float(ratio)
        if ratio < 0.25:
            profile["hook"]["placement"] = "top"
            profile["hook"]["y"] = 200
            profile["captions"]["margin_v"] = 220
        elif ratio > 0.7:
            profile["hook"]["placement"] = "lower_third"
            profile["hook"]["y"] = 1180
            profile["captions"]["margin_v"] = 280
        else:
            profile["hook"]["placement"] = "middle"
            profile["hook"]["y"] = 760
    if measurements.get("mean_shot_s"):
        profile["pacing"]["min_face_shot_s"] = max(0.6, round(float(measurements["mean_shot_s"]) * 0.5, 2))
    profile["name"] = measurements.get("name") or "from-reference"
    return validate(profile)

def preset_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")
