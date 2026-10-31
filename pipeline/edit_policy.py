"""Optional edit policy read from a style profile.

Nothing here is on by default except a mild minimum face-shot length from the
profile. Reference-matching and section glitches run only when the profile
turns them on.
"""
import os, re

AGENTS = []
PHRASES = []
SHOW_START_TOL = 0.3
MIN_FACE_SHOT = 1.5
GLITCH_EVERY = 15.0
ENFORCE_SHOW = False
GLITCH_ON = False

def apply_style(style):
    """Copy pacing and optional rules from a loaded style profile."""
    global MIN_FACE_SHOT, ENFORCE_SHOW, GLITCH_ON
    pacing = style.get("pacing") or {}
    rules = style.get("rules") or {}
    MIN_FACE_SHOT = float(pacing.get("min_face_shot_s", MIN_FACE_SHOT))
    ENFORCE_SHOW = bool(rules.get("show_references"))
    GLITCH_ON = bool(rules.get("glitch_on_sections"))

def configure(names=None):
    """Names that must be shown, only when rules.show_references is on."""
    global AGENTS, PHRASES
    if names is None:
        names = [a.strip() for a in os.environ.get("VEDIT_NAMES", "").split(",") if a.strip()]
    AGENTS = [str(a) for a in names if str(a).strip()]
    extra = "|".join(re.escape(a.lower()) for a in AGENTS)
    extra = (extra + "|") if extra else ""
    PHRASES = [r"here (?:she|he|it|they) (?:is|are)", r"walk(?:s|ing)? (?:me|you|us) through", r"\bwatch\b", r"look at", r"check (?:this|it) out", r"\bmeet\b",
               r"this is (?:" + extra + r"my|our|her|his|the|what|how)\b"]

def glitch_budget(dur):
    if not GLITCH_ON:
        return 0
    return max(0, int(dur // GLITCH_EVERY))

def _clause_end(W, i, s0):
    e = W[i]["e"]
    for j in range(i, len(W)):
        e = W[j]["e"]
        if W[j]["w"][-1:] in ".?!" or (j + 1 < len(W) and W[j + 1]["s"] - W[j]["e"] > 0.35) or e - s0 > 4.0:
            break
    return min(e, s0 + 4.0)

def triggers(W):
    """Phrases that must be shown. Empty unless the profile asks for it."""
    if not ENFORCE_SHOW:
        return []
    toks = [re.sub(r"[^\w']", "", w["w"]) for w in W]
    low = [t.lower() for t in toks]
    out = []
    text = " ".join(low)
    starts = []
    pos = 0
    for t in low:
        starts.append(pos)
        pos += len(t) + 1
    def idx(ch):
        return max(k for k, p in enumerate(starts) if p <= ch)
    for pat in PHRASES:
        for match in re.finditer(pat, text):
            i = idx(match.start())
            needs_picture = not any(k in match.group(0) for k in ("watch", "look at", "check"))
            out.append(dict(text=match.group(0), s=W[i]["s"], e=_clause_end(W, idx(match.end() - 1), W[i]["s"]), needs="picture" if needs_picture else "any"))
    for i, token in enumerate(toks):
        if token in AGENTS:
            out.append(dict(text=token, s=W[i]["s"], e=W[i]["e"], needs="picture"))
    out.sort(key=lambda x: x["s"])
    merged = []
    for item in out:
        if merged and item["s"] <= merged[-1]["e"]:
            merged[-1]["e"] = max(merged[-1]["e"], item["e"])
            merged[-1]["text"] += " + " + item["text"]
            if item["needs"] == "picture":
                merged[-1]["needs"] = "picture"
        else:
            merged.append(dict(item))
    return merged

PICTURE_KINDS = ("footage", "hq_footage")
ANY_KINDS = ("footage", "hq_footage", "screen", "panel")
GRAPHIC_PATTERNS = ("/agents/", "/dashboards/", "agent-card", ".png", ".webm")

def covered(tr, shots):
    ok = PICTURE_KINDS if tr.get("needs") == "picture" else ANY_KINDS
    return any((a <= tr["s"] + SHOW_START_TOL) and b >= tr["e"] - 0.05 and (k in ok) for a, b, *kk in shots for k in [(kk[0] if kk else "footage")])

def looks_graphic(path):
    return any(p in path for p in GRAPHIC_PATTERNS)

def in_word(W, t, tol=0.06):
    return next((w for w in W if w["s"] + tol < t < w["e"] - tol), None)
