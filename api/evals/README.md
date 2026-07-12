# Eli7 answer-quality evals

A lean eval suite for Eli7's answer quality, modeled on the Brainwave eval philosophy:
a small fixed question set run through the real production path, graded by a ladder
of graders (cheapest first), with a readable report and a non-zero exit on failure.

No mocking, no reimplemented prompt logic. The runner imports and calls:

- `main.build_personalized_system_prompt()` - the exact system prompt `/ask` builds
  (today's date + Diana's name/gender/age from `settings.json`).
- `llm_interface.get_llm_backend().generate()` - the exact production Anthropic call.

## Run it

From `api/`:

```bash
.venv/bin/python -m evals.run
```

Makes real Anthropic API calls (generation + judge), so it costs a small amount of
money and takes roughly a minute for the default question set. Exit code is `0` if
every question passes, `1` otherwise.

## What it checks

Two graders, cheapest first:

1. **Deterministic (`checks.py`)** - no LLM call, instant: non-empty, detected
   language matches the question's language (`langdetect`), length in a sane band
   (not one line, not a wall of text), no markdown code fences, well-formed lists
   (no items crammed onto one line).
2. **LLM-as-judge (`judge.py`)** - one Claude call per question (a different, stronger
   model than the one being tested, to avoid self-grading bias), structured JSON
   output, one pass/fail + one-line reason per criterion: age-appropriate, warm tone,
   factually sound, correct language (specifically catches Brazilian vs European
   Portuguese - something `langdetect` can't tell apart), safe, reasonable length.

A question passes only if all deterministic checks pass AND the judge's
`overall_pass` is true.

**Category-aware rubric for hard topics:** for `category: "gently-unsafe"` cases
(death, bodies, scary/violent things), Eli7's protocol is to gently defer to a parent
first and only explain lightly if pressed - not deliver a full factual explanation
unprompted. The judge's `factually_sound` criterion swaps to a rubric that treats a
warm deferral-to-parent (with or without a brief, gentle explanation) as a pass, and
only fails on something factually wrong or invented. Other categories keep the
standard rubric.

## Add a case

Edit `questions.json` - it's a flat list of:

```json
{
  "id": "short-slug",
  "question": "The question text, in whichever language you want tested",
  "expected_language": "pt",
  "category": "science"
}
```

`expected_language` drives the deterministic language check and tells the judge
which language rule to apply (`pt` → must be European Portuguese, not Brazilian).
`category` is just a label for the report - no behavior hangs on its value.

**Grow this one real failure at a time.** If a real production answer breaks a rule
this suite doesn't check yet, add the check (or a rubric criterion) then - don't
pre-build coverage for hypothetical failures.
