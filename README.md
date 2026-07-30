# Bonsai

An open-source, locally-hosted, self-guided AI learning platform. See `docs/` for the product background (`bonsai_initial_idea.md`, `bonsai_prd.md`) and `design.md` for the current build's technical design.

## Motivation
I love continuous learning, but I get tired of having to search through sites like Udemy or Coursera looking for courses, not finding exactly what I need, and then paying for a course that only loosely lines up with what I actually want to learn.

While laying in bed after searching for a good course on practical GPU programming for ML/AI engineers and not having any luck, I decided to ask Claude for advice. Is GPU programming worth learning? Where would it be best for an ML engineer to focus? What technology and programming languages would be involved? And finally, can you draft a course outline for me?

The outline drafted was very good -- it had a great structured approach with modules, timelines, practicum, and even a capstone project; but again, only the outline. The question then became how would I have Claude actually go about creating this course for me in an engaging, practical, and motivating way. If I could figure that out, I could have it teach me anything.

Recently, I've been on a bonsai kick on TikTok. The meditative patience that goes into creating and maintaining these seemingly ancient trees in miniature is fascinating to me: wiring shoots and cutting limbs, cleaning roots, repotting -- all with patient goal of creating something beautiful. That's the experience I want from this learning platform: a self-guided, self-built program of learning where the student has the ability to reshape the curriculum as they go through AI. The fact that Bonsai has "AI" in its name is just a fun coincidence.

Nigel

**Status:** Phase 0 — a React front-end shell running against static fixture data, plus a minimal Flask backend skeleton. No real course generation, retrieval, or persistence yet; that's Phase 1.

## Prerequisites

- Node.js 20+ and npm (for `frontend/`)
- Python 3.10+ (for `backend/`)

## Project structure

```
bonsai/
├── docs/          # PRD, idea doc, mockup, feedback docs
├── design.md      # Phase 0 design document
├── frontend/      # React + TypeScript + Vite + Tailwind SPA
└── backend/       # Flask app skeleton (health check only, for now)
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
python run.py
```

The only endpoint right now is a health check:

```
curl http://localhost:5000/api/health
# {"status": "ok"}
```

The frontend doesn't call the backend yet in Phase 0 — everything renders from fixtures in `frontend/src/data/`.
