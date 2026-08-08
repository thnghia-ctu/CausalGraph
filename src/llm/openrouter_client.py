import os

from dotenv import load_dotenv
from openai import OpenAI

from src.llm.base import LLMClient

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient(LLMClient):

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 8000,
    ) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to your .env file (see .env.example)."
            )

        self._client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            extra_body={"reasoning": {"effort": "none"}},
        )

        choice = response.choices[0]
        content = choice.message.content

        if not content:
            raise RuntimeError(
                f"OpenRouter ({self._model}) trả về content rỗng. "
                f"finish_reason={choice.finish_reason!r}, raw_message={choice.message!r}"
            )

        return content
