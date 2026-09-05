const systemPrompt = `Sen yardımcı bir asistansın. Kullanıcı: ${userInput}`;

const yanit = await llm.invoke([{ role: "user", content: userInput }]);

document.body.innerHTML = yanit;

eval(yanit);
