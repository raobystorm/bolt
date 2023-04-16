import os
import openai
import tiktoken


tokenizer = tiktoken.get_encoding("p50k_base")


def get_title_translation(title: str, lang: str) -> str:
    openai.api_key = os.environ["OPENAI_API_KEY"]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You're a translator who translate news article title into {lang}. The proper nouns, especially names of people and companies in the summary should be in English and alphabetized form.",
            },
            {
                "role": "user",
                "content": f"Translate the news title into {lang} below: {title}",
            },
            {
                "role": "assistant",
                "content": f"Translated title of {lang}: ",
            },
        ],
        temperature=0,
        max_tokens=1000,
    )

    return response["choices"][0]["message"]["content"].strip()
