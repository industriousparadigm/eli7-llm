"""Eval runner for Eli7 - Diana's kid-safe AI question terminal.

Runs a small fixed question set through the PRODUCTION path: the same
personalized system prompt main.py builds for /ask (build_personalized_system_prompt),
and the same AnthropicLLM.generate() call. Grades each answer with a ladder of
graders, cheapest first:

  1. Deterministic checks (checks.py) - non-empty, language match, length band,
     no code fences, well-formed lists. No LLM call, runs instantly.
  2. LLM-as-judge (judge.py) - one Claude call per question, structured output,
     for things only a model can assess: tone, factual soundness, PT-PT vs
     PT-BR, gentle handling of sensitive topics.

Run from api/:
    .venv/bin/python -m evals.run

Add a case: edit evals/questions.json. See evals/README.md.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from llm_interface import get_llm_backend
from main import build_personalized_system_prompt

from .checks import CheckResult, run_all as run_deterministic_checks
from .judge import JudgeVerdict, judge_response

QUESTIONS_FILE = Path(__file__).parent / "questions.json"


def load_questions() -> list[dict]:
    with open(QUESTIONS_FILE) as f:
        return json.load(f)


def print_check(result: CheckResult) -> None:
    mark = "✓" if result.passed else "✗"
    print(f"    {mark} {result.name}: {result.detail}")


def print_criterion(name: str, criterion) -> None:
    mark = "✓" if criterion.passed else "✗"
    print(f"    {mark} {name}: {criterion.reason}")


async def run_one(question: dict, system_prompt: str, llm) -> bool:
    """Run a single question through the production path and grade it. Returns pass/fail."""
    print(f"\n[{question['id']}] ({question['category']}) {question['question']!r}")

    result = await llm.generate(
        system=system_prompt,
        user=question["question"],
        history=[],
        max_tokens=int(os.getenv("MAX_TOKENS", 800)),
        temperature=float(os.getenv("TEMPERATURE", 0.7)),
    )
    response = result["text"].strip()
    print(f"  response: {response}")

    deterministic = run_deterministic_checks(response, question["expected_language"])
    print("  deterministic checks:")
    for r in deterministic:
        print_check(r)
    deterministic_passed = all(r.passed for r in deterministic)

    try:
        verdict = await judge_response(
            question["question"],
            response,
            question["expected_language"],
            question["category"],
        )
        print("  judge:")
        for field in JudgeVerdict.model_fields:
            if field == "overall_pass":
                continue
            print_criterion(field, getattr(verdict, field))
        judge_passed = verdict.overall_pass
    except Exception as e:
        print(f"  judge: ERROR - {e}")
        judge_passed = False

    passed = deterministic_passed and judge_passed
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}")
    return passed


async def main() -> int:
    questions = load_questions()
    system_prompt = build_personalized_system_prompt()
    llm = get_llm_backend()

    results = []
    for question in questions:
        passed = await run_one(question, system_prompt, llm)
        results.append((question["id"], passed))

    print("\n" + "=" * 60)
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    print(f"SUMMARY: {passed_count}/{total} passed")
    failed = [qid for qid, p in results if not p]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
    print("=" * 60)

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
