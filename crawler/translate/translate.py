import os

import openai


def get_translation(text: str, lang: str) -> str:
    openai.api_key = os.environ["OPENAI_API_KEY"]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You're a translator who translate news article into {lang}",
            },
            {"role": "user", "content": f"Translate the news article below: {text}"},
            {
                "role": "assistant",
                "content": f"Translation result of {lang}: ",
            },
        ],
        temperature=0,
        max_tokens=400,
    )

    return response["choices"][0]["message"]["content"]
