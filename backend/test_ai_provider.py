
from app.services.ai_provider import get_ai_provider


def main() -> None:
    provider = get_ai_provider()

    prompt = (
        "You are a browser copilot. "
        "Summarize this sample webpage in exactly 3 bullet points: "
        "A page explaining Python, its readability, libraries, "
        "and common uses in automation and web development."
    )

    print("Sending prompt to local Ollama model...")
    result = provider.generate(prompt)

    print("\nModel response:\n")
    print(result)


if __name__ == "__main__":
    main()
