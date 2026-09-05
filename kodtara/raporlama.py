import json

from .modeller import SEVIYELER, Bulgu


def esik_asildi(bulgular: list[Bulgu], esik: str) -> bool:
    sinir = SEVIYELER[esik]
    return any(SEVIYELER[b.seviye] >= sinir for b in bulgular)


def raporla(bulgular: list[Bulgu], bicim: str, dosya_sayisi: int, esik: str) -> str:
    if bicim == "json":
        return json.dumps(
            {
                "dosya_sayisi": dosya_sayisi,
                "bulgu_sayisi": len(bulgular),
                "esik": esik,
                "bulgular": [
                    {
                        "kural": b.kural,
                        "seviye": b.seviye,
                        "dosya": b.dosya,
                        "satir": b.satir,
                        "aciklama": b.aciklama,
                        "kanit": b.kanit,
                        "oneri": b.oneri,
                    }
                    for b in bulgular
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    satirlar = [f"KodTara: {dosya_sayisi} dosya, {len(bulgular)} bulgu."]
    for bulgu in bulgular:
        satirlar.append(f"[{bulgu.seviye.capitalize()}] {bulgu.dosya}:{bulgu.satir} {bulgu.kural}: {bulgu.aciklama}")
        if bulgu.kanit:
            satirlar.append(f"  Kanıt: {bulgu.kanit}")
        satirlar.append(f"  Öneri: {bulgu.oneri}")
    if esik_asildi(bulgular, esik):
        satirlar.append("Risk eşiğine ulaşıldı.")
    return "\n".join(satirlar)
