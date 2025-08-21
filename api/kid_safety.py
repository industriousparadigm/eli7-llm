import re
from typing import Tuple, List
from prompts import TECHNICAL_BANLIST, FILLER_PHRASES, SIMPLE_REPLACEMENTS, KID_REWRITE_PROMPT
import langdetect


def detect_language(text: str) -> str:
    """Detect the language of the text."""
    try:
        lang = langdetect.detect(text)
        # Check for Portuguese variant
        if lang == 'pt':
            # Look for PT-PT specific words
            pt_pt_markers = ['tu', 'torneira', 'autocarro', 'comboio', 'miúdo']
            if any(marker in text.lower() for marker in pt_pt_markers):
                return 'pt-PT'
            return 'pt'
        return lang
    except:
        return 'en'


def needs_rewrite(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text needs kid-friendly rewrite.
    Returns (needs_rewrite, list_of_issues)
    """
    issues = []
    
    # Check 1: Way too many sentences (only flag if excessive)
    sentences = re.split(r'[.!?]+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) > 8:  # Only flag if really long
        issues.append(f"Too many sentences: {len(sentences)} > 8")
    
    # Check 2: Chemical formulas or technical notation
    # More specific pattern for chemical formulas (H2O, CH4, CO2, etc)
    if re.search(r'\b[A-Z][a-z]?\d+\b|\b[A-Z]{2,}\d*\b', text):  # Matches H2O, CH4, CO2, etc
        issues.append("Contains chemical formula")
    
    if re.search(r'\d+\s*°|degrees?', text, re.IGNORECASE):
        issues.append("Contains degree notation")
    
    # Check 3: Technical banlist words
    text_lower = text.lower()
    found_banned = [word for word in TECHNICAL_BANLIST if word in text_lower]
    if found_banned:
        issues.append(f"Contains banned words: {', '.join(found_banned[:3])}")
    
    # Check 4: Average sentence length > 12 words
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_words > 12:
            issues.append(f"Sentences too long: avg {avg_words:.1f} words")
    
    # Check 5: Filler phrases
    for filler in FILLER_PHRASES:
        if filler in text_lower:
            issues.append(f"Contains filler: '{filler}'")
            break
    
    # Check 6: "Want more?" in text
    if "want more" in text_lower or "want to know more" in text_lower:
        issues.append("Contains 'Want more?' (UI handles this)")
    
    return len(issues) > 0, issues


def clean_response(text: str) -> str:
    """
    Minimal cleanup - only remove obvious filler phrases and "Want more?".
    Avoid deterministic word replacement that could break sentences.
    """
    result = text
    
    # Only remove the most egregious filler phrases that never belong
    egregious_fillers = [
        "good thinking",
        "great question",
        "boa pergunta",  # Portuguese
        "as an ai",
        "let me explain",
        "actually,",
        "basically,",
        "there are three types",
        "there are several types"
    ]
    
    for filler in egregious_fillers:
        # Remove with punctuation and following space
        pattern = re.escape(filler) + r'[.!?]?\s*'
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Remove "Want more?" since UI handles this
    result = re.sub(r'Want\s+(to\s+know\s+)?more\??\.?', '', result, flags=re.IGNORECASE)
    
    # Clean up extra spaces BUT PRESERVE NEWLINES!
    # Only collapse multiple spaces (not newlines) into single space
    result = re.sub(r'[ \t]+', ' ', result)  # Collapse multiple spaces/tabs
    result = re.sub(r'^\s*[,.]\s*', '', result)  # Remove leading punctuation
    
    return result.strip()


def truncate_to_two_sentences(text: str) -> str:
    """
    Hard truncate to first two sentences.
    """
    sentences = re.split(r'([.!?]+)', text.strip())
    result = []
    sentence_count = 0
    
    for i in range(0, len(sentences), 2):
        if sentence_count >= 2:
            break
        if i < len(sentences) and sentences[i].strip():
            result.append(sentences[i])
            if i + 1 < len(sentences):
                result.append(sentences[i + 1])
            sentence_count += 1
    
    return ''.join(result).strip()


def enforce_kid_safety(text: str, language: str = None) -> Tuple[str, bool]:
    """
    MINIMAL cleanup only - NO TRUNCATION.
    Claude is smart enough to handle kid-appropriate responses via system prompt.
    Returns (cleaned_text, was_modified)
    """
    if not text:
        return text, False
    
    # Just do minimal cleanup of obvious filler phrases
    cleaned = clean_response(text)
    
    # Return cleaned text, mark as modified if we removed any filler
    return cleaned, text != cleaned


def format_for_language(text: str, language: str) -> str:
    """
    Apply language-specific formatting.
    """
    if language == 'pt-PT':
        # Portuguese (Portugal) specific replacements
        pt_pt_replacements = {
            'você': 'tu',
            'vocês': 'vocês',  # Keep vocês for plural
            'banheiro': 'casa de banho',
            'trem': 'comboio',
            'ônibus': 'autocarro',
            'sorvete': 'gelado',
            'criança': 'miúdo',
            'crianças': 'miúdos',
        }
        
        result = text
        for br_word, pt_word in pt_pt_replacements.items():
            result = re.sub(r'\b' + br_word + r'\b', pt_word, result, flags=re.IGNORECASE)
        
        return result
    
    return text