#!/usr/bin/env python3
"""Ask a few questions and write a style profile.

  python style/questionnaire.py style.yaml
  python style/questionnaire.py style.json --answers answers.json

Non-interactive: pass --answers, a JSON object with the keys documented in
style.profile.answers_to_profile. Interactive mode reads stdin.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from style.profile import answers_to_profile, dump_yaml

QUESTIONS = [
    ("name", "Profile name", "plain"),
    ("pace", "Pace: slow, natural, or brisk", "natural"),
    ("captions", "Captions: block, karaoke, or none", "block"),
    ("border", "Draw a progress border? yes or no", "no"),
    ("accent", "Accent color as #RRGGBB (blank keeps the preset)", ""),
    ("hook", "Hook placement: top, middle, or lower_third", "top"),
    ("broll", "B-roll density: sparse, medium, or dense", "medium"),
    ("mood", "Music mood (calm, warm, bright, tense)", "calm"),
    ("genre", "Music genre (ambient, acoustic, pop, electronic)", "ambient"),
    ("energy", "Energy: low, medium, or high", "low"),
    ("tempo_bpm", "Tempo in BPM", "90"),
    ("sfx", "Sound-effect moments, comma-separated (cut, text, transition)", "cut"),
]

def _coerce(key, raw):
    raw = raw.strip()
    if key == "border":
        return raw.lower() in ("y", "yes", "true", "1")
    if key == "tempo_bpm":
        return int(raw or "90")
    if key == "sfx":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if key == "accent" and not raw:
        return None
    return raw

def from_prompt():
    answers = {}
    print("Style profile. Press enter to accept the suggestion in brackets.\n")
    for key, label, default in QUESTIONS:
        typed = input(f"{label} [{default}]: ").strip()
        value = _coerce(key, typed or default)
        if value is not None:
            answers[key] = value
    return answers

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    ap.add_argument("--answers")
    args = ap.parse_args(argv)
    if args.answers:
        answers = json.load(open(args.answers, encoding="utf-8"))
    else:
        answers = from_prompt()
    profile = answers_to_profile(answers)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    if args.out.endswith((".yaml", ".yml")):
        open(args.out, "w", encoding="utf-8").write(dump_yaml(profile))
    else:
        json.dump(profile, open(args.out, "w", encoding="utf-8"), indent=2)
        open(args.out, "a", encoding="utf-8").write("\n")
    print(f"wrote {args.out} ({profile['name']})")

if __name__ == "__main__":
    main()
