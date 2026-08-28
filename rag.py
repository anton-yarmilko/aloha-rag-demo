"""Minimal RAG retriever over a markdown knowledge base.

Splits every .md file in knowledge_base/ into sections (## headings)
and ranks them against a query with a simple TF-IDF-style score.
Synthetic demo data only - no proprietary content."""
from __future__ import annotations

import math
import re
from pathlib import Path

KB_DIR = Path(__file__).parent / "knowledge_base"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def load_sections() -> list[dict]:
    sections = []
    for md_file in sorted(KB_DIR.glob("*.md")):
        current = {"title": md_file.stem, "body": "", "source": md_file.name}
        for line in md_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if current["body"].strip():
                    sections.append(current)
                current = {"title": line[3:].strip(), "body": "", "source": md_file.name}
            else:
                current["body"] += line + "\n"
        if current["body"].strip():
            sections.append(current)
    return sections


def search(query: str, sections: list[dict], top_k: int = 3) -> list[dict]:
    q_tokens = set(_tokenize(query))
    n_docs = len(sections) or 1
    df: dict[str, int] = {}
    for sec in sections:
        for tok in set(_tokenize(sec["title"] + " " + sec["body"])):
            df[tok] = df.get(tok, 0) + 1
    scored = []
    for sec in sections:
        tokens = _tokenize(sec["title"] * 3 + " " + sec["body"])
        score = sum(
            (tokens.count(tok) / len(tokens)) * math.log(n_docs / (1 + df.get(tok, 0)) + 1)
            for tok in q_tokens if tok in tokens
        )
        if score > 0:
            scored.append((score, sec))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(sec, score=round(score, 4)) for score, sec in scored[:top_k]]
