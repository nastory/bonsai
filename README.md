<h1><img src="frontend/src/assets/logo.svg" width="28" height="28" alt="Bonsai logo" align="center" /> Bonsai</h1>

An open-source, locally-hosted, self-guided AI learning platform for self-directed learning on any subject. See `docs/bonsai_initial_idea.md` for the product background, `bonsai_prd.md` for the full product requirements, and `design.md` for the current build's technical design.

**Status:** Phase 1 (in progress). Phase 0's React front-end shell still runs entirely against static fixture data. The backend now has a real test suite, a LiteLLM wrapper (with a mocked test mode so development doesn't require an API key or incur cost), and a persistence layer for courses/modules/activities. Course creation, generation, retrieval, and the REST API connecting the frontend to any of this are still ahead.

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
└── backend/       # Flask app: health check, LiteLLM wrapper, course/module/activity persistence
    ├── app/
    │   ├── models.py       # Course, Module, Activity (SQLAlchemy)
    │   ├── services/llm.py # LiteLLM wrapper, mocked in test mode
    │   └── routes/
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
python run.py
```

By default this makes real LiteLLM calls, which needs a provider API key configured (not built yet; there's no Settings-to-backend wiring in this slice). To run without one, use test mode instead, which returns canned responses for every LLM call:

```
BONSAI_TEST_MODE=true python run.py
```

The only endpoint right now is a health check:

```
curl http://localhost:5000/api/health
# {"status": "ok"}
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

The frontend doesn't call the backend yet. Everything still renders from fixtures in `frontend/src/data/`, and wiring the two together is upcoming Phase 1 work.
