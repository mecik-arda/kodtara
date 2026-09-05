import openai

SISTEM = "Sen yardımcı bir asistansın."

sorgu = input("Soru: ")
prompt = SISTEM + "\nKullanıcı: " + sorgu
system_prompt = f"{SISTEM}\nKullanıcı girdisi: {sorgu}"

yanit = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
)

exec(yanit.choices[0].message.content)

import requests

requests.post("https://ornek-dis-sunucu.test/topla", json={"cikti": yanit.choices[0].message.content})

el.innerHTML = yanit.choices[0].message.content

print("API anahtarı sk-ORNEKANAHTAR1234567890 ile yanıt: " + yanit.choices[0].message.content)
