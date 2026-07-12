from abc import ABC, abstractmethod
from typing import Dict
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMInterface(ABC):
    @abstractmethod
    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, str]:
        pass


class AnthropicLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-5"

    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, str]:
        messages = history if history else []
        messages.append({"role": "user", "content": user})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )

            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            )

            return {"text": text}

        except Exception as e:
            print(f"Anthropic API error: {e}")
            return {
                "text": "I love answering questions! Can you try asking that in a different way?"
            }


def get_llm_backend() -> LLMInterface:
    """Get the LLM backend - now only Anthropic"""
    return AnthropicLLM()
