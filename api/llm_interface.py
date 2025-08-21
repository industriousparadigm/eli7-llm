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
        # Using Claude Sonnet 4 for best instruction following
        self.model = "claude-3-5-sonnet-20241022"  # This is the model ID for Sonnet 4
    
    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, str]:
        try:
            # Build messages with history
            messages = history if history else []
            messages.append({"role": "user", "content": user})
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages
            )
            
            # Extract text from response
            text = response.content[0].text if response.content else ""
            
            return {"text": text}
            
        except Exception as e:
            print(f"Anthropic API error: {e}")
            # Fallback response
            return {
                "text": "I love answering questions! Can you try asking that in a different way?"
            }


def get_llm_backend() -> LLMInterface:
    """Get the LLM backend - now only Anthropic"""
    return AnthropicLLM()