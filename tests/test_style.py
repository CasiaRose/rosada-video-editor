import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from style.profile import (
    NEUTRAL, answers_to_profile, load_profile, merge_profile, profile_from_measurements, preset_dir,
)

class StyleProfileTests(unittest.TestCase):
    def test_plain_preset_is_neutral_pace_and_border_off(self):
        profile = load_profile(os.path.join(preset_dir(), "plain.yaml"))
        self.assertEqual(profile["pacing"]["speed"], 1.0)
        self.assertFalse(profile["border"]["enabled"])
        self.assertEqual(profile["captions"]["mode"], "block")
        self.assertEqual(profile["cover"]["badge"], "")
        self.assertFalse(profile["rules"]["show_references"])

    def test_json_preset_overrides_only_named_fields(self):
        profile = load_profile(os.path.join(preset_dir(), "punchy.json"))
        self.assertEqual(profile["captions"]["mode"], "karaoke")
        self.assertTrue(profile["border"]["enabled"])
        self.assertEqual(profile["fonts"]["caption"], NEUTRAL["fonts"]["caption"])

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_profile(NEUTRAL, {"house_badge": "nope"})

    def test_questionnaire_answers(self):
        profile = answers_to_profile({
            "name": "studio",
            "pace": "brisk",
            "captions": "karaoke",
            "border": False,
            "hook": "lower_third",
            "broll": "sparse",
            "mood": "tense",
            "sfx": ["cut", "text"],
        })
        self.assertEqual(profile["name"], "studio")
        self.assertGreater(profile["pacing"]["speed"], 1.0)
        self.assertEqual(profile["hook"]["placement"], "lower_third")
        self.assertEqual(profile["broll"]["density"], "sparse")
        self.assertEqual(profile["sound"]["sfx_moments"], ["cut", "text"])
        self.assertFalse(profile["border"]["enabled"])

    def test_reference_measurements_change_rhythm_and_color(self):
        profile = profile_from_measurements({
            "cuts_per_minute": 14,
            "accent": "#112233",
            "caption_y_ratio": 0.82,
            "mean_shot_s": 1.2,
        })
        self.assertEqual(profile["broll"]["density"], "dense")
        self.assertEqual(profile["colors"]["accent"], "#112233")
        self.assertEqual(profile["hook"]["placement"], "lower_third")
        self.assertGreater(profile["pacing"]["speed"], 1.0)

    def test_round_trip_yaml(self):
        from style.profile import dump_yaml
        profile = answers_to_profile({"name": "round", "pace": "slow", "accent": "#ABCDEF"})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "style.yaml")
            open(path, "w", encoding="utf-8").write(dump_yaml(profile))
            loaded = load_profile(path)
        self.assertEqual(loaded["name"], "round")
        self.assertEqual(loaded["colors"]["accent"], "#ABCDEF")
        self.assertLess(loaded["pacing"]["speed"], 1.0)

if __name__ == "__main__":
    unittest.main()
