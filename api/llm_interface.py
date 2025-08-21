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
        # Using Claude Sonnet 4 - the latest and most advanced Sonnet model
        self.model = "claude-sonnet-4-20250514"
    
    async def generate(self, system: str, user: str, history: list = None, max_tokens: int = 150, temperature: float = 0.7) -> Dict[str, str]:
        try:
            # Build messages with history
            messages = history if history else []
            messages.append({"role": "user", "content": user})
            
            # DEBUG: Log what we're sending
            print(f"\n=== DEBUG: Anthropic API REQUEST ===")
            print(f"Model: {self.model}")
            print(f"Max tokens: {max_tokens}")
            print(f"Temperature: {temperature}")
            print(f"System prompt length: {len(system)}")
            print(f"User message: {user[:100]}...")
            print(f"History messages: {len(messages) - 1}")
            print(f"=====================================\n")
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages
            )
            
            # DEBUG: Log the COMPLETE API response object
            import json
            print(f"\n=== DEBUG: COMPLETE Anthropic API Response ===")
            print(f"Response type: {type(response)}")
            
            # Show ALL attributes of the response object
            print(f"\nResponse attributes: {dir(response)}")
            
            # Show the actual response data
            print(f"\nResponse.id: {response.id}")
            print(f"Response.type: {response.type}")
            print(f"Response.role: {response.role}")
            print(f"Response.model: {response.model}")
            print(f"Response.stop_reason: {response.stop_reason}")
            print(f"Response.stop_sequence: {response.stop_sequence}")
            print(f"Response.usage: {response.usage}")
            
            # Show content details
            print(f"\nResponse.content: {response.content}")
            print(f"Number of content blocks: {len(response.content)}")
            
            if response.content:
                for i, block in enumerate(response.content):
                    print(f"\nContent block {i}:")
                    print(f"  Type: {block.type}")
                    print(f"  Text length: {len(block.text)}")
                    print(f"  Text (first 200 chars): {block.text[:200]}...")
                    print(f"  Text (last 200 chars): ...{block.text[-200:]}")
                    print(f"  FULL TEXT:\n{block.text}")
            
            print(f"================================================\n")
            
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