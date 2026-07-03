"""Embedding utility helpers for scaffold-level retrieval smoke workflows."""

from __future__ import annotations

import math


def deterministic_embedding(texts: list[str]) -> list[list[float]]:
    """Generate deterministic low-dimensional embeddings for local smoke use.

    This fallback is intended for development and scaffold verification only.
    Production deployments should use SentenceTransformers, OpenAI, or Ollama embeddings.
    """

    vectors: list[list[float]] = []
    for text in texts:
        cleaned = text or ""
        length = float(len(cleaned))
        alpha = float(sum(char.isalpha() for char in cleaned))
        numeric = float(sum(char.isdigit() for char in cleaned))
        whitespace = float(sum(char.isspace() for char in cleaned))
        unique = float(len(set(cleaned)))

        # Lightweight normalization to avoid dominating magnitudes.
        denom = max(length, 1.0)
        vector = [
            length / 1000.0,
            alpha / denom,
            numeric / denom,
            whitespace / denom,
            unique / 256.0,
            math.sin(length % 97),
            math.cos(alpha % 89),
            1.0,
        ]
        vectors.append(vector)

    return vectors
