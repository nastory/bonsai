<h1><img src="frontend/src/assets/logo.svg" width="28" height="28" alt="Bonsai logo" align="center" /> Bonsai</h1>

An open-source, locally-hosted, self-guided AI learning platform for self-directed learning on any subject. See `docs/bonsai_initial_idea.md` for the product background, `bonsai_prd.md` for the full product requirements, and `design.md` for the current build's technical design.

**Status:** Phase 1 (in progress). Creating a course, running the interview, generating and revising an outline, and approving it are all real now, backed by the LLM (mocked in test mode), not a scripted Phase 0 flow, and generation actually respects whatever provider/model you've configured in Settings, hosted or a local Ollama model, verified against a real running Ollama instance. A module's actual lesson content (readings, quizzes, essays, discussions, projects) now generates the first time a learner reaches it, also verified against real Ollama. When a Tavily API key is configured, module generation routes through a retrieval agent that searches and fetches real web pages in an iterative loop before writing content, attaching citations to what it generates; built and fully tested against mocked calls, with live Tavily verification still pending. Completing a lesson activity persists too. Every LLM response is validated against an explicit schema before it touches the database, so a malformed model response fails clearly (a 502) instead of corrupting data or crashing with a confusing error. Settings covers hosted/BYOM model names, an embedding model (still unused, since semantic search isn't built), and the Tavily key. What's still ahead: changing direction mid-course, document ingestion, and AI evals (automated quality grading for generated content, see `design.md`'s Roadmap section).

## Motivation
I love continuous learning, but I get tired of having to search through sites like Udemy or Coursera looking for courses, not finding exactly what I need, and then paying for a course that only loosely lines up with what I actually want to learn.

While laying in bed after searching for a good course on practical GPU programming for ML/AI engineers and not having any luck, I decided to ask Claude for advice. Is GPU programming worth learning? Where would it be best for an ML engineer to focus? What technology and programming languages would be involved? And finally, can you draft a course outline for me?

The outline drafted was very good -- it had a great structured approach with modules, timelines, practicum, and even a capstone project; but again, only the outline. The question then became how would I have Claude actually go about creating this course for me in an engaging, practical, and motivating way. If I could figure that out, I could have it teach me anything.

Recently, I've been on a bonsai kick on TikTok. The meditative patience that goes into creating and maintaining these seemingly ancient trees in miniature is fascinating to me: wiring shoots and cutting limbs, cleaning roots, repotting -- all with patient goal of creating something beautiful. That's the experience I want from this learning platform: a self-guided, self-built program of learning where the student has the ability to reshape the curriculum as they go through AI. The fact that Bonsai has "AI" in its name is just a fun coincidence.

## Prerequisites

- Docker and Docker Compose (easiest way to run both servers together), **or**
- Node.js 20+ and npm (for `frontend/`) and Python 3.10+ (for `backend/`), to run them natively

## Project structure

```
bonsai/
├── docs/               # idea doc, mockup, feedback docs
├── bonsai_prd.md       # product requirements document
├── design.md           # design document (Phase 0, plus a Phase 1 section)
├── docker-compose.yml  # runs frontend + backend together, each in its own container
├── frontend/           # React + TypeScript + Vite + Tailwind SPA
│   └── Dockerfile
└── backend/            # Flask app: persistence, LiteLLM wrapper, REST routes
    ├── Dockerfile
    ├── app/
    │   ├── models.py            # Course, Module, Activity, SourceMaterial, UserSettings, ConversationMessage
    │   ├── prompts/              # LLM prompts as markdown files, kept out of code for clean versioning
    │   ├── services/
    │   │   ├── llm.py            # LiteLLM wrapper, mocked in test mode
    │   │   ├── llm_schemas.py    # Pydantic schemas validating LLM JSON output
    │   │   ├── model_selection.py    # UserSettings -> model/api_key/api_base for complete()
    │   │   ├── prompts.py        # loads app/prompts/*.md, fills in ${variables}
    │   │   ├── content_storage.py    # saves/loads an activity's generated content to/from disk
    │   │   ├── retrieval.py          # Tavily web search + page fetch, mocked in test mode
    │   │   ├── retrieval_agent.py    # search/fetch/evaluate tool-calling loop
    │   │   ├── course_generation.py  # interview -> outline -> approve
    │   │   └── module_generation.py  # generates a module's activities on demand, retrieval-grounded if a Tavily key is set
    │   └── routes/               # health, courses, settings, activities, course_creation, modules
    ├── migrations/          # Flask-Migrate / Alembic schema migrations
    └── tests/               # pytest suite
```

## Running with Docker Compose

The quickest way to get both servers running together:

```
docker compose up --build
```

This builds a container for each of `frontend/` and `backend/`, applies database migrations and seeds example courses automatically, and starts both dev servers with hot reload (your local `frontend/` and `backend/` directories are mounted into the containers, so code edits take effect immediately, same as running natively). Visit `http://localhost:5173` for the app; the backend is reachable at `http://localhost:5000`. `instance/bonsai.db` and generated module content land in `backend/instance/` on your host machine, same as running the backend natively, so your data survives `docker compose down`.

By default this makes real LiteLLM calls (a provider API key needs to be configured through Settings once the app is up). To run in test mode instead (mocked LLM calls, no API costs):

```
BONSAI_TEST_MODE=true docker compose up --build
```

Skip `--build` on subsequent runs unless you've changed a `Dockerfile` or a dependency file (`requirements.txt`, `package.json`).

## Running the frontend natively

```
cd frontend
npm install
npm run dev
```

Visit the URL Vite prints (defaults to `http://localhost:5173`).

## Running the backend natively

```
cd backend
python -m venv venv          # already created if you're continuing this session
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade             # creates instance/bonsai.db from the latest migration
python seed.py                # inserts example courses if the database is empty
python run.py
```

By default this makes real LiteLLM calls, which needs a provider API key configured (there's no Settings-to-backend wiring for that yet). To run without one, and avoid API costs entirely during development, use test mode instead, which returns canned responses for every LLM call while still using your real, persistent database:

```
BONSAI_TEST_MODE=true python run.py
```

Endpoints that exist now:

```
curl http://localhost:5000/api/health
# {"status": "ok"}

curl http://localhost:5000/api/courses
# [] (or the seeded example courses, if you ran seed.py)

curl http://localhost:5000/api/settings
# {"name": "Learner", "feedbackTone": "encouraging", ...}

curl -X POST http://localhost:5000/api/activities/<activity-id>/complete
# the full parent course, with that activity (and the next one it unlocks) updated

curl -X POST http://localhost:5000/api/courses -d '{"message": "I want to learn woodworking"}'
# {"courseId": "...", "done": false, "question": "..."}
# then POST .../interview-messages, .../generate-outline, .../outline-feedback, .../approve-outline

curl -X POST http://localhost:5000/api/modules/<module-id>/generate-activities
# the full parent course, with that module's activities generated (idempotent: a
# module that already has activities is returned unchanged)
```

## Running the backend tests

```
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -v
```

The suite always runs in test mode (mocked LLM calls, an in-memory database), so it never needs an API key or touches `instance/bonsai.db`.

## Backend database migrations

Schema changes go through Flask-Migrate:

```
cd backend
export FLASK_APP=run.py
flask db migrate -m "describe the change"
flask db upgrade
```

The frontend fetches courses and settings from the backend on load (see `frontend/src/lib/api.ts`), and creating a course through the app now runs the real interview -> outline -> approve flow. Run both servers together, with the backend seeded, to see it end to end. Reaching an in-progress module with no activities yet (e.g. a freshly-approved course, or one of the seeded example courses) triggers real lesson-content generation automatically; `CourseHome.tsx` shows "Generating..." until it lands.
