import tempfile
import unittest
from pathlib import Path

from kodtara.tarayici import tara_yolu

TURKCE_RISKLI = """sorgu = input("Soru: ")
system_prompt = f"Sistem talimatı. Kullanıcı girdisi: {sorgu}"
print(system_prompt)
"""


class TurkceTespitTestleri(unittest.TestCase):
    def test_turkce_kullanici_girdisi_yakalanir(self):
        with tempfile.TemporaryDirectory() as gecici:
            Path(gecici, "tr.py").write_text(TURKCE_RISKLI, encoding="utf-8")
            bulgular, _, _ = tara_yolu(gecici)
        self.assertIn("KDT01", {b.kural for b in bulgular})

    def test_turkce_rapor_mesaji_okunur(self):
        with tempfile.TemporaryDirectory() as gecici:
            Path(gecici, "tr.py").write_text(TURKCE_RISKLI, encoding="utf-8")
            bulgular, _, _ = tara_yolu(gecici)
        for bulgu in bulgular:
            self.assertNotIn("\ufffd", bulgu.aciklama)
            self.assertNotIn("\u00c3", bulgu.aciklama)
            self.assertNotIn("\u00c4", bulgu.aciklama)


if __name__ == "__main__":
    unittest.main()
