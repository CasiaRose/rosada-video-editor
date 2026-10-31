import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from project.receipts import plan, record
from project.notes import add_note, set_status, summary

class ReceiptTests(unittest.TestCase):
    def test_changed_input_stales_that_stage_and_downstream_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "raw.bin")
            words = os.path.join(tmp, "words.json")
            cut = os.path.join(tmp, "cut.mov")
            bed = os.path.join(tmp, "bed.wav")
            final = os.path.join(tmp, "final.mp4")
            for path, text in ((raw, "take-a"), (words, "hello"), (cut, "cut-a"), (bed, "bed-a"), (final, "out-a")):
                open(path, "w", encoding="utf-8").write(text)
            record(tmp, "transcribe", {"raw": raw}, {"model": "medium"}, {"words": words})
            record(tmp, "cut", {"raw": raw, "words": words}, {"speed": 1.0}, {"cut": cut})
            record(tmp, "sound", {}, {"tempo": 90}, {"bed": bed})
            record(tmp, "finish", {"cut": cut, "bed": bed}, {"lufs": -14}, {"final": final})
            spec = [
                {"name": "transcribe", "inputs": {"raw": raw}, "params": {"model": "medium"}},
                {"name": "cut", "inputs": {"raw": raw, "words": words}, "params": {"speed": 1.0}},
                {"name": "sound", "inputs": {}, "params": {"tempo": 90}},
                {"name": "finish", "inputs": {"cut": cut, "bed": bed}, "params": {"lufs": -14}},
            ]
            self.assertEqual(plan(tmp, spec), [])
            open(words, "w", encoding="utf-8").write("hello again")
            stale = plan(tmp, spec)
            self.assertIn("cut", stale)
            self.assertIn("finish", stale)
            self.assertNotIn("transcribe", stale)
            self.assertNotIn("sound", stale)

    def test_notes_summary_lists_time_status_and_still(self):
        with tempfile.TemporaryDirectory() as tmp:
            add_note(tmp, 3.5, "caption covers the subject")
            set_status(tmp, "n1", "fixed", still="stills/fix.jpg")
            text = summary(tmp)
            self.assertIn("3.50s", text)
            self.assertIn("fixed", text)
            self.assertIn("stills/fix.jpg", text)
            self.assertIn("0 open", text)

if __name__ == "__main__":
    unittest.main()
