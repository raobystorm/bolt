import json
import os
import aiohttp


async def call_openai(json_body: dict) -> str:
    api_key: str = os.environ["OPENAI_API_KEY"]
    headers = {
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.openai.com/v1/chat/completions", headers=headers, json=json_body
        ) as response:
            return await response.text()


async def summary_article(text: str, lang: str):
    pass


async def translate_article(text: str, lang: str) -> str:
    body = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
        "max_tokens": 3000,
        "messages": [
            {
                "role": "system",
                "content": f"You're a translator who translate news article into {lang}. The proper nouns, especially names of people and companies in the summary should be in English and alphabetized form.",
            },
            {
                "role": "user",
                "content": f"Translate the news article into {lang} below: {text}",
            },
            {
                "role": "assistant",
                "content": f"Translated article of {lang}: ",
            }]}
    response = json.loads(await call_openai(body))
    return response['choices'][0]['message']['content'].strip()


async def summary_title(text: str, lang: str):
    pass
