# Kid Tutor v2 - System Prompts for truly 7-year-old friendly responses

SYSTEM_PROMPT_V2 = """You're talking to a curious 7-year-old. Use simple, everyday words.

Keep your answer short and fun - like telling a little story.
Sometimes add an emoji or two to make things more fun! 🌟
Never use: formulas (H2O), technical terms, or teacher phrases.

CRITICAL formatting for lists:
When making ANY list, you MUST put each item on its OWN LINE like this:

* First item
* Second item  
* Third item

NEVER write lists inline like: * item1 * item2 * item3
ALWAYS use line breaks between list items.

If asked in Portuguese, answer in Portuguese (Portugal) using "tu"."""

# Rewrite instruction for post-processing
KID_REWRITE_PROMPT = """Rewrite this answer for a curious 7-year-old. Two short sentences only, simple everyday words, no formulas or lists, friendly image or tiny story. Keep the same language as the input. If a hard word remains, add (means: simple explanation). Do not add 'Want more?'"""

# Banlist of technical terms that should never appear
TECHNICAL_BANLIST = {
    'intersect', 'intersection', 'atmosphere', 'atmospheric', 'hydrides', 'hydride',
    'compound', 'compounds', 'molecule', 'molecules', 'molecular', 
    'react', 'reaction', 'reactions', 'approximate', 'approximately',
    'radius', 'quantum', 'algorithm', 'methane', 'hydrogen', 'oxygen',
    'element', 'elements', 'chemical', 'chemistry', 'formula', 'formulas',
    'viscosity', 'frequency', 'frequencies', 'laryngeal', 'vibration', 'vibrations',
    'electromagnetic', 'spectrum', 'wavelength', 'particles', 'electrons',
    'photosynthesis', 'synthesis', 'synthesize', 'degrees', 'angle', 'angles',
    'coefficient', 'density', 'mass', 'velocity', 'acceleration',
    'ch4', 'h2o', 'co2', 'o2', 'h2', 'ch3', 'nh3'  # Chemical formulas
}

# Filler phrases to remove
FILLER_PHRASES = [
    "good thinking",
    "great question", 
    "i can provide",
    "i can explain",
    "as an ai",
    "there are three types",
    "there are several types",
    "let me explain",
    "the answer is",
    "actually",
    "basically",
    "essentially",
    "furthermore",
    "however",
    "therefore",
    "in fact",
    "want more?",
    "would you like to know more"
]

# Simple word replacements
SIMPLE_REPLACEMENTS = {
    # Technical to simple
    'atmosphere': 'air around earth',
    'intersect': 'meet',
    'approximately': 'about',
    'reflect': 'bounce',
    'refract': 'bend',
    'particles': 'tiny bits',
    'molecules': 'tiny pieces',
    'vibration': 'shaking',
    'frequency': 'speed',
    'scatter': 'bounce around',
    'water vapor': 'water in the air',
    'evaporate': 'turn into mist',
    'condensation': 'water drops forming',
    'precipitation': 'rain or snow',
    
    # Portuguese (PT-PT) specific
    'você': 'tu',
    'banheiro': 'casa de banho',
    'trem': 'comboio',
    'ônibus': 'autocarro',
    'sorvete': 'gelado',
}