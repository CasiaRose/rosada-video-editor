import os, sys, tempfile, unittest, wave
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sound.generate import generate
from style.profile import NEUTRAL

class SoundFallbackTests(unittest.TestCase):
    def test_local_provider_writes_bed_and_effects_and_caches(self):
        style = dict(NEUTRAL)
        style["sound"] = dict(NEUTRAL["sound"])
        style["sound"]["sfx_moments"] = ["cut", "text"]
        style["sound"]["tempo_bpm"] = 100
        with tempfile.TemporaryDirectory() as tmp:
            first = generate(tmp, style=style, provider="local", duration_s=0.4, effect_s=0.2)
            self.assertEqual(first["provider"], "local")
            self.assertFalse(first["cached"])
            self.assertTrue(os.path.getsize(first["bed"]) > 44)
            with wave.open(first["bed"]) as handle:
                self.assertEqual(handle.getframerate(), 48000)
                self.assertGreater(handle.getnframes(), 100)
            self.assertIn("cut", first["effects"])
            self.assertTrue(os.path.exists(first["effects"]["text"]))
            second = generate(tmp, style=style, provider="local", duration_s=0.4, effect_s=0.2)
            self.assertTrue(second["cached"])
            self.assertEqual(second["bed"], first["bed"])

    def test_auto_without_key_uses_local(self):
        os.environ.pop("ELEVENLABS_API_KEY", None)
        with tempfile.TemporaryDirectory() as tmp:
            manifest = generate(tmp, style=NEUTRAL, provider="auto", duration_s=0.3, effect_s=0.15)
        self.assertEqual(manifest["provider"], "local")

if __name__ == "__main__":
    unittest.main()
