import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.llm.base import LLMClient

load_dotenv()


class GeminiClient(LLMClient):

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
    ) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file (see .env.example)."
            )

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        return response.text