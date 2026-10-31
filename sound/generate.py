#!/usr/bin/env python3
"""Generate a music bed and effects for one project, then cache them.

  python sound/generate.py project_dir --style style.yaml --provider auto

provider is auto, local, or elevenlabs. auto uses ElevenLabs only when
ELEVENLABS_API_KEY is set, and otherwise the local synthesizer. A failed
provider call falls back to local and says so in the manifest. The cache key
is the sound section of the profile plus the provider that actually ran.
"""
import argparse, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sound import elevenlabs, local
from style.profile import load_profile, NEUTRAL

def sound_prefs(style):
    prefs = dict(style.get("sound") or NEUTRAL["sound"])
    return prefs

def cache_dir(project_dir, prefs, provider):
    blob = json.dumps({"prefs": prefs, "provider": provider}, sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:16]
    return os.path.join(project_dir, "cache", "sound", digest)

def generate(project_dir, style=None, provider="auto", duration_s=8.0, effect_s=0.4):
    style = style or NEUTRAL
    prefs = sound_prefs(style)
    chosen = provider
    if chosen == "auto":
        chosen = "elevenlabs" if elevenlabs.api_key() else "local"
    folder = cache_dir(project_dir, prefs, chosen if chosen == "local" else "elevenlabs")
    manifest_path = os.path.join(folder, "manifest.json")
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        manifest["cached"] = True
        return manifest
    os.makedirs(folder, exist_ok=True)
    note = ""
    used = chosen
    bed_path = os.path.join(folder, "bed.wav" if chosen == "local" else "bed.mp3")
    if chosen == "elevenlabs":
        try:
            elevenlabs.music(prefs, bed_path, duration_s=max(duration_s, 3))
        except Exception as exc:
            used = "local"
            note = f"provider unavailable ({exc.__class__.__name__}); used local synthesizer"
            folder = cache_dir(project_dir, prefs, "local")
            os.makedirs(folder, exist_ok=True)
            bed_path = os.path.join(folder, "bed.wav")
            local.bed(prefs, bed_path, duration_s=duration_s)
    else:
        local.bed(prefs, bed_path, duration_s=duration_s)
    effects = {}
    cue_map = {}
    for moment in prefs.get("sfx_moments") or []:
        ext = "mp3" if used == "elevenlabs" else "wav"
        dest = os.path.join(folder, f"{moment}.{ext}")
        if used == "elevenlabs":
            try:
                elevenlabs.effect(moment, prefs, dest, duration_s=max(effect_s, 0.5))
            except Exception:
                dest = os.path.join(folder, f"{moment}.wav")
                local.effect(moment, prefs, dest, duration_s=effect_s)
                ext = "wav"
        else:
            local.effect(moment, prefs, dest, duration_s=effect_s)
        effects[moment] = dest
        cue_map[moment] = {"file": os.path.basename(dest), "db": -12, "align": "start"}
    cue_path = os.path.join(folder, "cue_map.json")
    json.dump(cue_map, open(cue_path, "w", encoding="utf-8"), indent=2)
    manifest = {
        "provider": used,
        "note": note,
        "cached": False,
        "bed": bed_path,
        "effects": effects,
        "cue_map": cue_path,
        "prefs": prefs,
    }
    json.dump(manifest, open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8"), indent=2)
    return manifest

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_dir")
    ap.add_argument("--style")
    ap.add_argument("--provider", default="auto", choices=["auto", "local", "elevenlabs"])
    ap.add_argument("--duration", type=float, default=8.0)
    args = ap.parse_args(argv)
    style = load_profile(args.style) if args.style else NEUTRAL
    manifest = generate(args.project_dir, style=style, provider=args.provider, duration_s=args.duration)
    print(json.dumps({k: manifest[k] for k in ("provider", "cached", "bed", "note")}, indent=2))

if __name__ == "__main__":
    main()
