"""Ask the bank agent one question: python chat.py."""

from pathlib import Path

from dotenv import load_dotenv

from agent import run_agent


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    try:
        question = input("Ask the bank agent: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not question:
        print("No question entered.")
        return

    result = run_agent(question)
    print(result["final_answer"])


if __name__ == "__main__":
    main()
