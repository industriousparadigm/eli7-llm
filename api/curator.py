"""The curator: decides what durably matters about Diana and commits it to her
memory repo. Fired after every /ask as a non-blocking background task, and by
/begin-new-topic as a synchronous consolidation pass.

This is the taste-heavy half of the memory system - memory_repo.py just owns the
repo's plumbing. A curation pass never raises: a bad Claude call, a git hiccup, or
a missing repo must never surface to Diana. Errors are logged and swallowed.
"""

import asyncio
import logging
import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import BaseModel

import memory_repo as memory

load_dotenv()

logger = logging.getLogger("curator")

# Mirror new curator commits to Supabase for the auditor dashboard. Best-effort:
# if unimportable, telemetry_push stays None and the push below is just skipped.
try:
    from telemetry import push as telemetry_push
except ImportError:
    telemetry_push = None

# Same model the production answers use (llm_interface.AnthropicLLM) - curation
# fires on every single exchange, so it should cost roughly what one answer costs,
# not more.
CURATOR_MODEL = "claude-sonnet-5"

# Serializes curator runs so an /ask curation and a /begin-new-topic curation
# firing close together can't race on reading/writing the same docs.
_lock = asyncio.Lock()

ROUTINE_INSTRUCTION = (
    "This is a routine pass after ONE exchange. Update recent.md briefly if the "
    "current thread shifted (a sentence or two - what she's curious about right "
    "now). Only touch memory.md or people.md if something clearly durable came up."
)

TOPIC_BOUNDARY_INSTRUCTION = (
    "Diana just started a NEW topic - the previous thread is ending. This is the "
    "moment to consolidate: if recent.md holds anything durable, fold it into "
    "memory.md or people.md, then shrink recent.md back down - it should no "
    "longer carry the old thread. A short note or empty is fine. Do not invent a "
    "new recent.md topic if no fresh transcript was given."
)

CURATOR_PROMPT = """You maintain the memory files for Eli7, a kid-safe AI terminal that \
Diana (8 years old, Portugal) talks to. These files get re-injected into EVERY future \
answer Eli7 gives her, so they must stay small, accurate, and true.

Your guiding objective for behavioral curation: our mission with Diana is to help her \
grow well - to learn, to wonder, and to have a good time - never to just please her in \
the moment. She is a CHILD, not a typical AI user. When you judge whether a behavioral \
change to about-diana.md is "better", better means it serves her growth, learning, \
wellbeing, and healthy age-appropriate challenge - NOT whatever maximizes her momentary \
delight or approval. A note that says "keep answers short because she disengages from \
long ones" is fine (it serves her attention and learning); a note that says "always \
agree with her" or "avoid ever challenging her" would work against the mission and must \
never be written. Diana is also going to keep growing up - part of your job over time is \
to notice when her current vocabulary, complexity, or challenge level looks like it's \
falling behind her age (too easy, no longer stretching her) and capture that as a note in \
"## O que funciona com a Diana", so Eli7's protected-core instruction to grow with her \
stays grounded in how she's actually maturing, not just her age in years.

--- about-diana.md (identity + behavior - see structure below) ---
{about_md}

--- memory.md (durable facts learned over time) ---
{memory_md}

--- people.md (her people: family, friends, pets, teachers) ---
{people_md}

--- recent.md (short rolling summary of what's current - decays fast, NOT a log) ---
{recent_md}

New exchange(s) since the last curation pass:
{transcript}

{mode_instruction}

--- about-diana.md structure and guardrails (read carefully - this file drives EVERY \
future answer, and mistakes here are the highest-blast-radius mistake you can make) ---
about-diana.md has two parts, marked in the file itself:
1. A PROTECTED CORE, from the top of the file down to the line "<!-- FIM DO NÚCLEO \
PROTEGIDO -->". This holds her fixed identity, tone rules, and safety/sensitivity \
rules (e.g. never badmouth family/friends unprompted, how to hold the Camila pressure \
and the Vovô Paulo discomfort). This also now carries the mission statement above.
2. An evolving section titled "## O que funciona com a Diana", after that marker. This \
is where you accumulate learned BEHAVIORAL notes: her communication style, what \
delights her, what confuses or frustrates her, the answer length/tone that land, \
topics that light her up, new sensitivities you observe.
If you return about_diana_md at all, you MUST include the ENTIRE protected core \
copied VERBATIM, character-for-character, exactly as given to you above - never \
remove, shorten, reword, reorder, or soften anything in it, and never weaken or drop a \
safety or sensitivity rule, even to make room, even if it seems redundant. You may ONLY \
add to or refine the "## O que funciona com a Diana" section that follows it. If you \
are not touching about-diana.md, leave about_diana_md null - do not return it just to \
re-paste the core unchanged.
Only propose an about-diana.md change on a REAL, REPEATED signal about how to be with \
her better - e.g. the same pattern shows up more than once across the exchange(s) \
given to you, or clearly confirms/sharpens a note already sitting in "## O que funciona \
com a Diana". NEVER propose one from a single ambiguous turn (one short reply, one \
so-so reaction) - that is noise, not a pattern. When in doubt, leave it null.

Rules - have taste:
- Only write memory.md or people.md if something DURABLE and CLEARLY STATED came up. \
Never invent or over-infer - a friend mentioned once in passing isn't durable; "my \
friend Sofia sits next to me at school" is a person worth keeping.
- If Diana mentions a person not yet in people.md - a friend, relative, teacher, or \
pet - add them: name plus how they relate to her, in her own words where possible. \
Watch for name collisions with people already listed (e.g. her mum is Mariana, a \
school friend is also named Mariana) - keep them clearly distinct, never merge them.
- If a new fact updates or contradicts an old one, REPLACE the old one - never keep both.
- Keep every file tight: memory.md and people.md read like a handful of bullet points, \
not a diary. recent.md is one short paragraph, not a transcript. Within "## O que \
funciona com a Diana", replace-and-distill an existing note when a new observation \
sharpens it - never let notes pile up side by side.
- If nothing durable changed for a file, leave that field null - never touch a file just \
to touch it.
- Return FULL replacement content for any file you change, not a diff or an append.
- Everything is written in European Portuguese (PT-PT).

Return the new content for any file that needs to change (null if unchanged), and a \
short one-line "reason" describing what changed, for the commit log."""


class CuratorUpdate(BaseModel):
    about_diana_md: str | None = None
    memory_md: str | None = None
    people_md: str | None = None
    recent_md: str | None = None
    reason: str


async def _run_curator(transcript: str, mode_instruction: str) -> None:
    async with _lock:
        try:
            memory.ensure_memory_repo()

            prompt = CURATOR_PROMPT.format(
                about_md=memory.read_doc(memory.ABOUT_FILE) or "(vazio)",
                memory_md=memory.read_doc(memory.MEMORY_FILE) or "(vazio)",
                people_md=memory.read_doc(memory.PEOPLE_FILE) or "(vazio)",
                recent_md=memory.read_doc(memory.RECENT_FILE) or "(vazio)",
                transcript=transcript,
                mode_instruction=mode_instruction,
            )

            client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            result = await client.messages.parse(
                model=CURATOR_MODEL,
                # 1500 -> 6000: about_diana_md can now return the full protected
                # core (~3200 chars, incl. the mission statement, homework and
                # grow-with-her rules, short-answers rule, and hard-topics
                # protocol - see memory_repo.ABOUT_SEED) plus the evolving
                # section, on top of memory/people/recent all changing in the
                # same pass - this was truncating the JSON output mid-string
                # at 1500/3000. max_tokens is just a ceiling, not a cost floor -
                # billing is for tokens actually generated, so headroom here
                # is free.
                max_tokens=6000,
                messages=[{"role": "user", "content": prompt}],
                output_format=CuratorUpdate,
            )
            update = result.parsed_output

            changed = []
            if update.about_diana_md is not None:
                memory.write_doc(memory.ABOUT_FILE, update.about_diana_md)
                changed.append(memory.ABOUT_FILE)
            if update.memory_md is not None:
                memory.write_doc(memory.MEMORY_FILE, update.memory_md)
                changed.append(memory.MEMORY_FILE)
            if update.people_md is not None:
                memory.write_doc(memory.PEOPLE_FILE, update.people_md)
                changed.append(memory.PEOPLE_FILE)
            if update.recent_md is not None:
                memory.write_doc(memory.RECENT_FILE, update.recent_md)
                changed.append(memory.RECENT_FILE)

            if changed:
                committed = memory.commit_all(f"curator: {update.reason} ({', '.join(changed)})")
                logger.info("curator updated %s: %s", ", ".join(changed), update.reason)

                # Push the new commit to Supabase right away so the auditor
                # dashboard doesn't lag. Guarded on top of push_curator_events
                # already being exception-safe - a telemetry hiccup here must
                # never surface as a curation failure.
                if committed and telemetry_push:
                    try:
                        await asyncio.to_thread(
                            telemetry_push.push_curator_events, memory.get_memory_dir()
                        )
                    except Exception:
                        logger.exception("telemetry: push_curator_events failed (curation itself succeeded)")
            else:
                logger.info("curator: nothing durable this pass (%s)", update.reason)

        except Exception:
            logger.exception("curator pass failed - memory repo left untouched")


async def curate_exchange(question: str, response: str) -> None:
    """Curate a single Q&A exchange. Fired as a background task after every /ask."""
    transcript = f"Diana: {question}\nEli7: {response}"
    await _run_curator(transcript, ROUTINE_INSTRUCTION)


async def curate_topic_boundary(transcript: str | None = None) -> None:
    """Consolidation pass when Diana starts a new topic. Called synchronously by
    /begin-new-topic - not fired-and-forgotten, since the endpoint reports back
    once it's actually done."""
    await _run_curator(
        transcript or "(sem trocas novas - consolida apenas com o recent.md atual)",
        TOPIC_BOUNDARY_INSTRUCTION,
    )
