import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "translate_prompt.md"


def _openrouter_client():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment or .env file.")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def llm_generate(user_prompt, target_language):
    client = _openrouter_client()
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "system",
                "content": (
                    "Act as a professional translator. Translate the user's input faithfully "
                    "into the requested target language. Preserve its meaning and tone, and "
                    "return only the translation."
                ),
            },
            {
                "role": "user",
                "content": f"Target language: {target_language}\n\nText:\n{user_prompt}",
            },
        ],
    )
    return response.choices[0].message.content


def translate_note(title, content, target_language):
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    client = _openrouter_client()
    response = client.chat.completions.create(
        model="openrouter/free",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "target_language": target_language,
                        "title": title,
                        "content": content,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )

    response_content = response.choices[0].message.content
    try:
        translated = json.loads(response_content)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("The translation response was not valid JSON.") from error

    if (
        not isinstance(translated, dict)
        or not isinstance(translated.get("title"), str)
        or not isinstance(translated.get("content"), str)
    ):
        raise ValueError("The translation response must contain string title and content fields.")

    return {"title": translated["title"], "content": translated["content"]}


def main():
    parser = argparse.ArgumentParser(description="Translate text using OpenRouter.")
    parser.add_argument("text", help="Text to translate")
    parser.add_argument("target_language", help="Language to translate the text into")
    args = parser.parse_args()

    print(llm_generate(args.text, args.target_language))


if __name__ == "__main__":
    main()