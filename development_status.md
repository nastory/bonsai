# Development Status

Last updated: 2026-08-05

This is a snapshot of what's built versus what's next. For the *why* behind any of it, see `bonsai_prd.md` (product requirements, with a full Milestones section per phase). For the *how*, see `design.md` (a build-slice-by-build-slice technical narrative covering everything below in far more detail, plus a Roadmap section for what's not built yet).

## At a glance

| Phase | Status |
|---|---|
| Phase 0 — UI Mockup | Done |
| Phase 1 — Core Loop | Done |
| Phase 2 — Rich Media & Continuity | Done |
| Phase 3 — Polish | Not started |

## Phase 0: UI Mockup — done

The full frontend, navigable end to end against static TypeScript fixtures. No real backend logic beyond a health check.

## Phase 1: Core Loop — done

The real backend stood up end to end against a live Ollama instance, with every response schema-validated so a malformed model response fails clearly instead of corrupting data:

- LLM-driven course creation: a free-text conversational interview shapes a course outline, which the learner can revise before approving.
- Real document upload (`.txt`/`.docx`/`.pdf`), with extracted text (later: chunked and embedded) grounding both the interview and the outline.
- Incremental, lazy per-module lesson generation, sequential per-activity for continuity, with retrieval-grounded citations.
- Quiz/assessment feedback wired to real generation, feedback-only per the product's no-grading stance.
- Mid-course direction changes: Branch Off (a new course, linked to its parent) and Change This Course (in place, only modules ahead change).
- Data export/import (a full JSON+content-files archive, secrets excluded).
- Partway through the phase, retrieval was reworked from a model-driven tool-use loop into a deterministic chunk-and-embed-and-retrieve RAG pipeline, shared by uploaded documents and web search, with citations attached in code from the chunks actually retrieved rather than authored by the model.

## Phase 2: Rich Media & Continuity — done

Every item on this phase's list shipped, including BYOM refinement:

- **Course thumbnail image generation.** A new independently-configurable image-generation model role (mirroring the embedding-model role) generates a real thumbnail on outline approval. Only OpenAI/Azure are actually supported (confirmed via the installed LiteLLM version); an unconfigured or failing model just keeps the gradient placeholder.
- **In-course visual aids for reading activities.** A retrieval-based mechanism, not generation: an LLM pass over a finished reading flags where a real image would clarify a concept, Tavily image search retrieves candidates, and the best match is inlined into the lesson.
- **"Keep going / dive deeper / branch off" from a completed course.** Finishing a course's last activity surfaces a "Keep going" entry point that reuses the same Branch Off mechanism.
- **Learning Objectives.** An optional standing weekly activity-count goal, tracked via activity-completion timestamps and computed live on the Today dashboard.
- **Opt-in web-search supplementing for document-grounded courses.** A document-grounded course can opt in to also drawing on web search, rather than the document being the only source.
- **Video embedding.** A real YouTube `<iframe>` embed as its own standalone module activity, best-effort once per module: a Tavily search (restricted to youtube.com/youtu.be, terms tailored to the module's actual content) surfaces a few candidates, a model picks the best match and writes a caption, and the video slots into whichever position in the module's activity order fits its content, not a fixed slot. See `docs/process_flows.md` for a diagram of exactly where this fits into module generation.
- **BYOM local-model refinement.** Not a single deliverable but a running set of real reliability fixes found and fixed via live verification against local Ollama models: routing BYOM calls through Ollama's `ollama_chat/` prefix instead of a buggy one, schema-constrained decoding (plus a lesson that schema validators' conditional requirements aren't enforced by the decoder, only a field's own required-ness), an explicit context-window size, a real litellm Ollama-embeddings bug worked around, and an interview prompt redesigned around a fixed topic checklist to reduce repeat-questioning on weaker local models.

## Phase 3: Polish — not started

Per `bonsai_prd.md`, not yet scoped in any detail:

- Settings refinements.
- Semantic search over the course index (using the embedding model already in place for retrieval).
- AI evals — rubric-based LLM grading of interview-question helpfulness, search-result relevance, and lesson/activity quality (moved here from Phase 2 scope).
- Community/contribution readiness.

## Current build health

- 344 backend tests passing (`cd backend && pytest`), frontend `tsc --noEmit`/`npm run build` both clean.
- Migration head: `3233479dcbab`.
- Every feature above has been verified against a real live Ollama instance and, where relevant, a real Tavily key or hosted provider, not just the mocked test suite — this project's standing verification bar throughout both phases.
