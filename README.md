<h1><img src="frontend/src/assets/logo.svg" width="28" height="28" alt="Bonsai logo" align="center" /> Bonsai</h1>

An open-source, locally-hosted, self-guided AI learning platform for self-directed learning on any subject. See `docs/bonsai_initial_idea.md` for the product background, `bonsai_prd.md` for the full product requirements, and `design.md` for the current build's technical design.

**Status:** Phase 1 (in progress). Creating a course, running the interview, generating and revising an outline, and approving it are all real now, backed by the LLM (mocked in test mode), not a scripted Phase 0 flow. Completing a lesson activity persists too. Every LLM response is validated against an explicit schema before it touches the database, so a malformed model response fails clearly (a 502) instead of corrupting data or crashing with a confusing error. The backend has a real test suite, a LiteLLM wrapper, prompts kept as separate versionable markdown files, a per-course conversation history, and REST routes over all of it. What's still ahead: generating a module's actual lesson content when the learner reaches it, changing direction mid-course, document ingestion, and the retrieval agent.

## Motivation
I love continuous learning, but I get tired of having to search through sites like Udemy or Coursera looking for courses, not finding exactly what I need, and then paying for a course that only loosely lines up with what I actually want to learn.

While laying in bed after searching for a good course on practical GPU programming for ML/AI engineers and not having any luck, I decided to ask Claude for advice. Is GPU programming worth learning? Where would it be best for an ML engineer to focus? What technology and programming languages would be involved? And finally, can you draft a course outline for me?

The outline drafted was very good -- it had a great structured approach with modules, timelines, practicum, and even a capstone project; but again, only the outline. The question then became how would I have Claude actually go about creating this course for me in an engaging, practical, and motivating way. If I could figure that out, I could have it teach me anything.

Recently, I've been on a bonsai kick on TikTok. The meditative patience that goes into creating and maintaining these seemingly ancient trees in miniature is fascinating to me: wiring shoots and cutting limbs, cleaning roots, repotting -- all with patient goal of creating something beautiful. That's the experience I want from this learning platform: a self-guided, self-built program of learning where the student has the ability to reshape the curriculum as they go through AI. The fact that Bonsai has "AI" in its name is just a fun coincidence.

## Prerequisites

- Node.js 20+ and npm (for `frontend/`)
- Python 3.10+ (for `backend/`)

## Project structure

```
bonsai/
├── docs/          # idea doc, mockup, feedback docs
├── bonsai_prd.md  # product requirements document
├── design.md      # design document (Phase 0, plus a Phase 1 section)
├── frontend/      # React + TypeScript + Vite + Tailwind SPA
└── backend/       # Flask app: persistence, LiteLLM wrapper, REST routes
    ├── app/
    │   ├── models.py            # Course, Module, Activity, SourceMaterial, UserSettings, ConversationMessage
    │   ├── prompts/              # LLM prompts as markdown files, kept out of code for clean versioning
    │   ├── services/
    │   │   ├── llm.py            # LiteLLM wrapper, mocked in test mode
    │   │   ├── llm_schemas.py    # Pydantic schemas validating LLM JSON output
    │   │   ├── prompts.py        # loads app/prompts/*.md, fills in ${variables}
    │   │   └── course_generation.py  # interview -> outline -> approve
    │   └── routes/               # health, courses, settings, activities, course_creation
    ├── migrations/          # Flask-Migrate / Alembic schema migrations
    └── tests/               # pytest suite
```

## Running the frontend

```
cd frontend
npm install
npm run dev
```

Visit the URL Vite prints (defaults to `http://localhost:5173`).

## Running the backend

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

The frontend fetches courses and settings from the backend on load (see `frontend/src/lib/api.ts`), and creating a course through the app now runs the real interview -> outline -> approve flow. Run both servers together, with the backend seeded, to see it end to end. A newly-created course's modules won't have real lesson content yet: generating a module's activities when the learner reaches it isn't built.
