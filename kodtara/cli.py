import argparse
import sys

from .modeller import SEVIYELER
from .raporlama import esik_asildi, raporla
from .tarayici import tara_yolu


class TurkceAyrıştırıcı(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace("usage:", "Kullanım:", 1)

    def format_help(self):
        return super().format_help().replace("usage:", "Kullanım:", 1)

    def error(self, mesaj):
        self.print_usage(sys.stderr)
        self.exit(2, "Hata: Komut veya seçenekler geçersiz. Yardım için --help kullanın.\n")


def ana(argumanlar: list[str] | None = None) -> int:
    ayrıştırıcı = TurkceAyrıştırıcı(
        prog="kodtara", description="KodTara LLM uygulama kodu tarayıcısı", add_help=False
    )
    ayrıştırıcı._positionals.title = "Komutlar"
    ayrıştırıcı._optionals.title = "Seçenekler"
    ayrıştırıcı.add_argument("--help", "-h", action="help", help="Yardımı göster ve çık")
    komutlar = ayrıştırıcı.add_subparsers(dest="komut", required=True)
    tara = komutlar.add_parser("tara", help="Kaynak kodu tara", add_help=False)
    tara._positionals.title = "Girdiler"
    tara._optionals.title = "Seçenekler"
    tara.add_argument("--help", "-h", action="help", help="Yardımı göster ve çık")
    tara.add_argument("yol", metavar="YOL", help="Dosya veya dizin")
    tara.add_argument("--bicim", choices=["metin", "json"], default="metin", help="Rapor biçimi")
    tara.add_argument(
        "--esik",
        choices=list(SEVIYELER),
        default="yuksek",
        help="Başarısız çıkış için en düşük risk seviyesi",
    )
    secenekler = ayrıştırıcı.parse_args(argumanlar)
    try:
        bulgular, taranan, atlanan = tara_yolu(secenekler.yol)
    except ValueError as hata:
        print(f"Hata: {hata}", file=sys.stderr)
        return 2
    if atlanan:
        print(f"Uyarı: {len(atlanan)} dosya atlandı (okunamadı veya çok büyük).", file=sys.stderr)
    print(raporla(bulgular, secenekler.bicim, len(taranan), secenekler.esik))
    return int(esik_asildi(bulgular, secenekler.esik))


if __name__ == "__main__":
    sys.exit(ana())
