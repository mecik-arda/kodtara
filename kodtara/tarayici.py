from __future__ import annotations

import ast
import re
from pathlib import Path

from .modeller import Bulgu

DESTEKLENEN_UZANTILAR = (".py", ".js", ".ts", ".jsx", ".tsx")
ATLANACAK_DIZINLER = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".ruff_cache"}
EN_BUYUK_DOSYA = 1_000_000

PROMPT_HEDEFI = re.compile(r"(system|sistem|talimat|instruction|prompt)", re.IGNORECASE)
KULLANICI_GIRDISI = re.compile(r"(user_input|userinput|\buser\w*|kullan[iÄ±]c[iÄ±]|\bgirdi\b|istek|soru|sorgu|mesaj|request\.|args\.|form\[|\binput\w*|sys\.argv)", re.IGNORECASE)
LLM_KAYNAK = re.compile(r"(llm|openai|anthropic|gemini|ollama|chat|completion|model|yanit|cevap|cikti|sonuc|response|output|reply)", re.IGNORECASE)
LLM_URETIM_FONK = re.compile(r"(^|[.`\s])(invoke|arun|create|chat|complete|generate|predict|stream|__call__)\b", re.IGNORECASE)
TEHLIKELI_CAGRI = re.compile(r"\b(exec|eval|compile)\s*\(|os\.system\s*\(|subprocess\.(run|call|Popen|check_output|check_call)\s*\(|pickle\.loads\s*\(")
KABUK_YETKI = re.compile(r"shell\s*=\s*True\b|\brm\s+-rf\b|\bsudo\s+[a-z]|\bchmod\s+777\b")
DIS_ISTEK = re.compile(r"\brequests\.(post|get|put|patch|delete)\s*\(|\bhttpx\.\w+\s*\(|\bfetch\s*\(")
HTML_BASMA = re.compile(r"innerHTML|dangerouslySetInnerHTML|\|\s*safe\b|markdown\.markdown\s*\(|mark_safe\s*\(|\brender\w*\s*\(", re.IGNORECASE)
LOG_FONK = re.compile(r"\bprint\s*\(|\blogging\.(info|debug|warning|error|critical)\s*\(|\blogger\.\w+\s*\(|\bconsole\.log\s*\(")
GIZLI_AD = re.compile(r"(api[_-]?key|apikey|secret|token|password|sifre|parola|authorization|auth[_-]?header)", re.IGNORECASE)

GIZLI_KALIPLAR = [
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{8,}"), "Anthropic anahtarÄ±"),
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "OpenAI anahtarÄ±"),
    (re.compile(r"hf_[A-Za-z0-9]{8,}"), "Hugging Face jetonu"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS eriÅŸim anahtarÄ±"),
    (re.compile(r"ghp_[A-Za-z0-9]{8,}"), "GitHub jetonu"),
    (re.compile(r"xox[bpas]-[A-Za-z0-9\-]{8,}"), "Slack jetonu"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Ã–zel anahtar"),
]


def _maskele(deger: str, gorunur: int = 4) -> str:
    metin = deger.strip()
    if len(metin) <= gorunur + 3:
        return metin[:gorunur] + "***"
    return metin[:gorunur] + "***" + metin[-2:]


def _kanit(satir: str) -> str:
    kisa = " ".join(satir.split())[:120]
    for kalip, _ad in GIZLI_KALIPLAR:
        kisa = kalip.sub(lambda m: _maskele(m.group(0)), kisa)
    return kisa


def _kabuk_riski(satir: str) -> bool:
    if not KABUK_YETKI.search(satir):
        return False
    dizi_disi = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`', "", satir, flags=re.DOTALL)
    return bool(KABUK_YETKI.search(dizi_disi))


def _llm_kaynakli_fonksiyon(fonksiyon: str) -> bool:
    return bool(LLM_URETIM_FONK.search(fonksiyon) or LLM_KAYNAK.search(fonksiyon))


def _degiskenler_kesisim(metin: str, kaynak: set[str]) -> set[str]:
    adlar = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", metin))
    return adlar & kaynak


def _python_veriakisi(metin: str) -> tuple[set[str], set[str]]:
    """AST'ten (llm kaynaklÄ± deÄŸiÅŸkenler, kullanÄ±cÄ± girdisi deÄŸiÅŸkenleri)."""
    llm_deg: set[str] = set()
    girdi_deg: set[str] = set()
    try:
        agac = ast.parse(metin)
    except SyntaxError:
        return llm_deg, girdi_deg

    def _girdi_kaynagi(cagri: ast.Call) -> bool:
        if isinstance(cagri.func, ast.Name):
            return cagri.func.id in {"input", "getpass"}
        s = ast.unparse(cagri.func).lower()
        return bool(re.search(r"(request\.(form|args|json|data)|sys\.argv|\.get\()", s))

    for dugum in ast.walk(agac):
        deger = None
        hedefler: list[ast.AST] = []
        if isinstance(dugum, ast.Assign):
            deger = dugum.value
            hedefler = list(dugum.targets)
        elif isinstance(dugum, ast.AnnAssign):
            deger = dugum.value
            hedefler = [dugum.target]
        if not isinstance(deger, ast.Call) or not hedefler:
            continue
        fonksiyon = ast.unparse(deger.func) if hasattr(ast, "unparse") else ""
        girdi = _girdi_kaynagi(deger)
        llm = _llm_kaynakli_fonksiyon(fonksiyon)
        for hedef in hedefler:
            ad = _hedef_adi(hedef)
            if not ad:
                continue
            if girdi:
                girdi_deg.add(ad)
            elif llm:
                llm_deg.add(ad)
    return llm_deg, girdi_deg


def _hedef_adi(hedef: ast.AST) -> str | None:
    if isinstance(hedef, ast.Name):
        return hedef.id
    if isinstance(hedef, (ast.Tuple, ast.List)):
        for eleman in hedef.elts:
            ad = _hedef_adi(eleman)
            if ad:
                return ad
    return None


def _satir_metinleri(metin: str) -> list[str]:
    return metin.splitlines()


def _satir_al(satirlar: list[str], numara: int) -> str:
    if 1 <= numara <= len(satirlar):
        return satirlar[numara - 1].strip()
    return ""


def _python_ast_tara(metin: str, goreceli: str) -> list[Bulgu]:
    satirlar = _satir_metinleri(metin)
    try:
        agac = ast.parse(metin)
    except SyntaxError as hata:
        return [Bulgu("KDT00", "dusuk", goreceli, hata.lineno or 1, "Dosya ayrÄ±ÅŸtÄ±rÄ±lamadÄ±, metin kurallarÄ±yla tarandÄ±.", "", "DosyanÄ±n Python sÃ¶zdizimini dÃ¼zeltin.")]

    llm_deg, girdi_deg = _python_veriakisi(metin)
    bulgular: list[Bulgu] = []

    def _hedef_adlari(dugum: ast.AST) -> list[str]:
        adlar: list[str] = []
        for hedef in (dugum.targets if isinstance(dugum, ast.Assign) else [dugum.target]):
            ad = _hedef_adi(hedef)
            if ad:
                adlar.append(ad)
        return adlar

    # KDT01 (AST): prompt'a atanan JoinedStr iÃ§inde kullanÄ±cÄ± girdisi deÄŸiÅŸkeni
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.Assign, ast.AnnAssign)) or not isinstance(dugum.value, ast.JoinedStr):
            continue
        adlar = _hedef_adlari(dugum)
        hedef_prompt = any(PROMPT_HEDEFI.search(ad) for ad in adlar)
        sabit_metin = " ".join(
            c.value for c in dugum.value.values if isinstance(c, ast.Constant) and isinstance(c.value, str)
        )
        icerik_prompt = bool(PROMPT_HEDEFI.search(sabit_metin) and KULLANICI_GIRDISI.search(sabit_metin))
        if not (hedef_prompt or icerik_prompt):
            continue
        for deger in dugum.value.values:
            if not isinstance(deger, ast.FormattedValue):
                continue
            if isinstance(deger.value, ast.Name) and (deger.value.id in girdi_deg or KULLANICI_GIRDISI.search(deger.value.id)):
                satir_no = getattr(deger, "lineno", 1) or getattr(dugum, "lineno", 1)
                bulgular.append(Bulgu("KDT01", "yuksek", goreceli, satir_no, "KullanÄ±cÄ± girdisi sistem promptuna doÄŸrudan ekleniyor.", _kanit(_satir_al(satirlar, satir_no)), "KullanÄ±cÄ± girdisini sistem talimatÄ±yla birleÅŸtirmeyin; rol ayrÄ±mÄ± yapÄ±n."))
                break

    def _cagri_arguman_metni(cagri: ast.Call) -> str:
        parc = [a for a in cagri.args] + [k.value for k in cagri.keywords]
        return " ".join(ast.unparse(p) if hasattr(ast, "unparse") else "" for p in parc)

    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Call):
            continue
        fonksiyon = ast.unparse(dugum.func) if hasattr(ast, "unparse") else ""
        arguman = _cagri_arguman_metni(dugum)
        satir_no = getattr(dugum, "lineno", 1)
        if re.search(r"\b(exec|eval|compile)\s*$|os\.system$|subprocess\.(run|call|Popen|check_output|check_call)$|pickle\.loads$", fonksiyon):
            if _degiskenler_kesisim(arguman, llm_deg) or LLM_KAYNAK.search(arguman):
                bulgular.append(Bulgu("KDT02", "kritik", goreceli, satir_no, "Model Ã§Ä±ktÄ±sÄ± kod olarak Ã§alÄ±ÅŸtÄ±rÄ±lÄ±yor.", _kanit(_satir_al(satirlar, satir_no)), "Model Ã§Ä±ktÄ±sÄ±nÄ± exec, eval veya kabuk Ã§aÄŸrÄ±sÄ±na vermeyin; izin listesi kullanÄ±n."))
        elif re.search(r"\b(print|logging\.(info|debug|warning|error|critical)|logger\.\w+)\s*$", fonksiyon) and _degiskenler_kesisim(arguman, llm_deg):
            bulgular.append(Bulgu("KDT07", "orta", goreceli, satir_no, "Hassas deÄŸer log veya konsola yazÄ±lÄ±yor.", _kanit(_satir_al(satirlar, satir_no)), "Loglara model Ã§Ä±ktÄ±sÄ± veya gizli deÄŸer yazmayÄ±n."))
    return bulgular


def _metin_kurallari(metin: str, goreceli: str, py_mi: bool, llm_deg: set[str] | None = None) -> list[Bulgu]:
    bulgular: list[Bulgu] = []

    def _llm_iliskisi(satir: str) -> bool:
        if llm_deg is not None:
            return bool(_degiskenler_kesisim(satir, llm_deg))
        return bool(LLM_KAYNAK.search(satir.lower()))

    for sira, ham in enumerate(metin.splitlines(), 1):
        satir = ham.strip()
        if not satir or satir.startswith(("#", "//")):
            continue
        kucuk = satir.lower()
        if PROMPT_HEDEFI.search(satir) and KULLANICI_GIRDISI.search(satir):
            if 'f"' in satir or "f'" in satir or "${" in satir or ".format(" in satir or "%s" in satir or ("+" in satir and KULLANICI_GIRDISI.search(satir)):
                bulgular.append(Bulgu("KDT01", "yuksek", goreceli, sira, "KullanÄ±cÄ± girdisi sistem promptuna doÄŸrudan ekleniyor.", _kanit(satir), "KullanÄ±cÄ± girdisini sistem talimatÄ±yla birleÅŸtirmeyin; rol ayrÄ±mÄ± yapÄ±n."))
        if TEHLIKELI_CAGRI.search(satir) and not py_mi and _llm_iliskisi(satir):
            bulgular.append(Bulgu("KDT02", "kritik", goreceli, sira, "Model Ã§Ä±ktÄ±sÄ± kod olarak Ã§alÄ±ÅŸtÄ±rÄ±lÄ±yor.", _kanit(satir), "Model Ã§Ä±ktÄ±sÄ±nÄ± exec, eval veya kabuk Ã§aÄŸrÄ±sÄ±na vermeyin; izin listesi kullanÄ±n."))
        if DIS_ISTEK.search(satir) and _llm_iliskisi(satir):
            bulgular.append(Bulgu("KDT03", "yuksek", goreceli, sira, "Model Ã§Ä±ktÄ±sÄ± doÄŸrulanmadan dÄ±ÅŸ isteÄŸe gÃ¶nderiliyor.", _kanit(satir), "GÃ¶ndermeden Ã¶nce izin verilen alanlarÄ± seÃ§in."))
        if HTML_BASMA.search(satir) and _llm_iliskisi(satir):
            bulgular.append(Bulgu("KDT04", "yuksek", goreceli, sira, "Model Ã§Ä±ktÄ±sÄ± kaÃ§Ä±ÅŸsÄ±z HTML olarak basÄ±lÄ±yor.", _kanit(satir), "HTML basmadan Ã¶nce kaÃ§Ä±ÅŸ yapÄ±n."))
        if _kabuk_riski(satir):
            bulgular.append(Bulgu("KDT05", "yuksek", goreceli, sira, "AÅŸÄ±rÄ± yetkili kabuk veya yÄ±kÄ±cÄ± komut kalÄ±bÄ±.", _kanit(satir), "shell=True ve yÄ±kÄ±cÄ± komutlardan kaÃ§Ä±nÄ±n."))
        for kalip, ad in GIZLI_KALIPLAR:
            eslesme = kalip.search(satir)
            if eslesme:
                bulgular.append(Bulgu("KDT06", "kritik", goreceli, sira, f"Koda gÃ¶mÃ¼lÃ¼ gizli anahtar bulundu ({ad}).", _maskele(eslesme.group(0)), "AnahtarÄ± ortam deÄŸiÅŸkenine taÅŸÄ±yÄ±n."))
                break
        if LOG_FONK.search(satir) and not py_mi and GIZLI_AD.search(satir):
            bulgular.append(Bulgu("KDT07", "orta", goreceli, sira, "Hassas deÄŸer log veya konsola yazÄ±lÄ±yor.", _kanit(satir), "Loglara anahtar veya gizli deÄŸer yazmayÄ±n."))
    return bulgular


def _dosyalari_topla(kok: Path) -> tuple[list[Path], list[Path]]:
    cikti: list[Path] = []
    buyukler: list[Path] = []
    if kok.is_file():
        return [kok], []
    for yol in sorted(kok.rglob("*")):
        if not yol.is_file():
            continue
        if any(parca in ATLANACAK_DIZINLER for parca in yol.parts):
            continue
        if yol.suffix.lower() not in DESTEKLENEN_UZANTILAR:
            continue
        try:
            if yol.stat().st_size > EN_BUYUK_DOSYA:
                buyukler.append(yol)
                continue
        except OSError:
            continue
        cikti.append(yol)
    return cikti, buyukler


def tara_yolu(girdi: str | Path) -> tuple[list[Bulgu], list[str], list[str]]:
    kok = Path(girdi)
    if not kok.exists():
        raise ValueError("Tarama yolu bulunamadı.")
    dosyalar, buyukler = _dosyalari_topla(kok)
    bulgular: list[Bulgu] = []
    atlanan: list[str] = [str(y) for y in buyukler]
    taban = kok.resolve().parent if kok.resolve().is_file() else kok.resolve()
    for yol in dosyalar:
        try:
            metin = yol.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            atlanan.append(str(yol))
            continue
        try:
            goreceli = str(yol.resolve().relative_to(taban))
        except ValueError:
            goreceli = yol.name
        py_mi = yol.suffix.lower() == ".py"
        if py_mi:
            llm_deg, _ = _python_veriakisi(metin)
            ast_bulgular = _python_ast_tara(metin, goreceli)
            metin_bulgular = _metin_kurallari(metin, goreceli, py_mi=True, llm_deg=llm_deg)
            gorulen = {(b.kural, b.satir) for b in ast_bulgular}
            bulgular.extend(ast_bulgular)
            bulgular.extend(b for b in metin_bulgular if (b.kural, b.satir) not in gorulen)
        else:
            bulgular.extend(_metin_kurallari(metin, goreceli, py_mi=False))
    bulgular.sort(key=lambda b: (b.dosya, b.satir, b.kural))
    taranan = [str(y) for y in dosyalar if str(y) not in atlanan]
    return bulgular, taranan, atlanan

