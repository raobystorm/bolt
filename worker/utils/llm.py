import json
import os
import aiohttp


async def _call_openai(json_body: dict) -> str:
    api_key: str = os.environ["OPENAI_API_KEY"]
    headers = {
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_body,
        ) as response:
            json_resp = json.loads(await response.text())
            return json_resp["choices"][0]["message"]["content"].strip()


async def summarize_article(text: str, lang: str, use_gpt4: bool = False) -> str:
    body = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": f"You're a news editor summarize news article into {lang}. The proper nouns, especially names of people and companies in the summary should be in English and alphabetized form.",
            },
            {
                "role": "user",
                "content": f"Summarize the news article in {lang} in several sentences. The article is below: {text}",
            },
            {
                "role": "assistant",
                "content": f"Summary of the article in {lang} in several sentences: ",
            },
        ],
    }
    if use_gpt4:
        body["model"] = "gpt-4"
    return await _call_openai(body)


async def translate_article(text: str, lang: str, use_gpt4: bool = False) -> str:
    body = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
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
                "content": f"Translated the article in {lang}: ",
            },
        ],
    }
    if use_gpt4:
        body["model"] = "gpt-4"
    return await _call_openai(body)


async def summarize_title(text: str, lang: str, use_gpt4: bool = False):
    body = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": f"You're a news editor summarize news article into one title in {lang}. The proper nouns, especially names of people and companies in the summary should be in English and alphabetized form.",
            },
            {
                "role": "user",
                "content": f"Summarize the news article into a one-sentence title in {lang} below: {text}",
            },
            {
                "role": "assistant",
                "content": f"Summarize the article into a one-sentence title of {lang}: ",
            },
        ],
    }
    if use_gpt4:
        body["model"] = "gpt-4"
    return await _call_openai(body)


async def translate_title(title: str, lang: str):
    body = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": f"You're a translator who translates news title into {lang}. The proper nouns, especially names of people and companies in the summary should be in English and alphabetized form.",
            },
            {
                "role": "user",
                "content": f"Translate the news title into {lang} below: {title}",
            },
            {
                "role": "assistant",
                "content": f"Translated title in {lang}: ",
            },
        ],
    }
    return await _call_openai(body)
