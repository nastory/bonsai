# Bonsai — Feedback on Initial Idea

## Context
Nigel drafted `docs/bonsai_initial_idea.md`, a concept for an open-source, locally-hosted, self-guided AI learning platform: users describe what they want to learn, an LLM (Claude) interviews them and generates a course outline, then generates modules on demand as the learner progresses, sourcing and synthesizing web materials along the way. The repo currently contains only this doc — no code, no architecture decisions yet. This request is for feedback on the idea plus a list of considerations that may have been missed, not an implementation plan. This document is meant to be read and discussed, not executed against.

## What's Strong
- The motivation is concrete and personal (a real gap: existing courses never match exactly what you want), which usually produces a sharper product than an abstract "wouldn't it be cool if" idea.
- The restrictions/disclaimers section (illegal content, medical/legal disclaimers, esoteric-topic honesty, religion/politics neutrality, no-accreditation, no-correctness-guarantee) is unusually mature for a first draft — most people skip this until later.
- The UX walkthrough (§5) is detailed enough to already reveal real product decisions: one-question-per-screen interview, max ~10 questions, revisable outline, per-module checkpoint with "change directions," "keep going"/"dive deeper"/"branch off" from completed courses.
- Recognizing the outline-vs-full-course gap (Claude gives a great outline but no execution) is the actual insight driving this — worth keeping front and center as the thing that differentiates Bonsai from "just ask Claude."

## Key Considerations Not Yet Addressed

### 1. Grounding and trust in generated content
The doc says materials should be "vetted and cited, with inline links," but doesn't yet specify *how*. Pure LLM generation from training data will hallucinate sources and go stale (especially for fast-moving topics like GPU programming). This effectively requires a retrieval step — real web search/fetch integrated into generation, not just prompting the model to "cite sources." This is probably the single biggest technical dependency in the whole idea and deserves an explicit architecture decision early.

### 2. Practical exercises need execution, not just text
For a topic like GPU programming, "practicum" and "exercises" implies runnable/gradable code, not just reading comprehension quizzes. That means some kind of sandboxed code execution environment. This is a substantial scope item that's easy to hand-wave in a first draft and expensive to bolt on later — worth deciding whether v1 supports it at all, or whether v1 exercises are limited to non-code formats (reading checks, short-answer, conceptual quizzes).

### 3. Skill vs. standalone app is a real fork, not a detail
The doc itself flags this tension (§2) and then moves past it, but it's actually a foundational architecture decision:
- **Claude Code skill**: fastest to prototype, but ties Bonsai to users who have Claude Code installed, and the front-end/skill boundary gets awkward (how does a skill "drop into" a web front-end?).
- **Standalone app with direct LLM API calls**: matches the "open-source, locally hosted" framing much better, works for any user with an API key, but is more build effort up front.
Recommend deciding this before writing any code, since it changes what "front-end" even means.

### 4. Course outline schema
§3 lists roughly what an outline and module should contain. Since the front-end, the module generator, and the "change directions" mid-course editing flow all depend on this shape, it's worth formalizing as an actual JSON schema early rather than letting it evolve implicitly — this becomes the contract between generation and rendering.

### 5. State and context management across sessions
Modules are generated incrementally over what could be a multi-week course. Each generation call needs enough context (prior modules, outline, learner's stated goals, any "change direction" feedback) to stay consistent without re-sending the entire course history every time. Worth planning a concrete strategy (structured state file + summarization, or a lightweight RAG-over-past-modules approach) rather than discovering the token-cost/consistency problem after the fact.

### 6. Non-linear editing ("change directions," branching, dependency graphs)
§3 mentions mapping dependencies so there are "no holes" in the curriculum, and §5 describes mid-course redirection and branching into new courses from a completed one. Combined, these imply outline versioning and a dependency graph that can be edited mid-flight without orphaning content. This is meaningfully more complex than a linear list of modules — worth explicitly scoping down for v1 (e.g., "changing direction regenerates all remaining modules linearly" instead of a true graph) unless the graph is a deliberate v1 goal.

### 7. Content moderation is a product requirement, not just a prompt
§4's restrictions list will partly come "through the LLM itself" per the doc, but for things like illegal content it's worth deciding whether Bonsai adds its own moderation/classification layer rather than relying solely on the underlying model's judgment — particularly since course topics are learner-generated and open-ended.

### 8. Legal exposure around sourced content
Synthesizing and redistributing web articles/video content, even locally and non-commercially, touches copyright and platform-ToS questions (e.g., YouTube embedding rules, fair-use boundaries for synthesized text). Worth at least a lightweight pass on this before building the sourcing pipeline, even for an OSS hobby project — and worth picking an actual OSS license for the repo itself.

### 9. Cost and API key handling
If Bonsai calls an LLM API directly, the user presumably brings their own key. Worth deciding early how costs are made visible/predictable (module generation + web retrieval + interview questions all cost tokens), and how keys are stored locally.

### 10. Scope for a true v1 / proof of concept
The current doc already spans: full front-end, conversational course-creation flow, web-sourced + cited materials, video embedding, dependency-mapped curriculum, and a moderation layer. That's a lot for "as basic as possible just to get something working." Recommend explicitly naming a minimal proof-of-concept slice — for example: single local user, text-only materials (no video embedding yet), linear (non-branching) outlines, no code-execution exercises, minimal citation via a single web-search tool call per module — and treating grounding/citation quality, code exercises, and non-linear editing as fast-follows rather than v1 requirements.

## Decisions Made (2026-07-29)
Responses to the considerations above, for reference going forward:
1. **Web search/retrieval** — confirmed required; to be designed in engineering.
2. **No in-app coding/execution environment** — Bonsai teaches any subject, not just code; learners use their own tools (same as woodworking needing your own wood/tools). Exercises for hands-on topics will need a submission + LLM-review format rather than auto-grading.
3. **Standalone app, not a Claude Code skill** — decided.
4. **Course outline schema** — deferred to engineering discussion.
5. **State/context/memory storage** — deferred to engineering discussion.
6. **No non-linear branching** — when a learner changes direction, the old module graph is deleted and the new fork replaces it. Simpler than versioned/branching graphs.
7. **Content moderation with no human review (locally-hosted)** — approach: rely on the first-party model provider's built-in safety as the default backstop; add a lightweight automated topic-level gate (classifier or heuristic) at course-creation time, independent of the generating model; for user-supplied/open-source local models, treat responsibility for outputs as shifting to the user (documented policy stance, not a technical guarantee) since a local uncensored model can't be forced to refuse.
8. **Sourced content is public data, used locally, not redistributed** — treated as no different from personal research via search engines; lower legal exposure than initially flagged since content isn't republished to other users.
9. **Cost** — to be measured via testing; app should also support open-source/local models, not just hosted APIs. Note: multi-provider support means the retrieval/generation interface (#1) needs to abstract over differing model capabilities (e.g., tool-use/web search support varies by provider).
10. **No fixed v1 scope yet** — still in broad product ideation, not ready to lock an MVP slice.

## Suggested Next Steps
1. Continue product ideation until ready to lock a v1 scope slice.
2. Once scope firms up, this is a good candidate for the `prd-builder` skill to turn into a formal PRD before implementation starts.
3. Open design thread to revisit later: finalize the local-model moderation policy language (#7) before public release, even if not before early prototyping.
