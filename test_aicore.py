"""Verify the configured AI Core deployment can complete a chat request."""

from ai_core import client, model_name


def main() -> None:
    response = client().chat.completions.create(
        model=model_name(),
        messages=[{"role": "user", "content": "Reply with exactly: AI Core works"}],
        max_tokens=16,
        temperature=0,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()