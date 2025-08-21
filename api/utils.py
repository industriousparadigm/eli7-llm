import re
from typing import List, Tuple
from nanoid import generate


def generate_context_id() -> str:
    return generate(size=12)


def chunk_text(text: str, max_chunk_size: int = 200) -> List[str]:
    """Break text into chunks of approximately max_chunk_size characters."""
    text = text.strip()
    
    if not text:
        return []
    
    # Split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If single sentence is too long, break it by commas or spaces
        if len(sentence) > max_chunk_size:
            # Try to break by commas first
            parts = sentence.split(', ')
            for part in parts:
                if len(part) > max_chunk_size:
                    # Break by words as last resort
                    words = part.split()
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = word
                        else:
                            current_chunk += (" " + word if current_chunk else word)
                else:
                    if len(current_chunk) + len(part) + 2 > max_chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = part
                    else:
                        current_chunk += (", " + part if current_chunk else part)
        else:
            # Try to add sentence to current chunk
            if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
            else:
                current_chunk += (" " + sentence if current_chunk else sentence)
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def format_for_kid(text: str) -> str:
    """Apply kid-friendly formatting to text."""
    
    # First, replace complex words and phrases with simpler ones
    simple_replacements = {
        # Technical terms
        "intersect": "meet",
        "intersection": "meeting point",
        "approximately": "about",
        "degrees": "amount",
        "40 degrees": "halfway up",
        "42 degrees": "halfway up", 
        "angle": "tilt",
        "reflect": "bounce",
        "reflection": "bouncing",
        "refract": "bend",
        "refraction": "bending",
        "spectrum": "spread of colors",
        "phenomenon": "thing that happens",
        "natural phenomenon": "something nature does",
        "occur": "happen",
        "occurs": "happens",
        "particles": "tiny bits",
        "molecules": "tiny pieces",
        "vibration": "shaking",
        "vibrating": "shaking",
        "frequency": "speed",
        "low-frequency": "slow",
        "high-frequency": "fast",
        "communicate": "talk",
        "produce": "make",
        "produced": "made",
        "creates": "makes",
        "forming": "making",
        "appears": "shows up",
        "alternate": "take turns",
        "ice crystals": "tiny ice pieces",
        "water droplets": "tiny water drops",
        "sunlight": "light from the sun",
        "upper atmosphere": "high up in the sky",
        "atmosphere": "the air around Earth",
        
        # Simplify complex explanations
        "at an angle of": "tilted at",
        "reflects off": "bounces off",
        "passes through": "goes through",
        "interacts with": "meets",
        "consists of": "is made of",
        "as a result": "so",
        "due to": "because of",
        "in order to": "to",
        
        # Add friendly tone
        "The reason": "Here's why",
        "This is because": "That's because",
        "In fact": "Actually",
        "Therefore": "So",
        "However": "But",
    }
    
    result = text
    
    # Apply simple replacements
    for complex, simple in simple_replacements.items():
        result = re.sub(rf'\b{complex}\b', simple, result, flags=re.IGNORECASE)
    
    # Add explanations for remaining complex words
    complex_words = {
        "volcano": "volcano (means: mountain that shoots hot rock)",
        "photosynthesis": "photosynthesis (means: how plants make food)",
        "gravity": "gravity (means: what pulls things down)",
        "ecosystem": "ecosystem (means: animals and plants living together)",
        "energy": "energy (means: power to do things)",
        "oxygen": "oxygen (means: air we breathe)",
        "carbon dioxide": "carbon dioxide (means: air we breathe out)",
        "magma": "magma (means: melted rock)",
        "lava": "lava (means: hot melted rock)",
        "molten": "melted",
        "crust": "outer layer",
        "Earth's crust": "Earth's outer layer",
        "eruption": "explosion",
        "volcanic eruption": "volcano explosion",
    }
    
    for word, replacement in complex_words.items():
        result = re.sub(rf'\b{word}\b', replacement, result, flags=re.IGNORECASE)
    
    # Clean up any remaining technical language
    result = re.sub(r'\b\d+\s*degrees?\b', 'partway up', result, flags=re.IGNORECASE)
    result = re.sub(r'\bapproximately\s+\d+\b', 'about halfway', result, flags=re.IGNORECASE)
    
    # Make sentences more conversational
    if not result.endswith(("!", "?", "Want more?")):
        if "Want more?" not in result:
            result = result.rstrip(".") + "!"
    
    return result


def is_safe_topic(question: str) -> Tuple[bool, str]:
    """Check if topic is appropriate for kids."""
    # Simple denylist for inappropriate topics
    unsafe_keywords = [
        "violence", "death", "kill", "murder", "suicide",
        "drug", "alcohol", "cigarette", "smoke",
        "sex", "adult", "inappropriate"
    ]
    
    question_lower = question.lower()
    for keyword in unsafe_keywords:
        if keyword in question_lower:
            return False, "Let's ask an adult together about that."
    
    return True, ""


def count_tokens_approximate(text: str) -> int:
    """Approximate token count (roughly 4 chars per token)."""
    return len(text) // 4