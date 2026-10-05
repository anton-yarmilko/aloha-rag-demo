"""Minimal RAG retriever over a markdown knowledge base.

Splits every .md file in knowledge_base/ into sections (## headings)
and ranks them against a query with a simple TF-IDF-style score.
Synthetic demo data only - no proprietary content."""
from __future__ import annotations

import math
import re
from pathlib import Path

KB_DIR = Path(__file__).parent / "knowledge_base"

# A small, explicit English stop-word policy for this synthetic English KB.
STOP_WORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it of on "
    "or that the this to was what when where which with you your".split()
)


def _tokenize(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[^\W_]+", text.casefold()) if tok not in STOP_WORDS]


def load_sections() -> list[dict]:
    sections = []
    for md_file in sorted(KB_DIR.glob("*.md")):
        current = None
        for line in md_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if current and current["body"].strip():
                    sections.append(current)
                current = {"title": line[3:].strip(), "body": "", "source": md_file.name}
            elif current is not None:
                current["body"] += line + "\n"
        if current and current["body"].strip():
            sections.append(current)
    return sections


def search(query: str, sections: list[dict], top_k: int = 3) -> list[dict]:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return []
    n_docs = len(sections) or 1
    df: dict[str, int] = {}
    for sec in sections:
        for tok in set(_tokenize(sec["title"] + " " + sec["body"])):
            df[tok] = df.get(tok, 0) + 1
    scored = []
    for sec in sections:
        tokens = _tokenize(" ".join([sec["title"]] * 3) + " " + sec["body"])
        # Reject incidental overlap. This demo heuristic is not confidence.
        if len(q_tokens.intersection(tokens)) / len(q_tokens) < 0.5:
            continue
        score = sum(
            (tokens.count(tok) / len(tokens)) * math.log(n_docs / (1 + df.get(tok, 0)) + 1)
            for tok in q_tokens if tok in tokens
        )
        if score > 0:
            scored.append((score, sec))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(sec, score=round(score, 4)) for score, sec in scored[:top_k]]
