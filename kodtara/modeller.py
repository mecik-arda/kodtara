from dataclasses import dataclass


SEVIYELER = {"dusuk": 1, "orta": 2, "yuksek": 3, "kritik": 4}

KURALLAR = {
    "KDT01": ("yuksek", "Kullanıcı girdisi sistem promptuna doğrudan ekleniyor."),
    "KDT02": ("kritik", "Model çıktısı kod olarak çalıştırılıyor."),
    "KDT03": ("yuksek", "Model çıktısı doğrulanmadan dış isteğe gönderiliyor."),
    "KDT04": ("yuksek", "Model çıktısı kaçışsız HTML olarak basılıyor."),
    "KDT05": ("yuksek", "Aşırı yetkili kabuk veya yıkıcı komut kalıbı."),
    "KDT06": ("kritik", "Koda gömülü gizli anahtar bulundu."),
    "KDT07": ("orta", "Hassas değer log veya konsola yazılıyor."),
}


@dataclass(frozen=True)
class Bulgu:
    kural: str
    seviye: str
    dosya: str
    satir: int
    aciklama: str
    kanit: str
    oneri: str
