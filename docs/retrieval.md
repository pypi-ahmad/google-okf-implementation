# Retrieval Design

## Objective

Provide robust enterprise retrieval that works for both:

- semantic questions ("Explain Orders API dependencies")
- structured lookup questions ("Show schema columns for orders table")

## Retrieval Components

- Vector retrieval: semantic similarity from embeddings + Chroma.
- Lexical retrieval: BM25 over local OKF text.
- Graph retrieval: relation propagation from seed concepts.
- Structured boosts: type-aware signals for APIs, metrics, tables, datasets, playbooks, glossary.

## Router Modes

- `auto`: infer best mode from question intent
- `vector`: prioritize semantic similarity
- `keyword`: prioritize lexical/BM25 match
- `graph`: prioritize dependency traversal
- `hybrid`: weighted ensemble

## Ranking and Traceability

Each result includes:

- final rank score
- per-signal breakdown (`semantic`, `keyword`, `graph`, `structured`)
- explanation trace

This makes retrieval behavior inspectable for debugging and evaluation.

## Graph Expansion

When API concepts are retrieved, graph traversal can expand context to linked:

- datasets
- metrics
- tables

This reduces missing-context failure modes common in raw vector-only RAG.

## Evaluation Metrics

Retrieval evaluation utilities support:

- `recall@k`
- `MRR`
- `answer_support` (evidence phrase coverage)

These metrics are implemented in `enterprise_okf_ai.retrieval` and used in notebook and tests.
