- Long-output generation (outline especially, possibly sequential module
  activity generation too) can still fail against local/BYOM models under
  context-window/output-length pressure — an empty `{}` response or JSON
  truncated mid-object, distinct from the "conversational prose instead of
  JSON" bug fixed on 2026-08-03 (that one's resolved via `ollama_chat/` +
  JSON-mode `response_format`). Options if this proves common in practice:
  explicit `num_ctx`/`max_tokens` config in `app/services/llm.py`, or
  splitting outline generation into smaller calls. Currently accepted as a
  disclosed BYOM limitation, same as the module-generation rework's
  sequential-activity-generation truncation risk (`module_generation.py`
  docstring) — not fixed preemptively.
- Define, in one place, what each learning activity type (reading, quiz,
  essay, project, discussion, assessment) actually is and when/how often it
  should show up in a module — right now `course_outline.md` only says
  "3 to 6 activities... mix of guided readings, short written essays, guided
  discussions, checkbox quizzes, or hands-on projects... end with an
  assessment or capstone," with no real definition of what distinguishes,
  say, a "quiz" from an "assessment," or guidance on a sensible mix/cadence
  (e.g. how many readings before a check, how often a project vs. an essay
  makes sense for a given topic). Would inform both the outline-generation
  prompt and the PRD/design docs.
