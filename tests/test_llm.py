"""Optional manual API smoke test; not executed by pytest collection."""

from openai import OpenAI
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    response = OpenAI().responses.create(
        model="gpt-5.6-luna",
        input="Explain what an AI agent is in exactly two sentences.",
    )
    print(response.output_text)
