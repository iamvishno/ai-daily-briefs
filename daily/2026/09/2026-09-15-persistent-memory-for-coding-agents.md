---
date: "2026-09-15"
topic: "New AI tools, models and platforms"
source: "Hugging Face"
source_url: "https://huggingface.co/blog/funes"
source_published: "2026-09-03"
automated: false
generation_mode: "curated-initial-entry"
---

# Persistent memory could make coding agents more useful across sessions

A recent Hugging Face article presents Funes, an open-source memory layer designed to help coding agents carry useful context between sessions. Instead of treating old agent traces as a large archive, the system turns them into a dataset that can be indexed, retrieved and connected back to its original evidence.

## Why this matters

Coding agents often begin a new session without knowing why an earlier technical decision was made. A searchable memory layer could reduce repeated investigation and make long-running work more consistent. The interesting engineering problem is not simply storing more text; it is deciding what to retrieve, when to retrieve it and how to preserve reliable provenance.

## My perspective

This connects closely with my interest in RAG, LlamaIndex and agent-based workflows. The same retrieval principles used to ground an answer in documents can also help an agent recover the reasoning behind earlier project decisions.

## What I want to explore next

I want to compare raw session history with structured, retrieval-based memory and examine how relevance, recency and source traceability affect an agent's decisions.

## A point to keep in mind

Persistent memory also creates privacy and safety questions. Incorrect or outdated reasoning can be retrieved alongside useful context, so deletion controls, user approval and clear source links remain important.

## Source

[Hugging Face: Give Your Coding Agents a Memory You Own](https://huggingface.co/blog/funes)

---

> This initial brief was carefully curated from the cited source. Personal project claims were not generated.
