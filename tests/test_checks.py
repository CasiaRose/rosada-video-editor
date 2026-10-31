import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qa.engine import evaluate
from style.profile import NEUTRAL

class CheckSkippedTests(unittest.TestCase):
    def test_missing_measurements_are_not_deliverable(self):
        report = evaluate({}, checks=None, style=NEUTRAL)
        self.assertFalse(report["deliverable"])
        self.assertIn("loudness", report["not_run"])
        self.assertIn("av_sync", report["not_run"])
        self.assertIn("caption_safe_zone", report["not_run"])
        self.assertIn("text_overlap", report["not_run"])
        self.assertNotIn("skin_cast", report["not_run"])
        self.assertIn("did not run", report["summary"])
        self.assertIn("loudness", report["summary"])

    def test_failed_check_is_named_and_blocks_delivery(self):
        meas = {
            "integrated_lufs": -24.0,
            "true_peak_db": -1.5,
            "video_s": 10.0,
            "audio_s": 10.0,
            "min_luma": 40,
            "repeat_ratio": 0.0,
            "caption_boxes": [[80, 400, 1000, 500]],
            "text_boxes": [{"name": "hook", "box": [80, 200, 1000, 420]}, {"name": "caption", "box": [80, 400, 1000, 500]}],
        }
        report = evaluate(meas, style=NEUTRAL)
        self.assertFalse(report["deliverable"])
        self.assertEqual(report["failed"], ["loudness", "text_overlap"])
        self.assertEqual(report["not_run"], [])
        self.assertIn("failed", report["summary"])

    def test_passing_measurements_are_deliverable(self):
        meas = {
            "integrated_lufs": -14.2,
            "true_peak_db": -1.4,
            "video_s": 12.0,
            "audio_s": 12.02,
            "min_luma": 30,
            "repeat_ratio": 0.01,
            "caption_boxes": [[80, 1500, 1000, 1580]],
            "text_boxes": [
                {"name": "hook", "box": [80, 200, 1000, 420]},
                {"name": "caption", "box": [80, 1500, 1000, 1580]},
            ],
        }
        report = evaluate(meas, style=NEUTRAL)
        self.assertTrue(report["deliverable"], report["summary"])
        self.assertEqual(report["not_run"], [])

    def test_opt_in_check_that_cannot_run_blocks_delivery(self):
        meas = {
            "integrated_lufs": -14.0,
            "true_peak_db": -1.2,
            "video_s": 5,
            "audio_s": 5,
            "min_luma": 20,
            "repeat_ratio": 0,
            "caption_boxes": [[80, 1500, 1000, 1560]],
            "text_boxes": [{"name": "caption", "box": [80, 1500, 1000, 1560]}],
        }
        report = evaluate(meas, checks={"orientation": {"enabled": True}}, style=NEUTRAL)
        self.assertFalse(report["deliverable"])
        self.assertIn("orientation", report["not_run"])

if __name__ == "__main__":
    unittest.main()
