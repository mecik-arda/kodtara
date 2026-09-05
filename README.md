# kodtara

LLM uygulaması kodunda güvensiz prompt kurma ve çıktı işleme kalıplarını yakalayan hafif, **çevrimdışı** statik tarayıcı.

Python dosyalarını AST ile, JavaScript/TypeScript dosyalarını metin kurallarıyla tarar. Kod çalıştırmaz, ağa bağlanmaz. Çıktılar Türkçedir, CI'da kullanılabilir (`--bicim json`, çıkış kodları).

> **İlham:** OWASP LLM05 (güvensiz çıktı işleme) ve LLM06 (aşırı yetki) — sahada tekrar eden hata, model çıktısının `exec`/`eval`/kabuk çağrısına verilmesi ve sistem promptuna kullanıcı girdisinin gömülmesidir (Vanna.AI CVE-2024-5565 zinciri gibi). Bu kalıpları tek komutla yakalamak için yazıldı.

---

## Özellikler

- **Prompt birleştirme (KDT01)** — sistem promptuna f-string/`+`/`.format`/`${}` ile kullanıcı girdisi gömme
- **Çıktı çalıştırma (KDT02)** — model çıktısını `exec`, `eval`, `os.system`, `subprocess`, `pickle.loads` içine verme
- **Dış istek (KDT03)** — model çıktısını doğrulamadan `requests`/`httpx`/`fetch` ile dışarı gönderme
- **HTML basma (KDT04)** — model çıktısını `innerHTML`, `dangerouslySetInnerHTML`, `|safe`, `markdown` ile kaçışsız basma
- **Aşırı yetki (KDT05)** — `shell=True`, `rm -rf`, `sudo`, `chmod 777` kalıpları; yalnızca gerçek çağrılarda, string/dizi içi sözcüklerde değil
- **Gizli anahtar (KDT06)** — `sk-`, `sk-ant-`, `hf_`, `AKIA`, `ghp_`, Slack jetonu, özel anahtar; kanıt maskelenir
- **Log sızıntısı (KDT07)** — model çıktısı veya anahtar değerini `print`/`logging` ile yazma
- **Taint duyarlı** — KDT02/03/04/07 Python'da yalnızca LLM çağrısından türeyen değişkenlerde bildirilir; normal `subprocess`/`requests` kullanımı FP üretmez
- **Çıkış kodları** — eşik ve üzeri bulgu varsa 1, temizse 0, hata olursa 2
- **JSON çıktı** — `--bicim json` ile makine okunur sonuç

## Kurulum

```bash
git clone https://github.com/mecik-arda/kodtara
cd kodtara
pip install .
```

## Kullanım

```bash
# Dizini tara
kodtara tara ./src

# Tek dosyayı JSON olarak tara (CI için)
kodtara tara ornekler/riskli.py --bicim json --esik yuksek

# Eşiği düşür
kodtara tara ornekler --esik orta
```

Örnek çıktı:

```
KodTara: 1 dosya, 3 bulgu.

[Yuksek] riskli.py:5 KDT01: Kullanıcı girdisi sistem promptuna doğrudan ekleniyor.
  Kanıt: syst***}"
  Öneri: Kullanıcı girdisini sistem talimatıyla birleştirmeyin, rol ayrımı yapın.
[Kritik] riskli.py:7 KDT02: Model çıktısı kod olarak çalıştırılıyor.
  Kanıt: exec***nt
  Öneri: Model çıktısını exec, eval veya kabuk çağrısına vermeyin, izin listesi kullanın.
Risk eşiğine ulaşıldı.
```

## Denetlenenler

| Kural | Python (AST+metin) | JS/TS (metin) |
|---|---|---|
| KDT01 prompt birleştirme | ✓ | ✓ |
| KDT02 çıktı çalıştırma | ✓ | ✓ |
| KDT03 dış istek | ✓ | ✓ |
| KDT04 HTML basma | ✓ | ✓ |
| KDT05 aşırı yetki | ✓ | ✓ |
| KDT06 gizli anahtar | ✓ | ✓ |
| KDT07 log sızıntısı | ✓ | ✓ |

`.git`, `__pycache__`, `.venv`, `node_modules` atlanır. 1 MB üstü dosyalar atlanır. Ayrıştırılamayan Python dosyası `KDT00` olarak raporlanır; okunamayan/çok büyük dosyalar atlandığında CLI `Uyarı:` satırı basar, sessizce geçilmez.

## Güvenlik modeli

- Tarayıcı **yalnızca okur**; kodu çalıştırmaz, dosyayı değiştirmez, ağa bağlanmaz.
- Gizli anahtar kanıtları maskelenir (`sk-O***90` gibi); ham değer rapora yazılmaz.
- Tarayıcıyı **yalnızca kendi kodunuzda veya inceleme izniniz olan depolarda** çalıştırın.
- Statik tarama yaklaşıktır: kodlanmış veya parçalanmış değerler kaçabilir, her bulguyu gözle doğrulayın.

## Geliştirme

```bash
python -m unittest discover -s tests -v
```

## Lisans

[MIT](LICENSE) — [Arda Meçik](https://github.com/mecik-arda)

Bu proje, Türkçe yapay zeka güvenliği kaynak listesi
[awesome-ai-security-tr](https://github.com/fevziegeyurtsevenler/awesome-ai-security-tr)
ekosistemine katkı kapsamında geliştirilmiştir.

---

## Yazar

**[Arda Meçik](https://github.com/mecik-arda)** — siber güvenlik ve yapay zeka güvenliği üzerine çalışan geliştirici.

---

## Bu repoyu beğendiyseniz

KodTara, **Arda Meçik** tarafından geliştirilmiştir. Türkçe yapay zeka güvenliği ekosistemine katkı sağlamak için yazılan bu projeyi beğendiyseniz:

- **Yıldızlamayı unutmayın** — açık kaynak projelere destek, görünürlük demektir.
- **Takip edin:** [github.com/mecik-arda](https://github.com/mecik-arda) — vektör veritabanı güvenliği, LLM kod denetimi ve ajan güvenliği üzerine sürekli yeni araçlar ve Türkçe siber güvenlik yazıları yayımlıyorum.
- **Aynı ailenin diğer araçları:**
  - [vektortara](https://github.com/mecik-arda/vektortara) — ChromaDB/Qdrant/Weaviate güvenlik tarayıcısı
  - [izkalkan](https://github.com/mecik-arda/izkalkan) — ajan çağrı izlerinde hassas veri ve dış iletişim risk analizi
- **İş birliği / proje teklifleri için:** GitHub üzerinden iletişime geçebilirsiniz.

Her yıldız, yeni bir Türkçe güvenlik aracının yazılmasına teşvik olur. Teşekkürler!
