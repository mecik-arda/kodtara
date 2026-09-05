import json
import tempfile
import unittest
from pathlib import Path

from kodtara.cli import ana
from kodtara.tarayici import tara_yolu


RISKLİ = """import openai
import requests

sorgu = input("Soru: ")
system_prompt = f"Sen asistansın. Kullanıcı: {sorgu}"
yanit = openai.chat.completions.create(model="x", messages=[{"role": "system", "content": system_prompt}])
exec(yanit.choices[0].message.content)
requests.post("https://ornek.test", json={"cikti": yanit})
"""

GÜVENLİ = """import html
import openai

def uret(girdi):
    return openai.chat.completions.create(model="x", messages=[{"role": "user", "content": girdi}])

print(html.escape("merhaba"))
"""


class TaramaTestleri(unittest.TestCase):
    def _yaz(self, dizin, ad, icerik):
        yol = Path(dizin) / ad
        yol.write_text(icerik, encoding="utf-8")
        return yol

    def test_riskli_ornek(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "riskli.py", RISKLİ)
            bulgular, taranan, _ = tara_yolu(gecici)
            kurallar = {b.kural for b in bulgular}
            self.assertIn("KDT01", kurallar)
            self.assertIn("KDT02", kurallar)
            self.assertIn("KDT03", kurallar)
            self.assertTrue(any(b.seviye == "kritik" for b in bulgular))
            self.assertEqual(len(taranan), 1)

    def test_guvenli_ornek(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "guvenli.py", GÜVENLİ)
            bulgular, _, _ = tara_yolu(gecici)
            self.assertEqual([b for b in bulgular if b.seviye in {"kritik", "yuksek"}], [])

    def test_gizli_anahtar_maskelenir(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "anahtar.py", 'API_KEY = "sk-ORNEKANAHTAR1234567890"\n')
            bulgular, _, _ = tara_yolu(gecici)
            gizli = [b for b in bulgular if b.kural == "KDT06"]
            self.assertEqual(len(gizli), 1)
            self.assertNotIn("ORNEKANAHTAR1234567890", gizli[0].kanit)
            self.assertIn("sk-O", gizli[0].kanit)

    def test_js_kalibi(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "riskli.js", "const s = `Sistem: ${userInput}`;\neval(yanit);\n")
            bulgular, _, _ = tara_yolu(gecici)
            kurallar = {b.kural for b in bulgular}
            self.assertIn("KDT01", kurallar)
            self.assertIn("KDT02", kurallar)

    def test_kabuk_yetkisi(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "komut.py", "import subprocess\nsubprocess.run(cmd, shell=True)\n")
            bulgular, _, _ = tara_yolu(gecici)
            self.assertTrue(any(b.kural == "KDT05" for b in bulgular))

    def test_html_basma(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "web.js", "el.innerHTML = llmResponse;\n")
            bulgular, _, _ = tara_yolu(gecici)
            self.assertTrue(any(b.kural == "KDT04" for b in bulgular))

    def test_cli_cikis_kodlari(self):
        with tempfile.TemporaryDirectory() as gecici:
            riskli = self._yaz(gecici, "riskli.py", RISKLİ)
            self.assertEqual(ana(["tara", str(riskli), "--esik", "kritik"]), 1)
            guvenli = self._yaz(gecici, "guvenli.py", GÜVENLİ)
            self.assertEqual(ana(["tara", str(guvenli), "--esik", "kritik"]), 0)
            self.assertEqual(ana(["tara", str(Path(gecici) / "yok.py")]), 2)

    def test_json_bicimi(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "riskli.py", RISKLİ)
            bulgular, taranan, _ = tara_yolu(gecici)
            from kodtara.raporlama import raporla

            veri = json.loads(raporla(bulgular, "json", len(taranan), "yuksek"))
            self.assertIn("bulgular", veri)
            self.assertGreaterEqual(veri["bulgu_sayisi"], 3)

    def test_bozuk_python(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "bozuk.py", "def eksik(:\n")
            bulgular, taranan, _ = tara_yolu(gecici)
            self.assertEqual(len(taranan), 1)
            self.assertTrue(all(b.kural == "KDT00" for b in bulgular))

    def test_saf_komut_fp_yok(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "saf.py", 'import subprocess\nsubprocess.run(["git", "status"])\nimport requests\nprint(response.status_code)\n')
            bulgular, _, _ = tara_yolu(gecici)
            self.assertEqual([b for b in bulgular if b.kural in {"KDT02", "KDT03"}], [])

    def test_cok_satirli_fstring_yakalanir(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(
                gecici,
                "cok.py",
                'import openai\nsorgu = input("Soru: ")\nsystem_prompt = f"""Sen bir asistansin.\\nKullanici sorusu:\\n{sorgu}"""\nopenai.chat.completions.create(model="x", messages=[{"role": "system", "content": system_prompt}])\n',
            )
            bulgular, _, _ = tara_yolu(gecici)
            self.assertTrue(any(b.kural == "KDT01" for b in bulgular))

    def test_dizi_icinde_yikici_komut_fp_yok(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "zararsiz.py", 'def shutdown_handler():\n    pass\nsozluk = {"anahtar": "rm -rf /tmp/deneme"}\n')
            bulgular, _, _ = tara_yolu(gecici)
            self.assertEqual([b for b in bulgular if b.kural == "KDT05"], [])

    def test_js_kdt05_gercek_shell(self):
        with tempfile.TemporaryDirectory() as gecici:
            self._yaz(gecici, "kabuk.py", "import subprocess\nsubprocess.call('ls -la', shell=True)\n")
            bulgular, _, _ = tara_yolu(gecici)
            self.assertTrue(any(b.kural == "KDT05" for b in bulgular))


if __name__ == "__main__":
    unittest.main()
