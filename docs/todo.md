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
