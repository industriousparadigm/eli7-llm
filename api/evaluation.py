#!/usr/bin/env python3
"""
Comprehensive evaluation system for kid-friendly responses.
Measures readability, complexity, safety, and engagement.
"""

import re
import statistics
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    """Metrics for evaluating response quality"""
    sentence_count: int
    avg_words_per_sentence: float
    max_words_in_sentence: int
    readability_score: float  # Flesch Reading Ease
    complex_word_count: int
    technical_terms_found: List[str]
    safety_issues: List[str]
    overall_score: float
    passed: bool


class ResponseEvaluator:
    """Evaluates responses for kid-friendliness"""
    
    # Simple words a 7-year-old should know (sample list)
    SIMPLE_WORDS = set([
        'cat', 'dog', 'water', 'rain', 'sun', 'moon', 'star', 'tree', 'flower',
        'happy', 'sad', 'big', 'small', 'hot', 'cold', 'fast', 'slow',
        'mom', 'dad', 'friend', 'play', 'run', 'jump', 'eat', 'sleep',
        'color', 'sound', 'light', 'dark', 'up', 'down', 'in', 'out'
    ])
    
    # Technical terms that should not appear
    TECHNICAL_TERMS = {
        'molecule', 'atom', 'frequency', 'vibration', 'chemical', 'formula',
        'compound', 'element', 'particle', 'wavelength', 'spectrum',
        'atmospheric', 'electromagnetic', 'synthesis', 'quantum',
        'algorithm', 'coefficient', 'density', 'velocity', 'acceleration'
    }
    
    # Banned phrases
    BANNED_PHRASES = [
        'let me explain', 'good thinking', 'actually', 'basically',
        'as an ai', 'i can provide', 'there are several types'
    ]
    
    def evaluate(self, response: str, question: str = "") -> EvaluationMetrics:
        """Evaluate a response for kid-friendliness"""
        
        # Clean the response
        response = response.strip()
        
        # Split into sentences
        sentences = self._split_sentences(response)
        sentence_count = len(sentences)
        
        # Calculate word metrics
        word_counts = [len(s.split()) for s in sentences]
        avg_words = statistics.mean(word_counts) if word_counts else 0
        max_words = max(word_counts) if word_counts else 0
        
        # Calculate readability (Flesch Reading Ease)
        readability = self._calculate_flesch_score(response)
        
        # Count complex words
        complex_count = self._count_complex_words(response)
        
        # Find technical terms
        technical_found = self._find_technical_terms(response)
        
        # Check safety issues
        safety_issues = self._check_safety(response)
        
        # Calculate overall score (0-100)
        overall_score = self._calculate_overall_score(
            sentence_count, avg_words, readability, 
            complex_count, technical_found, safety_issues
        )
        
        # Determine if response passes
        passed = (
            sentence_count <= 5 and  # Allow up to 5 sentences
            avg_words <= 15 and  # Allow slightly longer sentences
            readability >= 75 and  # Slightly more flexible readability
            len(technical_found) == 0 and
            len(safety_issues) == 0
        )
        
        return EvaluationMetrics(
            sentence_count=sentence_count,
            avg_words_per_sentence=round(avg_words, 1),
            max_words_in_sentence=max_words,
            readability_score=round(readability, 1),
            complex_word_count=complex_count,
            technical_terms_found=technical_found,
            safety_issues=safety_issues,
            overall_score=round(overall_score, 1),
            passed=passed
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_flesch_score(self, text: str) -> float:
        """
        Calculate Flesch Reading Ease score.
        90-100: Very easy (5th grade)
        80-90: Easy (6th grade) 
        70-80: Fairly easy (7th grade)
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return 100.0
        
        words = text.split()
        word_count = len(words)
        sentence_count = len(sentences)
        
        if word_count == 0:
            return 100.0
        
        # Count syllables (simplified)
        syllable_count = sum(self._count_syllables(word) for word in words)
        
        # Flesch Reading Ease formula
        if sentence_count > 0 and word_count > 0:
            score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
            return max(0, min(100, score))
        return 100.0
    
    def _count_syllables(self, word: str) -> int:
        """Simple syllable counter"""
        word = word.lower()
        vowels = 'aeiou'
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1
        
        # Ensure at least 1 syllable
        return max(1, syllable_count)
    
    def _count_complex_words(self, text: str) -> int:
        """Count words with 3+ syllables"""
        words = re.findall(r'\b\w+\b', text.lower())
        return sum(1 for word in words if self._count_syllables(word) >= 3)
    
    def _find_technical_terms(self, text: str) -> List[str]:
        """Find technical terms in the text"""
        text_lower = text.lower()
        found = []
        
        for term in self.TECHNICAL_TERMS:
            if term in text_lower:
                found.append(term)
        
        # Also check for chemical formulas
        if re.search(r'\b[A-Z][a-z]?\d+\b|\bH2O\b|\bCO2\b|\bO2\b', text):
            found.append("chemical_formula")
        
        # Check for degree notation
        if re.search(r'\d+\s*°|\d+\s+degrees?', text):
            found.append("degree_notation")
        
        return found
    
    def _check_safety(self, text: str) -> List[str]:
        """Check for safety issues"""
        issues = []
        text_lower = text.lower()
        
        # Check banned phrases
        for phrase in self.BANNED_PHRASES:
            if phrase in text_lower:
                issues.append(f"banned_phrase: {phrase}")
        
        # Check for inappropriate content patterns
        if re.search(r'death|die|kill|hurt|scary|monster', text_lower):
            issues.append("potentially_scary_content")
        
        return issues
    
    def _calculate_overall_score(self, sentence_count: int, avg_words: float,
                                readability: float, complex_count: int,
                                technical_found: List[str], safety_issues: List[str]) -> float:
        """Calculate overall score from 0-100"""
        score = 100.0
        
        # Sentence count penalty
        if sentence_count > 2:
            score -= (sentence_count - 2) * 20
        
        # Word count penalty
        if avg_words > 10:
            score -= min(30, (avg_words - 10) * 3)
        
        # Readability bonus/penalty
        if readability >= 90:
            score += 10
        elif readability < 80:
            score -= min(30, (80 - readability))
        
        # Complex words penalty
        score -= complex_count * 5
        
        # Technical terms penalty
        score -= len(technical_found) * 15
        
        # Safety issues penalty
        score -= len(safety_issues) * 20
        
        return max(0, min(100, score))


def evaluate_batch(responses: List[Tuple[str, str]]) -> Dict:
    """Evaluate a batch of question-response pairs"""
    evaluator = ResponseEvaluator()
    results = []
    
    for question, response in responses:
        metrics = evaluator.evaluate(response, question)
        results.append({
            'question': question,
            'response': response,
            'metrics': metrics
        })
    
    # Calculate aggregate stats
    passed_count = sum(1 for r in results if r['metrics'].passed)
    avg_score = statistics.mean(r['metrics'].overall_score for r in results)
    
    return {
        'results': results,
        'summary': {
            'total': len(results),
            'passed': passed_count,
            'pass_rate': round(passed_count / len(results) * 100, 1),
            'avg_score': round(avg_score, 1)
        }
    }


# Test questions for evaluation
TEST_QUESTIONS = [
    "Why do cats purr?",
    "How is water made?",
    "What is rain?",
    "Why is the sky blue?",
    "How do plants grow?",
    "Why do we have dreams?",
    "What makes thunder?",
    "How do birds fly?",
    "Why do leaves change color?",
    "Where do rainbows come from?"
]