"""Explicitly invoked, single-request API smoke test; pytest never calls it."""
import os


def main():
    from dotenv import load_dotenv
    from model_client import OpenAIModelClient
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("SKIP: OPENAI_API_KEY is unavailable")
        return
    try:
        response = OpenAIModelClient().generate(
            [{"input": "Say that this is a fake banking prototype. Do not call tools."}], [])
        assert response.final_answer
        print("PASS: one API request returned a final answer")
    except Exception as exc:
        print(f"FAIL: smoke request failed ({type(exc).__name__}); no retry attempted")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
