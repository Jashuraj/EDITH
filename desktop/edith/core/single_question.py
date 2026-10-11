"""Single-Question Protocol for EDITH.

Inspired by jarvis-omniroute core/single_question.py architecture.
Guarantees EDITH only asks at most one clarifying question at a time to prevent overwhelming the user.
"""

from __future__ import annotations

import re


def enforce_single_question(text: str) -> str:
    """Enforces that an assistant response contains at most one clarifying question mark.

    If multiple questions are present, preserves the primary question and converts
    or strips extraneous interrogatives.
    """
    if not text:
        return text

    q_count = text.count("?")
    if q_count <= 1:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    processed = []
    question_found = False

    for sentence in sentences:
        if "?" in sentence:
            if not question_found:
                processed.append(sentence)
                question_found = True
            else:
                # Convert secondary question to a declarative statement or truncate
                clean = sentence.replace("?", ".")
                words = clean.split()
                if len(words) > 3:
                    processed.append(clean)
        else:
            processed.append(sentence)

    result = " ".join(processed).strip()
    if result.count("?") > 1:
        first_q = result.find("?")
        result = result[:first_q + 1] + result[first_q + 1:].replace("?", ".")

    return result
