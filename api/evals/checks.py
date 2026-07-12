"""Deterministic (no-LLM) checks for Eli7 answers. Cheap and fast - run first."""

import re
from dataclasses import dataclass

import langdetect

MIN_WORDS = 8
MAX_WORDS = 220


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_non_empty(response: str) -> CheckResult:
    passed = bool(response.strip())
    return CheckResult("non_empty", passed, "ok" if passed else "response is empty")


def check_language_match(response: str, expected_language: str) -> CheckResult:
    if not response.strip():
        return CheckResult("language_match", False, "empty response")
    try:
        detected = langdetect.detect(response)
    except Exception as e:
        return CheckResult("language_match", False, f"langdetect error: {e}")
    passed = detected == expected_language
    return CheckResult(
        "language_match", passed, f"detected={detected} expected={expected_language}"
    )


def check_length_band(response: str) -> CheckResult:
    word_count = len(response.split())
    passed = MIN_WORDS <= word_count <= MAX_WORDS
    return CheckResult(
        "length_band", passed, f"{word_count} words (band: {MIN_WORDS}-{MAX_WORDS})"
    )


def check_no_code_fences(response: str) -> CheckResult:
    passed = "```" not in response
    return CheckResult("no_code_fences", passed, "ok" if passed else "contains ``` fence")


# Only "*" and "N." are checked for multiple-markers-crammed-on-one-line: a bare "-"
# is too easily a prose dash (e.g. "show up - yellow, orange") to tell apart from a
# bullet by regex alone, so it would false-positive on ordinary sentences.
_ASTERISK_MARKER_RE = re.compile(r'(?:^|\s)\*\s+\S')
_NUMBERED_MARKER_RE = re.compile(r'(?:^|\s)\d+\.\s+\S')
_EMPTY_MARKER_RE = re.compile(r'^\s*(?:[*\-]|\d+\.)\s*$')


def check_well_formed_lists(response: str) -> CheckResult:
    """If the response has a markdown list, each item should be on its own line."""
    issues = []
    for line in response.split("\n"):
        markers = len(_ASTERISK_MARKER_RE.findall(line)) + len(_NUMBERED_MARKER_RE.findall(line))
        if markers > 1:
            issues.append(f"multiple list markers on one line: {line.strip()!r}")
        if _EMPTY_MARKER_RE.match(line):
            issues.append(f"empty list item: {line.strip()!r}")
    passed = not issues
    return CheckResult("well_formed_lists", passed, "ok" if passed else "; ".join(issues))


def run_all(response: str, expected_language: str) -> list[CheckResult]:
    return [
        check_non_empty(response),
        check_language_match(response, expected_language),
        check_length_band(response),
        check_no_code_fences(response),
        check_well_formed_lists(response),
    ]
