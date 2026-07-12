"""Regenerates the starter-question suggestion pool for Eli7's welcome screen.

Reads Diana's memory repo (about-diana.md + memory.md + people.md + recent.md)
and asks Claude for ~60 fresh, topic-tagged PT-PT questions weighted to her
current interests, mixed with broad variety across many topics so the pool
never feels thematically clustered. Those are then MERGED with the baseline
pool (pool.json, ~150 questions) - deduped - into one big (~200) servable
pool, written to generated_pool.json (the pool /suggestions serves first,
see main.py).

Run every 6h via cron.sh (crontab line in README.md). Idempotent - safe to
run any number of times, each run overwrites generated_pool.json whole from a
fresh read of the memory repo and the baseline pool.

Degrades to the baseline pool (pool.json) by doing nothing: on any failure -
missing/unreadable memory repo, API error, a too-small result - this leaves
generated_pool.json untouched, and /suggestions falls back to whatever's
already there (or pool.json alone, if generated_pool.json has never been
written).
"""

import asyncio
import json
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import BaseModel

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
import memory_repo as memory  # noqa: E402

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("suggestions.generate")

# Same tier as curator.py - this runs a few times a day, not per exchange, so
# there's headroom to spend a bit more without it mattering cost-wise.
GENERATE_MODEL = "claude-sonnet-5"
POOL_SIZE = 60  # how many NEW questions to generate this run
MIN_ACCEPTABLE_SIZE = 24  # below this, treat the result as broken and keep the old pool

# Closed set of topics - keeps the merged pool groupable so the UI can pick 3
# chips from 3 different topics every time. Must match the tags used in
# pool.json. Any topic Claude returns outside this set gets coerced to "fun"
# rather than aborting the whole run over one bad tag.
ALLOWED_TOPICS = [
    "space", "animals", "body", "nature", "weather", "ocean", "feelings",
    "tech", "fun", "art", "music", "food", "history", "dinosaurs", "maths",
]

SUGGESTIONS_DIR = Path(__file__).resolve().parent
BASELINE_POOL_FILE = SUGGESTIONS_DIR / "pool.json"
GENERATED_POOL_FILE = SUGGESTIONS_DIR / "generated_pool.json"

PROMPT = """Estás a gerar perguntas novas para o pool de sugestões ("chips") do \
ecrã de boas-vindas do Eli7, um terminal de IA seguro para crianças. Quem o usa é \
a Diana (8 anos, Portugal).

--- about-diana.md (quem ela é) ---
{about_md}

--- memory.md (factos duradouros aprendidos sobre ela) ---
{memory_md}

--- people.md (as pessoas da vida dela) ---
{people_md}

--- recent.md (o que a tem interessado agora mesmo) ---
{recent_md}

O pool já tem estas perguntas - não repitas nenhuma, nem quase-repetições da \
mesma ideia com outras palavras:
{baseline_questions}

Gera {pool_size} perguntas NOVAS, em português de Portugal, no estilo destas \
(curtas, curiosas, terminadas num emoji):
- "Porque é que os gatos ronronam? 🐱"
- "Como funcionam os arco-íris? 🌈"
- "O que faz os trovões? ⛈️"

Cada pergunta tem de vir com um "topic" escolhido exatamente de entre esta \
lista fechada: {allowed_topics}.

Regras:
- À volta de 60% das perguntas deve ser AMPLA e variada, espalhada pelos \
temas da lista acima - nunca concentrada só num ou dois temas.
- O resto (à volta de 40%) deve pesar para os interesses REAIS da Diana, \
lidos acima (ex: matemática/contas, pintura, o jogo Mario Wonder, a Rosalina \
e as Lumas, o irmão Oscar). Espalha esses 40% pelos VÁRIOS interesses dela - \
no máximo 3 perguntas sobre o mesmo interesse específico (ex: no máximo 3 \
sobre Rosalina/Lumas, no máximo 3 sobre matemática) para não ficar tudo \
parecido. Nunca inventes interesses que não estejam nos ficheiros - sem \
factos duradouros ou tema atual, fica só na variedade ampla.
- Cada pergunta é uma frase curta, terminada num emoji, tom caloroso e \
curioso, adequada a uma criança de 8 anos. Nunca temas assustadores, \
violentos, tristes de mais, ou inadequados.
- Nunca repitas a mesma pergunta duas vezes, nem repitas (com outras \
palavras) nenhuma pergunta já listada acima.
- Devolve exatamente {pool_size} perguntas, todas diferentes entre si e do \
pool já existente."""


class GeneratedQuestion(BaseModel):
    text: str
    topic: str


class QuestionPool(BaseModel):
    questions: list[GeneratedQuestion]


def _normalize_key(text: str) -> str:
    """Accent/emoji/punctuation/case-insensitive key, used to dedupe
    near-identical questions when merging pools."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _load_baseline() -> list[dict]:
    try:
        data = json.loads(BASELINE_POOL_FILE.read_text(encoding="utf-8"))
        return [
            {"text": q["text"], "topic": q.get("topic") or "fun"}
            for q in (data.get("questions") or [])
            if isinstance(q, dict) and q.get("text")
        ]
    except Exception:
        logger.exception("failed to read baseline pool %s", BASELINE_POOL_FILE)
        return []


async def generate_pool(baseline: list[dict]) -> list[dict] | None:
    """Returns the fresh (deduped, topic-tagged) NEW questions, or None if
    generation failed/degraded and the existing pool should be left alone."""
    try:
        memory.ensure_memory_repo()
        about_md = memory.read_doc(memory.ABOUT_FILE)
        memory_md = memory.read_doc(memory.MEMORY_FILE)
        people_md = memory.read_doc(memory.PEOPLE_FILE)
        recent_md = memory.read_doc(memory.RECENT_FILE)

        baseline_questions = "\n".join(f"- {q['text']}" for q in baseline) or "(vazio)"

        prompt = PROMPT.format(
            about_md=about_md or "(vazio)",
            memory_md=memory_md or "(vazio)",
            people_md=people_md or "(vazio)",
            recent_md=recent_md or "(vazio)",
            baseline_questions=baseline_questions,
            pool_size=POOL_SIZE,
            allowed_topics=", ".join(ALLOWED_TOPICS),
        )

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        result = await client.messages.parse(
            model=GENERATE_MODEL,
            max_tokens=8000,
            # This is a straightforward structured-list generation, not a task
            # that benefits from extended reasoning - and leaving thinking on
            # its default was silently spending the entire max_tokens budget
            # on a ThinkingBlock, hitting stop_reason=max_tokens with zero
            # actual output (parsed_output=None). Disabling it fixes that.
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
            output_format=QuestionPool,
        )

        questions = []
        for q in result.parsed_output.questions:
            text = q.text.strip()
            if not text:
                continue
            topic = (q.topic or "").strip().lower()
            if topic not in ALLOWED_TOPICS:
                topic = "fun"
            questions.append({"text": text, "topic": topic})

        if len(questions) < MIN_ACCEPTABLE_SIZE:
            logger.warning(
                "generated pool too small (%d questions) - keeping existing pool",
                len(questions),
            )
            return None

        return questions

    except Exception:
        logger.exception("suggestion generation failed - leaving pool untouched")
        return None


def merge_pools(baseline: list[dict], generated: list[dict]) -> list[dict]:
    """Baseline ∪ generated, deduped by normalized text. Baseline first so a
    generated question that happens to collide with a baseline one is
    dropped in favor of the (already-reviewed) baseline wording."""
    seen: set[str] = set()
    merged: list[dict] = []
    for item in (*baseline, *generated):
        key = _normalize_key(item["text"])
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append({"text": item["text"], "topic": item.get("topic") or "fun"})
    return merged


async def main() -> None:
    baseline = _load_baseline()
    generated = await generate_pool(baseline)
    if generated is None:
        logger.info("no pool written this run")
        return

    merged = merge_pools(baseline, generated)
    GENERATED_POOL_FILE.write_text(
        json.dumps({"questions": merged}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "wrote %d questions (%d baseline + %d new generated, deduped) to %s",
        len(merged), len(baseline), len(generated), GENERATED_POOL_FILE,
    )


if __name__ == "__main__":
    asyncio.run(main())
