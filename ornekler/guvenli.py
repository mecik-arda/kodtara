import html
import os

import openai


def yanit_uret(kullanici_girdisi: str) -> str:
    yanit = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Sen yardımcı bir asistansın."},
            {"role": "user", "content": kullanici_girdisi},
        ],
    )
    return yanit.choices[0].message.content


def guvenli_goster(ham_cikti: str) -> str:
    return html.escape(ham_cikti)


if __name__ == "__main__":
    istek = "Merhaba"
    uretilen = yanit_uret(istek)
    güvenli_metin = guvenli_goster(uretilen)
    print("İşlem tamamlandı.")
    print(os.environ.get("ORNEK_AYAR", "hazır"))
