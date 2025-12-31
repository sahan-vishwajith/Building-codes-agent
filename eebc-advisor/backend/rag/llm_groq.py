import os
from groq import Groq

class GroqLLM:
    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 800, top_p: float = 1.0):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY environment variable.")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

    def chat(self, system: str, user: str, **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
        )
        return (resp.choices[0].message.content or "").strip()
