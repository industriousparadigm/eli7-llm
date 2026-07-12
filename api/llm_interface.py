from abc import ABC, abstractmethod
from typing import Dict
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server-side web search tool (see the claude-api skill: web_search_20260209 is the
# current variant with dynamic filtering, supported on Sonnet 5). Capped at 3 uses
# per turn to bound latency/cost - Nuvem should look things up occasionally, not
# reflexively.
WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 3,
}


class LLMInterface(ABC):
    @abstractmethod
    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, object]:
        pass


class AnthropicLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-5"

    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, object]:
        messages = history if history else []
        messages.append({"role": "user", "content": user})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=[WEB_SEARCH_TOOL],
            )

            # Only "text" blocks ever reach the child - this naturally excludes
            # server_tool_use / web_search_tool_result blocks (and citations, which
            # are a separate structured field on the block, never inline markup).
            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            )

            searched = any(
                getattr(block, "type", None) == "server_tool_use"
                and getattr(block, "name", None) == "web_search"
                for block in response.content
            )

            # Never hand the child an empty bubble (can happen if extended thinking
            # eats the whole token budget and no text block comes back).
            if not text.strip():
                text = "Hmm, a Nuvem baralhou-se um bocadinho! 🌥️ Podes perguntar outra vez?"

            return {"text": text, "searched": searched}

        except Exception as e:
            print(f"Anthropic API error: {e}")
            return {
                "text": "I love answering questions! Can you try asking that in a different way?",
                "searched": False,
            }


def get_llm_backend() -> LLMInterface:
    """Get the LLM backend - now only Anthropic"""
    return AnthropicLLM()
