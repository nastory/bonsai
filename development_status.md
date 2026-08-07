# Development Status

Last updated: 2026-08-07

This is a snapshot of what's built versus what's next. For the *why* behind any of it, see `bonsai_prd.md` (product requirements, with a full Milestones section per phase). For the *how*, see `design.md` (a build-slice-by-build-slice technical narrative covering everything below in far more detail, plus a Roadmap section for what's not built yet).

## At a glance

| Phase | Status |
|---|---|
| Phase 0 — UI Mockup | Done |
| Phase 1 — Core Loop | Done |
| Phase 2 — Rich Media & Continuity | Done |
| Phase 3 — Polish | Done (one item on hold) |

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

## Phase 3: Polish — done (one item on hold)

Per `bonsai_prd.md`'s Milestones, this phase is scoped down to two items: semantic search over the course index, and community/contribution readiness. Everything else once listed here (Settings refinements, AI evals) was explicitly dropped from scope rather than deferred — Settings refinements had already happened incidentally across earlier phases' work, and AI evals were dropped in favor of relying on human experience using the app instead of automated LLM-graded evals.

- **Semantic search over the course index — done, delivered as "Resources".** Three features grounded in a learner's own already-generated course content, reached from a new "Resources" nested nav item (replacing the old cross-course title-search "Library" page, dropped entirely):
  - **Flash Cards** and **Quiz Me** — pick a course and module, and an LLM generates a saved, reusable set of question/answer pairs (Flash Cards) or a standalone quiz (Quiz Me) grounded in that module's real generated content. Generated once, never regenerated.
  - **Ask Me Anything** — a chat scoped strictly to a learner's own course materials, not general knowledge. Each message runs through a four-step pipeline: an LLM rewrites the question into search-optimized terms (resolving conversational follow-ups via chat history), a classifier picks up to 3 courses whose material could plausibly help, each selected course's vector index is queried concurrently and merged, and a final answer is generated strictly from what was retrieved — declining if nothing relevant turns up. No persistence; the client resends its own transcript each turn.
  - Found and fixed a real, live-reproduced bug along the way: an already-existing course with a real uploaded document had no vector index at all (a lost-update race from an unrelated debugging session), so Ask Me Anything silently had zero coverage for it despite otherwise working correctly. Fixed with a new `backfill_vector_indexes.py` maintenance script that rebuilds a missing index from a course's already-extracted document text, no re-upload needed — confirmed the code path that indexes documents at upload time already works correctly for anything created going forward.
- **Reset Bonsai — done, not originally scoped, added on request.** A "Reset Bonsai" option in the user menu permanently deletes every course and all Settings (including API keys), leaving the installation exactly as it was on first install. The one irreversible action in the product, so it requires typing a confirmation word on top of a normal confirm dialog, and the server re-checks that confirmation itself rather than trusting the frontend alone.
- **LLM cost estimation — done.** A script (`estimate_costs.py`) drives real generation against a throwaway database, measures real per-call token usage, and extrapolates to an "average course" cost estimate across several reference hosted models — see the README's cost table.
- **Activity content definitions & cadence — done.** Closed the longest-standing open item on what each learning activity type is and how often it should appear (per the user-authored `docs/course_content_definitions.md`), which required two genuinely new pieces of functionality: quiz/assessment restructured from one question to a real multi-question list, and discussion activities reworked into a genuine multi-turn conversation (target 3, hard cap 5 exchanges) instead of a single-shot submit-and-feedback flow. Capstone also became a fully distinct activity type rather than a styling variant of "project".
- **First-time onboarding modal — done.** A one-time popup on first load walks through setting a username, model/embedding configuration (skippable), and a Tavily key (skippable).
- **Community/contribution readiness — on hold.** The one remaining Milestones line item; asked the user what it should concretely mean (contribution docs, repo/license polish, something else) and they chose to leave the roadmap as complete for now rather than scope it. Revisit if it comes up later.

## Current build health

- 475 backend tests passing (`cd backend && pytest`), frontend `tsc --noEmit`/`npm run build` both clean.
- Migration head: `cf828066c025`.
- Every feature above has been verified against a real live Ollama instance and, where relevant, a real Tavily key or hosted provider, not just the mocked test suite — this project's standing verification bar throughout every phase.
