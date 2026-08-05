# Bonsai — Phase 0 Design Document

Scope: Phase 0 only, per the PRD's milestone breakdown — a React front-end shell running against dummy/static data, plus a minimal Flask backend skeleton to establish the monorepo shape. No real generation, retrieval, or persistence logic yet; that's Phase 1. This doc will get a companion/update when Phase 1 design starts.

## 1. Overview
Bonsai's Phase 0 build is a navigable, visually-finished mockup of the full learning experience: browsing courses, running through the course-creation interview, reviewing a generated outline, working through a lesson, hitting different exercise types, getting a module-completion check-in, and configuring settings — all backed by static TypeScript fixtures instead of a real backend. Alongside it, a bare-bones Flask app is scaffolded in `backend/` so the repo has its final two-package shape from day one, even though it does nothing yet but respond to a health check.

## 2. Requirements summary
From the PRD and the approved mockup (`docs/bonsai_mockup.png`, `docs/bonsai_mockup_feedback.md`):
- Sidebar-driven SPA: Today (home), My Courses, Create Course, Library, Settings, matching the mockup's nav.
- Course creation is an **open-ended, free-text conversational interview** (not preset-option pills, per mockup feedback) — dynamically-phrased questions one per screen, capped around ten, ending in a generated outline the learner can revise or approve.
- Course → Modules → Learning Activities (readings, lessons, assessments/exercises) hierarchy, each module ending in an assessment or capstone/practicum.
- Module titles/descriptions are visible from the outline immediately; each module's actual activity content stays greyed out/locked until the learner reaches it and it "generates."
- On finishing a module, the learner is prompted for feedback, which (in the real product) shapes the next module; for Phase 0 this is a UI-only interaction.
- Exercises are feedback-only, never graded — need to represent the range described in the PRD: checkbox quiz, short essay, guided project submission+feedback, guided chat discussion.
- Table-of-contents panel, opened from the lesson header's list icon, showing all modules/activities with locked/current/completed states.
- Settings screen needs: model provider configuration placeholder (hosted vs. Bring-Your-Own-Model tiers), a thumbnail-generation toggle (added per mockup feedback, to save tokens), and a feedback-tone preference (encouraging vs. straightforward).
- Visual identity from the mockup: forest-green primary color, warm cream background, rounded white cards, sprout icon as the AI's avatar in chat, clean sans-serif type.
- Monorepo layout: `frontend/` and `backend/` side by side, `backend/` starting minimal now and filled in during Phase 1.
- **Added post-review:** the course-creation flow lets a learner attach one or more source documents instead of (or alongside) a typed topic; the same interview still runs to tailor teaching style regardless of source. Any course created this way keeps a "Source Materials" link back to the original file(s), separate from the web-sourced inline citations under Retrieval & Citation.
- **Added post-review:** clicking a course (from My Courses) lands on a course home page first, not directly into the current lesson. It shows overall progress, which module/activity the learner is currently on, and a collapsible module → activity list with completed/current/locked indicators, with a "Continue" action to jump into the current lesson.

## 3. Technology choices
- **Frontend build tool:** Vite + React + TypeScript. *(User's choice.)* No Next.js — this is a pure local SPA with no SSR needs.
- **Package manager:** npm. *(User's choice.)*
- **Styling:** Tailwind CSS with a custom theme (colors/fonts below), rather than a generic component library — the mockup has a distinct identity that a stock MUI/Chakra look would work against. *(Claude's choice, following from the mockup.)*
- **Icons:** `lucide-react` — matches the thin, rounded icon style in the mockup sidebar. *(Claude's choice.)*
- **Routing:** `react-router-dom`. *(Claude's choice — standard for a multi-screen SPA.)*
- **State for mock data:** a single React Context (`AppDataContext`) holding the fixture data and simple client-side mutations (e.g., marking a module complete). No Redux/Zustand — overkill for static fixtures. *(Claude's choice.)*
- **Backend:** Python 3.10 + Flask, app-factory pattern, `flask-cors` enabled for local Vite dev server access. *(Per PRD; Python 3.10 because that's what's installed locally — Phase 1 design can revisit the version pin if needed.)*
- **Design tokens (approximate, from the mockup image):**
  - Primary green: `#1B4332` (sidebar active state, primary buttons)
  - Hover/accent green: `#2D6A4F`
  - Background: `#FAF8F5` (warm cream)
  - Card surface: `#FFFFFF` with `#E8E4DC` border
  - Text primary: `#1F2421`, text secondary: `#6B7280`
  - Font: Inter (system-ui fallback stack)
  These are a starting point read off the mockup, not measured pixel values — expect minor tuning once screens are built.

## 4. Architecture

```
┌─────────────────────────────┐        ┌───────────────────────────┐
│         frontend/           │        │         backend/          │
│  Vite + React + TS SPA      │  HTTP  │  Flask app factory        │
│  (all data from local       │───────▶│  GET /api/health only     │
│   fixtures in Phase 0)      │        │  (not called by the app   │
└─────────────────────────────┘        │   yet — just scaffolded)  │
                                        └───────────────────────────┘
```

Frontend structure:
- `AppShell` renders the persistent sidebar + top-level `<Outlet>` for routed pages.
- `AppDataContext` wraps the app, exposing the fixture courses/user and a few local mutators (mark activity viewed, mark module complete, append interview answer) so screens feel interactive without a backend.
- Pages consume context + route params; no page fetches anything over HTTP in Phase 0.
- A shared `ActivityCard` component renders differently per activity `type` (reading, quiz, essay, project, discussion, assessment) — one component, type-driven rendering, rather than five near-duplicate components.

Backend structure:
- Minimal app factory (`create_app()`), CORS enabled, one blueprint (`health`) with `GET /api/health` returning `{"status": "ok"}`. Nothing else — this exists so the monorepo shape and run instructions are real from day one, not so Phase 0 depends on it.

## 5. Data model

TypeScript types (`frontend/src/types/course.ts`):

```typescript
export type ActivityType = 'reading' | 'video' | 'quiz' | 'essay' | 'project' | 'discussion' | 'assessment';
export type ActivityStatus = 'locked' | 'available' | 'completed';
export type ModuleStatus = 'locked' | 'in_progress' | 'completed';

export interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  status: ActivityStatus;
  estimatedMinutes?: number;
  // Rendered body varies by type — reading uses `body` (markdown-ish string with
  // inline citation markers), quiz uses `question`/`options`, essay/project use
  // `prompt`, discussion uses a seed `prompt` for the chat.
  body?: string;
  citations?: { label: string; url: string }[];
  question?: string;
  options?: string[];
  prompt?: string;
}

export interface Module {
  id: string;
  title: string;
  description: string;
  estimatedTimeline: string;
  status: ModuleStatus;
  learningOutcomes: string[];
  activities: Activity[];
}

export interface SourceMaterial {
  id: string;
  fileName: string;
  /** Blob URL for files attached this session; undefined for fixture-only examples with no real file behind them. */
  url?: string;
}

export interface Course {
  id: string;
  title: string;
  description: string;
  prerequisites: string[];
  estimatedTimeline: string;
  thumbnailUrl: string;
  progressPercent: number;
  modules: Module[];
  /** Present only for courses created from uploaded documents rather than a typed topic. */
  sourceMaterials?: SourceMaterial[];
}

export interface UserSettings {
  name: string;
  feedbackTone: 'encouraging' | 'straightforward';
  thumbnailGenerationEnabled: boolean;
  modelProvider: {
    tier: 'hosted' | 'byom';
    hostedProvider?: 'anthropic' | 'openai';
    apiKey?: string; // never persisted for real in Phase 0, just a form field
    byomEndpoint?: string;
  };
}
```

Fixture depth for Phase 0 (`frontend/src/data/mockCourses.ts`):
- **GPU Programming for ML Engineers** — the fully fleshed-out course, matching the mockup: 4 modules total, 2 built out with real-looking activities (readings with dummy citations, a quiz, an essay prompt, a discussion prompt, one capstone/practicum-style project), 2 later modules present as titles/descriptions only with `status: 'locked'` so the greyed-out behavior is visible. Also carries one `sourceMaterials` entry (a fixture-only example, no real `url`) to demonstrate the Source Materials display on an already-existing course.
- **Deep Learning Foundations** and **Data Structures & Algorithms** — list-level only (title, description, progress, thumbnail), matching the "My Courses" mockup card but not deep-linked into full lesson content. Keeps fixture-writing effort focused on proving the pattern once, thoroughly, rather than spreading thin across three courses.

## 6. Public interface

Routes (`frontend/src/App.tsx`):
- `/` (`Today`) — continue-learning card + "up next" preview, per mockup Screen 1.
- `/courses` (`MyCourses`) — list view, per mockup Screen 5.
- `/create` (`CreateCourse`) — open-ended conversational interview (chat-style, sprout avatar, free-text input, progress dots), replacing the mockup's preset pills per the feedback doc. Added post-review: a document-attach control (multiple files) alongside the initial free-text topic input — attaching files is optional and doesn't replace the interview that follows.
- `/create/review` (`OutlineReview`) — new screen, not in the original mockup: shows the generated outline (title, description, prerequisites, timeline, ordered module list) with "Ask for changes" (free-text) and "Start Learning" actions. Added post-review: when documents were attached, a Source Materials list renders in the outline card, carried over via router navigation state from `CreateCourse` (`File` objects aren't serializable to a URL, so they travel as React Router `location.state` rather than a route param).
- `/courses/:courseId` (`CourseHome`) — added post-review: this reverses an earlier decision (Section 6 originally had no bare course route, sending `CourseCard` straight to the current activity). A learner now lands here first when clicking a course from My Courses: overall progress, "currently on" module/activity with a Continue action, and a collapsible module → activity list with completed/current/locked indicators (a page-level counterpart to the `Lesson` route's slide-over table of contents, not a shared component with it — the collapse-by-default interaction differs enough, and `TableOfContents` is left as-is rather than reworked to match).
- `/courses/:courseId/modules/:moduleId/activities/:activityId` (`Lesson`) — the lesson/activity view, per mockup Screens 2–3, including the table-of-contents panel (triggered from the header list icon) and the `ActivityCard` for the current activity. Added post-review: a "Source Materials" header button (only rendered when `course.sourceMaterials` is non-empty) opens a `SourceMaterialsPanel` listing the course's attached documents — this gives real purpose to the mockup's "Resources" icon, which Section 6 originally dropped as undefined.
- `/settings` (`Settings`) — model provider config (hosted vs. BYOM), thumbnail-generation toggle, feedback-tone preference.
- `/about` (`About`), `/terms` (`Terms`), `/privacy` (`Privacy`), `/policy` (`UserPolicy`) — added post-review: static info pages reached from a dropdown menu on the sidebar's user-profile button (see below), rather than the static non-interactive button originally built.

A module-completion check-in (feedback prompt, with a "change direction" option) renders as a modal over the `Lesson` route when the last activity in a module is completed, rather than being its own route. The sidebar's user-profile button opens a `UserMenu` dropdown (About Bonsai, Terms of Service, Privacy Policy, User Policy, and an inline "Update username" action using the existing `updateUserSettings` mutator) rather than being a dead click target. Added post-review: an "Export My Data" action and an "Import User Data" action sit alongside the info links in that same dropdown, placeholders for the PRD's Data Export & Import requirement. Both now go through a shared two-step dialog pair (`ConfirmDialog` then `NoticeDialog`, in `components/layout/`) rather than an inline note: clicking either closes the dropdown and opens a `ConfirmDialog` explaining what the action will do, with Cancel/Confirm. Export's Confirm immediately shows a `NoticeDialog` acknowledging it isn't wired up yet. Import's Confirm (labeled "Choose File") triggers a real file picker (`accept=".zip"`); once a file is actually chosen, a `NoticeDialog` names it and gives the same "not wired up yet" acknowledgment. Neither does anything with the file — Phase 1 will.

Backend (`backend/app/routes/health.py`):
- `GET /api/health` → `200 {"status": "ok"}`. Only endpoint that exists in Phase 0.

## 7. Project layout

```
bonsai/
├── docs/                          # existing idea doc, feedback docs, mockup
├── bonsai_prd.md                  # moved out of docs/ to the project root
├── design.md
├── README.md
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                # router setup
│       ├── index.css              # Tailwind directives + theme tokens
│       ├── types/
│       │   └── course.ts
│       ├── data/
│       │   ├── mockCourses.ts
│       │   └── mockUser.ts
│       ├── context/
│       │   └── AppDataContext.tsx
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   ├── UserMenu.tsx        # dropdown from the profile button: info pages + inline username edit
│       │   │   ├── InfoPage.tsx        # shared layout for About/Terms/Privacy/UserPolicy
│       │   │   ├── ConfirmDialog.tsx   # added post-review: generic explain + Cancel/Confirm popup
│       │   │   └── NoticeDialog.tsx    # added post-review: generic acknowledgment popup with a Close button
│       │   ├── ui/                # themed primitives: Button, Card, Input, Toggle, ProgressBar, Badge
│       │   ├── course/
│       │   │   └── CourseCard.tsx
│       │   ├── lesson/
│       │   │   ├── TableOfContents.tsx
│       │   │   ├── ActivityCard.tsx
│       │   │   ├── ModuleCompletionModal.tsx
│       │   │   └── SourceMaterialsPanel.tsx  # added post-review: lists a course's uploaded documents
│       │   └── chat/
│       │       └── ChatBubble.tsx  # sprout-avatar chat bubble, used in Create Course
│       └── pages/
│           ├── Today.tsx
│           ├── MyCourses.tsx
│           ├── CourseHome.tsx      # added post-review: progress, current position, collapsible module/activity list
│           ├── CreateCourse.tsx
│           ├── OutlineReview.tsx
│           ├── Lesson.tsx
│           ├── Library.tsx          # added post-review: reconciles nav (Section 2) with routes (Section 6)
│           ├── Settings.tsx
│           ├── About.tsx           # added post-review: from UserMenu
│           ├── Terms.tsx           # added post-review: from UserMenu
│           ├── Privacy.tsx         # added post-review: from UserMenu
│           └── UserPolicy.tsx      # added post-review: from UserMenu
└── backend/
    ├── requirements.txt
    ├── run.py
    └── app/
        ├── __init__.py             # create_app(), CORS setup, blueprint registration
        └── routes/
            └── health.py
```

## 8. Implementation plan
1. Scaffold monorepo folders (`frontend/`, `backend/`) alongside existing `docs/`.
2. Hand-write the Vite + React + TS project files (`package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`) and Tailwind config with the theme tokens from Section 3.
3. Build themed UI primitives in `components/ui/` (Button, Card, Input, Toggle, ProgressBar, Badge) — these get reused by every page, build them first.
4. Define TypeScript types in `types/course.ts`.
5. Write fixture data in `data/mockCourses.ts` and `data/mockUser.ts` per the depth described in Section 5.
6. Build `AppDataContext` and wire it into `main.tsx`.
7. Build `AppShell` + `Sidebar`, matching the mockup's nav.
8. Build `Today` page.
9. Build `MyCourses` page + `CourseCard`.
10. Build `CreateCourse` page + `ChatBubble` (open-ended interview flow, free-text only).
11. Build `OutlineReview` page (new screen).
12. Build `TableOfContents` and `ActivityCard` (covering all six activity types), then the `Lesson` page that composes them, including the module-completion feedback modal.
13. Build `Settings` page.
14. Wire up `react-router-dom` in `App.tsx`; click through every nav path to confirm it's reachable.
15. Scaffold the Flask backend: app factory, CORS, `/api/health`, `requirements.txt`, `run.py`.
16. Write the root `README.md` covering monorepo layout, how to run `frontend/` (`npm install && npm run dev`) and `backend/` (`pip install -r requirements.txt && python run.py`).
17. Added post-review: build `UserMenu` + `InfoPage` + the four info pages, wire the four new routes, replace the sidebar's static profile button.
18. Added post-review: add `SourceMaterial` to the type model, a document-attach control in `CreateCourse` (`File[]` in local state), carry attached files to `OutlineReview` via router navigation state and render them there, add a fixture `sourceMaterials` entry to the GPU Programming course, and build `SourceMaterialsPanel` + the Lesson header button that opens it.
19. Added post-review: build `CourseHome`, add its route, and repoint `CourseCard` at `/courses/:courseId` instead of the learner's current activity.

## 9. Open questions / deferred decisions
- **Node/npm aren't installed on this machine.** I can hand-write every frontend file, but installing dependencies and running the Vite dev server to visually confirm it renders needs Node present. Revisit before calling Phase 0 "done" — worth installing Node so we can actually view it in a browser.
- **Exact design tokens are approximate**, read off the mockup image rather than an official style guide. Expect small color/spacing adjustments once real screens are built and compared side-by-side with the mockup.
- **Fixture depth is intentionally uneven** (one fully-built course, two list-only) to keep Phase 0 effort focused on proving the pattern rather than authoring lots of placeholder content. Revisit if you want all three courses fully fleshed out.
- **Flask backend is intentionally inert** — no DB, no real routes beyond health check. Phase 1 design will define the real API surface (course generation, retrieval, persistence) described in the PRD.
- **Capstone/practicum activities** are treated as a styling variant of the "project" activity type for now (not a fully distinct type) since the PRD doesn't describe them as functionally different — worth confirming that's right once we're deeper into content design.
- **Document upload was UI-only in Phase 0** (attached files lived in browser memory via `URL.createObjectURL`, nothing parsed or persisted). Superseded later in Phase 1 — see "Real document ingestion" below: files are now really extracted, stored, and used to ground the interview, outline, and (when present) module generation.

## Phase 1: Foundations (Persistence + LiteLLM)

First build slice of Phase 1, covering the plumbing everything else depends on: a real test suite, the LiteLLM wrapper, and the Course/Module/Activity persistence layer. Course-creation flow, retrieval, generation, and the REST API surface are the next slice, built on top of this.

### Test-driven development
All backend work from this point follows red/green/refactor: write a failing test against the not-yet-built code, confirm it fails for the right reason, implement, confirm it passes. `backend/tests/` holds the suite (`pytest`, run via `python -m pytest` from `backend/`), with `backend/requirements-dev.txt` (`-r requirements.txt` plus `pytest`) kept separate from the runtime `requirements.txt` so an end user installing Bonsai to actually use it doesn't need test tooling. `tests/conftest.py` provides `app` (a `create_app(test=True)` instance), `client` (its test client), and `db` (fresh in-memory tables per test, torn down after).

### LLM_TEST_MODE and the LiteLLM wrapper
`create_app(test: bool = False)` sets `app.config["LLM_TEST_MODE"]`. `run.py` reads it from the `BONSAI_TEST_MODE` environment variable, so a developer runs `BONSAI_TEST_MODE=true python run.py` to use the app without any API key or cost, and the pytest suite always runs with `test=True` regardless. `app/services/llm.py` is the only module that imports `litellm`. Its `complete(messages, model)` function checks `LLM_TEST_MODE` and either calls `litellm.completion()` for real or returns a canned string (`"[MOCK RESPONSE] <last user message>"`) that echoes the prompt, so it's visibly obvious in the UI when a response is mocked. Retrieval (Tavily) should get the same treatment once it's built: one wrapper module per external call, one seam per capability.

### Persistence: Course, Module, Activity
`app/extensions.py` holds bare `db = SQLAlchemy()` and `migrate = Migrate()` instances (kept out of `app/__init__.py` and `app/models.py` to avoid a circular import between them). `app/models.py` defines `Course` → `Module` → `Activity` with cascading deletes and explicit `position` columns for ordering (SQLite doesn't guarantee row order otherwise). Per the PRD's hybrid storage decision, these models hold structural metadata and status only. `Activity.content_path` is a nullable pointer to where the real generated content (body text, citations, quiz options, etc.) lives on disk, not a column of its own. `Course.progress_percent` is a computed Python property (percent of activities with `status == "completed"`), not a stored column, so it can't drift out of sync with the activities it's derived from.

In test mode the database is `sqlite:///:memory:` (fresh per test via the `db` fixture); otherwise it's a real file at `<instance_path>/bonsai.db`, created via Flask's `instance_relative_config=True` folder (already covered by the existing `*.db` gitignore rule). Schema changes go through Flask-Migrate: `FLASK_APP=run.py flask db migrate -m "..."` to autogenerate a migration, `flask db upgrade` to apply it. This is deliberate setup for the PRD's flagged export/import-portability risk: Alembic is the mechanism that will let an older export's schema get upgraded on import in a later phase.

**Note for anyone regenerating a migration:** `app/models.py` must actually be imported somewhere `create_app()` runs (it's imported inside the factory, after `db.init_app()`), or Alembic's autogenerate sees an empty `db.metadata` and reports "No changes in schema detected" even though the models exist. Hit this once already; the fix is the `from app import models` line inside `create_app()`, not a `flask db` flag.

### Deferred to the next slice (at the time this section was written)
`SourceMaterial` and `UserSettings` don't have persistence models yet (Phase 0's fixtures cover them on the frontend for now). Where API keys should live, in the same database that gets exported, or a separate untracked local file, so export doesn't need to remember to scrub them, is an open question worth deciding before `UserSettings` persistence is built. No REST API routes exist yet beyond `/api/health`; the frontend still runs entirely off static fixtures. Document ingestion (real text extraction) and the retrieval agent are unbuilt.

## Phase 1: SourceMaterial, UserSettings, and the first REST routes

Second build slice, same TDD discipline as the first: every model and route below was written test-first (failing test confirmed, then implementation).

### SourceMaterial and UserSettings models
`SourceMaterial` (`app/models.py`) follows the same pattern as `Activity`: a `course_id` foreign key with cascading delete, `file_name`, and `file_path` pointing at the stored file on disk (no upload/serving endpoint yet, just the model).

`UserSettings` resolves the API-key storage question flagged in the previous section: it stays in the same SQLite database as everything else, not a separate file. There's genuinely one settings row for the whole app (no multi-user concept), enforced by a `get_or_create()` classmethod that always operates on `id=1` rather than a normal query, so callers never need to think about "which settings row." The tradeoff this accepts: whenever data export/import gets built, it needs to explicitly skip the `model_provider_api_key` and `model_provider_byom_endpoint` columns rather than dumping the whole database file. Noted here so that work doesn't forget it.

### Serialization: to_dict()
Every model got a `to_dict()` method producing the same camelCase shape already established in `frontend/src/types/course.ts` (`estimatedTimeline`, `progressPercent`, `learningOutcomes`, `type` rather than `activityType`, etc.), even though the Python attributes themselves stay snake_case. This means the frontend can eventually consume these responses directly against its existing types with no field-renaming layer in between. `Activity.to_dict()` deliberately omits the content-heavy fields (`body`, `citations`, `question`, `options`, `prompt`, `checkPrompt`) since nothing populates `content_path` yet; those will get read from disk and added once generation exists.

`UserSettings.to_dict()` never includes the raw `apiKey`. It returns `modelProvider.hasApiKey: bool` instead, so a future Settings UI can show "a key is configured" without the backend echoing a stored secret back on every read. This does mean the frontend's current `UserSettings` type (which has `modelProvider.apiKey?: string`) will need a small adjustment when it's actually wired to this API, deferred until that wiring happens.

### REST routes
`GET /api/courses` (list) and `GET /api/courses/<id>` (full detail, 404 if missing) in `app/routes/courses.py`; `GET /api/settings` (creates defaults on first call) and `PUT /api/settings` (partial update, both at the top level and within the nested `modelProvider` object, so updating one field never clobbers another) in `app/routes/settings.py`. Both blueprints are registered in `create_app()` alongside the existing health check. No course-creation route exists yet; these are read/update only.

### Still deferred (at the time this section was written)
The frontend is not wired to any of this yet; `AppDataContext` still runs entirely off the Phase 0 fixtures. Document ingestion, the retrieval agent, and actual LLM-driven course/module generation are unbuilt. File upload/serving for `SourceMaterial` (an actual endpoint to receive and store the file `file_path` points at) doesn't exist yet either, only the model.

## Phase 1: Wiring the frontend to courses and settings

Third build slice: `AppDataContext` now fetches real data from the backend instead of the Phase 0 fixtures, which are deleted (`frontend/src/data/mockCourses.ts`, `mockUser.ts`). Activity completion, course creation, and generation are still frontend-only or unbuilt, covered below.

### API client
`frontend/src/lib/api.ts` is a small wrapper around `fetch` (`fetchCourses`, `fetchSettings`, `updateSettings`) pointed at a hardcoded `http://localhost:5000/api`. No env-var plumbing for this yet, since there's only one deployment target (localhost dev) right now; revisit if that stops being true.

### AppDataContext
On mount, it fetches courses and settings in parallel and populates state; a `DEFAULT_USER` constant (matching the backend's own defaults) means `user` is never null while waiting, so pages don't need loading guards. A `loading` flag is exposed but not yet consumed anywhere. If the fetch fails (backend not running), it logs to the console and leaves the default/empty state rather than crashing, which is proportionate for a dev-stage app, not a production error-handling story.

`completeActivity` was a local-only state mutation through this point, same logic as Phase 0, since there was no backend endpoint for it yet; see the next section for where that changed. `updateUserSettings` calls `PUT /api/settings` and replaces local state with the response, rather than merging the patch into local state directly, so the frontend's view of settings always reflects what the backend actually stored.

### The API-key display problem, resolved
Since the backend's `UserSettings.to_dict()` deliberately never returns the raw API key (see the previous section), the frontend's `UserSettings` type changed to match: `modelProvider.apiKey?: string` became `modelProvider.hasApiKey: boolean`. A separate `UserSettingsPatch` type (in `frontend/src/types/course.ts`) is what `updateUserSettings` actually accepts, since PUT is where a new `apiKey` gets written even though GET never reads one back. `Settings.tsx` reflects this: the API key input is a write-only local draft (`apiKeyDraft`, always starts empty) that saves on blur and shows "A key is configured" / "No key set yet" based on `hasApiKey`, rather than trying to bind to a value that no longer exists. The `byomEndpoint` field also moved to save-on-blur (matching the same pattern) rather than firing a network request per keystroke, which the old fixture-only version didn't need to worry about.

### Seed data
`backend/seed.py` inserts the same three example courses the old frontend fixtures had (GPU Programming, Deep Learning Foundations, Data Structures & Algorithms), run once via `python seed.py`. Worth noting: GPU Programming's `progress_percent` comes out to 60.0, computed, matching the old fixture's hardcoded value exactly, but Deep Learning Foundations and Data Structures & Algorithms now show 0% instead of the old fixture's hardcoded 30%/10%. Those two courses never had real per-activity data behind them (Phase 0 deliberately kept them "list-level only"), so 0% is the honest computed answer rather than a fabricated one. Fixing that means giving them real activities, not faking the percentage.

### Still deferred (at the time this section was written)
No endpoint exists yet to persist activity completion, so progress resets on refresh for anything done after the seed. File upload/serving for `SourceMaterial`, document ingestion, the retrieval agent, and real course-creation/generation are all still unbuilt; `CreateCourse` and `OutlineReview` still run their Phase 0 scripted/canned flow untouched.

## Phase 1: Persisting activity completion

Fourth build slice: progress now survives a refresh. Test-first as usual.

### `POST /api/activities/<id>/complete`
`app/routes/activities.py` moves the unlock cascade server-side, the exact same logic that used to live only in `AppDataContext`: mark the activity completed, unlock the next locked activity in its module by position, and if that was the module's last remaining activity, mark the module completed and unlock the next locked module in the course. It takes only the activity id (not course/module ids) since `Activity.id` is already a unique primary key and the rest is reachable through its relationships (`activity.module`, `module.course`). Returns the full serialized parent course so the frontend can just replace its local copy wholesale rather than reconciling a partial update.

### Frontend
`AppDataContext.completeActivity` now takes just `(activityId: string)` (was `(courseId, moduleId, activityId)`, the ids beyond `activityId` were never actually needed once the backend does the work) and calls the new endpoint, replacing the course in local state with the authoritative response instead of computing the unlock logic client-side. `Lesson.tsx`'s `handleContinue` still navigates immediately based on the client's own knowledge of module structure (is there a next activity at this position, yes/no), without waiting on the completion request to resolve; that's a deliberate, minor race (the status update lands a moment after navigation) rather than an oversight, acceptable given how fast a local SQLite write actually is.

### Verified
Manually confirmed end-to-end with curl against the seeded GPU Programming course, not just the test suite: completing `m2-a3` moved `progressPercent` from 60.0 to 70.0, unlocked `m2-a4`, and a fresh `GET /api/courses/gpu-programming` afterward still showed the change, confirming it's really in SQLite and not just held in the response.

## Phase 1: Real course creation (interview -> outline -> approve)

Fifth build slice, and the largest so far: `CreateCourse` and `OutlineReview` no longer run Phase 0's scripted/canned flow. This section also covers two decisions the user set before building: prompts live as separate markdown files, and every course carries a growing conversation history, not just a creation transcript.

### Prompts: markdown files, not Python constants
`backend/app/prompts/` holds plain `.md` files (`course_interview.md`, `course_outline.md` so far), loaded by `app/services/prompts.py`'s `load_prompt(name, **variables)` using stdlib `string.Template` (`${variable}` placeholders, no templating dependency needed). The point: a prompt-wording change now shows up as a diff to a `.md` file, not tangled into a code diff, and versioning is just git history on those files. No explicit multi-version registry (e.g., `v1/`, `v2/` folders) was built, since nothing yet needs to run two prompt versions side by side; add one if that becomes real.

### `ConversationMessage` and `Course.stage`
The interview happens *before* a course has a title, modules, or anything else, which is awkward if conversation history is supposed to belong to a course. Resolved by creating the `Course` row immediately when a learner starts (title="New Course", empty description/prerequisites/modules, `stage="interview"`), so its history has something to attach to from message one. `Course.stage` moves through `interview` -> `outline_review` -> `active` (no `completed` transition wired yet, that's course-progress work, not creation). `ConversationMessage` (`app/models.py`) holds `course_id`, `role` (`user`/`assistant`), a free-form `kind` tag (`interview_answer`, `interview_question`, `outline_presented`, `outline_revision_request`, `outline_approved`, not a rigid enum so new kinds don't need a migration), `content`, and `created_at`. `Course.parent_course_id` (self-referential, nullable) is added now for future "keep going / dive deeper / branch off" lineage, but no branch/extend endpoint exists yet; that's still Phase 2, per the roadmap.

### `app/services/course_generation.py`
The interview loop (`start_course`, `submit_interview_answer`) counts `interview_question`-kind messages to decide when to stop (capped at `MAX_INTERVIEW_QUESTIONS = 10`, matching the PRD's "roughly ten questions"), asks the model for the next question via the `course_interview` prompt, and expects strict JSON back (`{"done": bool, "question": str|null}`). The outline loop (`generate_outline`, `submit_outline_feedback`, `approve_outline`) does the same with the `course_outline` prompt, replacing `Course.modules` wholesale on (re)generation, which correctly cascades-deletes any prior modules via the existing `delete-orphan` relationship config. `approve_outline` flips `stage` to `active` and starts the first module. A small `_parse_json_response` helper strips common ```` ```json ```` code-fence wrapping before parsing, since real models often add that despite being told not to.

Two internal-only pieces, not part of the public API: `CourseNotFoundError` (a domain exception the route layer catches and turns into a 404, keeping "not found" handling out of the service functions' control flow) and the LLM model string is a hardcoded `DEFAULT_MODEL` constant for now, since per-user model selection from `UserSettings` isn't wired into generation yet.

### Test-mode mocking lives at the generation-function level, not in `complete()`
This was the wrinkle flagged before building: `app/services/llm.py`'s `LLM_TEST_MODE` mock just echoes text back, which can't satisfy something that needs structured JSON. So `_next_interview_step` and `_generate_outline_content` each have their own `LLM_TEST_MODE` branch returning realistic canned structured data directly (a deterministic "ask up to 10 questions" sequence; a canned 3-module outline), bypassing `complete()`/JSON-parsing entirely in test mode. This is what let the test suite verify real control flow (does the interview actually stop at 10, do modules actually get created) without a live model.

### A real bug this surfaced: `test` and "in-memory database" were the same flag
`create_app(test=True)` used to switch to `sqlite:///:memory:` as a side effect of enabling `LLM_TEST_MODE`. That's correct for the pytest suite (which wants both together), but wrong for running the dev server day-to-day: `BONSAI_TEST_MODE=true python run.py` (exactly what avoiding LLM costs requires) silently lost access to the real, persisted database. Fixed by splitting into two independent parameters: `create_app(test: bool, in_memory_db: bool = False)`. `tests/conftest.py`'s `app` fixture now explicitly passes both (`test=True, in_memory_db=True`); `run.py` never passes `in_memory_db`, so the dev server always sees the real file regardless of LLM test mode. Caught by manually restarting the dev server in test mode mid-session and noticing the seeded courses disappeared, not by the test suite, since the test suite's fixture was already (correctly, for its own purposes) requesting both flags together.

### Frontend
`CreateCourse.tsx` no longer scripts a fixed question list: it calls `startCourse(message)` on the first answer, then `submitInterviewAnswer(courseId, answer)` for each one after, rendering whatever question the backend returns. Progress dots now show progress toward the shared `MAX_QUESTIONS = 10` constant (duplicated by hand between frontend and backend, no shared-config layer between them yet) rather than a fixed local question array. When the backend signals `done`, it calls `generateOutline(courseId)` and navigates to `/create/review/:courseId` (the route gained a `:courseId` param it didn't have before). `OutlineReview.tsx` fetches the real course by id on mount, sends revision feedback to `submitOutlineFeedback`, and "Start Learning" calls `approveOutline` then `AppDataContext.refreshCourses()` (a new context method that just re-fetches the course list) before navigating to My Courses, so the newly-active course actually shows up without a page reload. Attached files are still frontend-only preview (unchanged from Phase 0): nothing uploads them to the backend, since document ingestion is still deferred.

### Still deferred (at the time this section was written)
Module *content* generation (`POST /api/modules/<id>/generate-activities`, so a module's actual readings/quizzes/etc. get created when reached) and change-direction (regenerating remaining modules from mid-course feedback) were both in the original proposal but scoped out of this slice to keep it reviewable; they reuse the same generation machinery built here. Document upload/ingestion, the retrieval agent, and branch/extend ("keep going / dive deeper") remain unbuilt.

### Verified
Full flow confirmed end-to-end with curl against the real dev server (test mode, real database): started a course, answered through all 10 interview questions (confirmed `done` flips exactly on the 10th), generated an outline (3 modules, `stage: outline_review`), approved it (`stage: active`, first module `in_progress`), and confirmed it appeared in `GET /api/courses` alongside the seeded ones. Test course cleaned up afterward.

## Phase 1: Schema enforcement for LLM outputs

Sixth build slice: before this, a malformed or off-spec model response (missing a field, wrong type, invalid JSON) would fail deep inside `_apply_outline` with a confusing `KeyError`, or worse, silently write garbage into the database. Now every prompt's expected response shape is a Pydantic schema, validated right where the response is parsed.

### `app/services/llm_schemas.py`
`InterviewStepSchema` (`done: bool`, `question: str | None`) and `CourseOutlineSchema`/`CourseModuleSchema` (matching `course_outline.md`'s requested JSON exactly) are Pydantic models. Their field names deliberately use the prompts' own camelCase (`estimatedTimeline`, `learningOutcomes`) rather than PEP 8 snake_case, since these classes exist purely to mirror the external JSON contract, not as general Python domain models. `validate_llm_json(raw: str, schema: type[BaseModel])` combines the markdown-code-fence stripping that used to live in `course_generation.py`, JSON parsing, and schema validation into one call, raising a single `LLMOutputValidationError` for either failure mode (invalid JSON syntax, or valid JSON that doesn't match the schema) rather than leaking a raw `json.JSONDecodeError` or `pydantic.ValidationError`.

Pydantic itself wasn't a new dependency in practice (it was already installed transitively via `litellm`), but it's now an explicit direct dependency in `requirements.txt` since `app` code imports it directly.

### Both the real and mocked generation paths return the same schema types
`_next_interview_step` and `_generate_outline_content` return `InterviewStepSchema`/`CourseOutlineSchema` instances either way: the real path calls `complete()` then `validate_llm_json(...)`; the `LLM_TEST_MODE` mock path constructs the schema objects directly (`InterviewStepSchema(done=..., question=...)`, `CourseOutlineSchema(title=..., modules=[CourseModuleSchema(...), ...])`). This means the canned test-mode data is held to the exact same shape as real output, so the mocks can't silently drift out of sync with what the schema actually requires. Downstream code (`_advance_interview`, `_apply_outline`) uses attribute access (`result.done`, `outline.modules[i].title`) instead of dict indexing.

### Route-level handling
The four course-creation routes that call into generation (`create_course`, `post_interview_answer`, `post_generate_outline`, `post_outline_feedback`) catch `LLMOutputValidationError` and return `502` with a description, distinct from the existing `404` (course not found). `approve_outline` doesn't call generation, so it only needs the `404` case. The frontend didn't need any changes for this: `api.ts`'s `request()` already throws on any non-OK status, and `CreateCourse`/`OutlineReview` already catch and show a generic error message.

### Verified
Two kinds of tests, both necessary: unit tests directly against `validate_llm_json` (valid data passes, invalid JSON syntax and schema-mismatched JSON both raise `LLMOutputValidationError`), and integration tests that run with `LLM_TEST_MODE` off and monkeypatch `litellm.completion` itself to return malformed text, confirming the error actually propagates through the real `complete()` -> `validate_llm_json` path from `start_course`/`generate_outline`, and that the route layer turns it into a `502` rather than a raw 500 crash. The `real_llm_app`/`real_llm_client` fixtures added for this (in `tests/conftest.py`) are the first fixtures in the suite that exercise the non-test-mode code path at all, with the database still isolated and in-memory.

## Phase 1: BYOM model name field

Seventh build slice, small: confirmed a local Ollama instance (`llama3`, at `http://localhost:11434`) actually responds. Actually pointing generation at it needs settings-driven model selection in `course_generation.py`, which isn't built yet, but BYOM settings could only store the endpoint, not which model to ask for at it, so this closes that gap first: `UserSettings.model_provider_byom_model` (nullable string), surfaced as `modelProvider.byomModel` in serialization, accepted by `PUT /api/settings`, and a matching input in `Settings.tsx` (same save-on-blur pattern as `byomEndpoint`, since it isn't secret and shouldn't fire a request per keystroke). Migration applied; verified live against the running dev server.

## Phase 1: Hosted model name + embedding model fields

Eighth build slice, finishing the Settings model-configuration surface. Same gap as BYOM applied to the hosted tier: `hostedProvider` only says *which company* (Anthropic vs OpenAI), not *which model*, and `DEFAULT_MODEL` in `course_generation.py` is still a hardcoded Claude model regardless of what's selected. Added `UserSettings.model_provider_hosted_model` (nullable string, optional, blank means "use a sensible default"), same pattern as `byomModel`.

Also added `UserSettings.embedding_model`, per the PRD's requirement that embedding be independently configurable from the completion model (a learner might reasonably want Anthropic for completion but a local embedding model, or vice versa), so it's a top-level field, not nested under `modelProvider`. Doesn't do anything yet since retrieval and semantic search aren't built; the Settings UI says so explicitly rather than implying it's already wired up.

Both fields, migration, and their `Settings.tsx` inputs (save-on-blur, matching the existing pattern) built the same way as `byomModel` was: model column -> `to_dict()` -> route acceptance -> migration -> frontend type -> frontend field. Verified live against the running dev server.

## Phase 1: Tavily API key field + settings-driven model selection

Ninth and tenth build slices together: finished the Settings model-configuration surface, then actually made generation use it.

### Tavily API key
`UserSettings.tavily_api_key`, top-level (not nested under `modelProvider`, same reasoning as `embedding_model`: it's a separate concern from the LLM provider entirely per the PRD). Masked the same way as the hosted API key: `hasTavilyApiKey: bool` on read, `tavilyApiKey` write-only on `PUT`. Doesn't do anything yet since the retrieval agent isn't built; `Settings.tsx` says so explicitly.

### `app/services/model_selection.py`
`resolve_model_config()` reads the single `UserSettings` row and returns exactly the kwargs `llm.complete()` needs: for `hosted`, `{"model": ..., "api_key": ...}` (falling back to a per-provider default model, `claude-3-5-sonnet-20241022` or `gpt-4o`, when `hostedModel` is blank); for `byom`, `{"model": "ollama/<byomModel>", "api_base": <byomEndpoint>}` (falling back to `llama3` / `http://localhost:11434` when unset), following LiteLLM's own convention for routing to a local Ollama instance. Put in its own module rather than inside `course_generation.py` since module-content generation will need the identical resolution logic.

`llm.complete()` gained optional `api_key`/`api_base` parameters, forwarded to `litellm.completion()` only when actually provided (not passed as `None`), so the existing hosted-only call sites and tests didn't need to change. `course_generation.py`'s two real-mode call sites (`_next_interview_step`, `_generate_outline_content`) now call `complete(messages=..., **resolve_model_config())` instead of a hardcoded `DEFAULT_MODEL` constant, which is gone.

### Verified against a real local model, not just mocks
Ran the dev server in real (non-test) mode with `UserSettings` already configured for BYOM (`llama3` at `http://localhost:11434`, set via the Settings UI earlier) and started a real course through `POST /api/courses`. It genuinely called Ollama, got back valid JSON matching `InterviewStepSchema`, and persisted correctly. The generated question's wording was a bit off (referenced the topic as `[New Course]` instead of the actual subject), which is llama3 (8B, quantized) being a weaker model at following the prompt precisely, not a bug: this is exactly the disclosed "best-effort" BYOM quality tradeoff from the PRD, and confirms the plumbing (settings -> model resolution -> real API call -> schema validation -> persistence) all works end to end. Test course cleaned up afterward.

## Phase 1: Module content generation

Eleventh build slice: a module's actual lesson content (readings, quizzes, essays, discussions, projects) now gets generated the first time a learner reaches it, closing the biggest gap called out at the end of the course-creation slice. Reuses every pattern established so far: prompts as markdown, schema-validated output, mocked vs. real branching, settings-driven model resolution.

### Schema and prompt
`GeneratedActivitySchema` (`app/services/llm_schemas.py`): `type` (a `Literal` of `reading`/`quiz`/`essay`/`project`/`discussion`/`assessment`, deliberately excluding `video`, since video embedding isn't built), `title`, `estimatedMinutes`, and four optional content fields (`body`, `question`, `options`, `prompt`) that only apply to some types. No cross-field validation requiring type-appropriate fields (e.g. forcing `reading` to have a `body`): the frontend's `ActivityCard` already tolerates missing optional fields gracefully, so enforcing it here would just be extra rigidity without a real payoff. `ModuleActivitiesSchema` wraps a list of these. `app/prompts/module_generation.md` asks for 3-6 activities per module, mixed formats, ending in an assessment (or a capstone project for the course's final module), matching the PRD's "no grading, feedback only" stance for quizzes/assessments.

### Hybrid storage made real: `content_storage.py`
Until now `Activity.content_path` existed as a column but nothing wrote to or read from it. `app/services/content_storage.py` adds `save_activity_content(activity_id, content) -> str` and `load_activity_content(content_path) -> dict`, storing one JSON file per activity under `<instance_path>/module_content/`. `Activity.to_dict()` now merges in file content when `content_path` is set (`data.update(load_activity_content(...))`), so the content-heavy fields only ever hit disk, never the database. This needed one small fix to `app/__init__.py`: `os.makedirs(app.instance_path, exist_ok=True)` used to run only in the non-in-memory-db branch, so the test suite's in-memory-db fixtures had no real directory to write content files into even though the LLM mocking and the database are independent concerns; moved it to run unconditionally.

### `app/services/module_generation.py`
`generate_module_activities(module_id)` is idempotent: a module that already has activities is returned unchanged, so a duplicate trigger (the learner revisits a page, the frontend fires twice) never regenerates or duplicates content. Otherwise it builds the prompt from the module's own title/description/learning outcomes (plus the parent course's title/description for context), gets back a validated `ModuleActivitiesSchema`, and persists one `Activity` per generated item: the first is `status="available"` (matching `findCurrentActivity`'s expectation that a learner-ready activity is `available`, not `in_progress`, which is a module-level status), the rest `"locked"`. Each activity's non-structural fields get written via `save_activity_content` before commit. `LLM_TEST_MODE` returns three canned `[MOCK]`-prefixed activities (reading, discussion, assessment) built from the same `GeneratedActivitySchema`/`ModuleActivitiesSchema` types the real path uses, so mocks can't drift from the schema.

### Route
`POST /api/modules/<module_id>/generate-activities` (new `app/routes/modules.py`, registered as its own blueprint): calls the service, catches `ModuleNotFoundError` -> 404 and `LLMOutputValidationError` -> 502 (same pattern as the course-creation routes), returns the serialized parent course.

### Frontend: minimal auto-trigger
`CourseHome.tsx` already had a "Generating..." placeholder state built for an in-progress module with zero activities (from Phase 0's mockup fidelity work), but nothing actually triggered generation. Added a `useEffect` that finds the first `in_progress` module with `activities.length === 0` and calls the new `generateModuleActivities(moduleId)` context method once (guarded by a `useRef<Set<string>>` of already-triggered module ids, so a re-render or a mid-flight course refresh can't fire a duplicate request). `AppDataContext` follows the same pattern as `completeActivity`: call the API, then replace the course in local state with the server's authoritative response.

### Verified
Full test suite (schema validation, `content_storage` round-trip, `module_generation` service including idempotency and an `LLMOutputValidationError` integration test with `litellm.completion` monkeypatched, and the route's 404/200 cases) plus a real end-to-end run against the dev server in real (non-test) mode with the existing BYOM `llama3` configuration: called `POST /api/modules/dl-module-2/generate-activities` against the seeded Deep Learning Foundations course's in-progress, zero-activity module. Unlike the earlier interview-question test, llama3 produced four well-formed, schema-valid, genuinely on-topic activities on the first try (a reading on convolutions, an essay prompt, a multiple-choice quiz, and a CNN implementation project), with no retries needed. Calling the endpoint again returned the identical activity ids, confirming idempotency against the real database, not just the mocked test. `npm run build` and `tsc --noEmit` both pass with the new frontend wiring.

## Phase 1: Retrieval agent

Twelfth build slice: module generation can now ground reading content in real web sources via Tavily, matching the PRD's requirement that this be an actual iterative search/fetch/evaluate loop, not a single unevaluated search pass. Built and fully tested against mocked/monkeypatched calls; live verification against a real Tavily key is still pending (Tavily's Python SDK wasn't used, since the API is a plain two-endpoint REST surface not worth an extra dependency for).

### `app/services/retrieval.py`
Thin wrapper around Tavily's `POST /search` and `POST /extract` endpoints (via `requests`, now an explicit dependency rather than transitive-only through `litellm`): `web_search(query, api_key, max_results=5) -> list[dict]` (`{title, url, content}` per result) and `fetch_page(url, api_key) -> dict` (`{url, content}`, from Tavily's `raw_content` field). Both raise a single `RetrievalError` on any HTTP failure or an empty/missing result set, mirroring `llm_schemas.LLMOutputValidationError`'s "one clear exception type" approach. Both also check `LLM_TEST_MODE` and return canned `[MOCK]` results without touching `requests` at all when it's on, exactly mirroring `llm.py`'s existing convention for `complete()`, so retrieval never costs Tavily credits in dev or the test suite.

### `app/services/llm.py`: `complete_with_tools()`
A sibling to `complete()`, not a replacement: takes an OpenAI-style `tools` list and returns the raw response message (exposing `.content` and `.tool_calls`) instead of unwrapping straight to a content string, since the caller needs to see whether the model asked to call a tool. No `LLM_TEST_MODE` branch inside it, deliberately: per this project's existing convention (see the Schema Enforcement section above), mocking lives at the generation-function level, and `complete_with_tools` is only ever reached from a path (`module_generation`'s real-mode branch) that's already skipped entirely in test mode.

### `app/services/retrieval_agent.py`: the tool-calling loop
`run_agent(messages, model_config, tavily_api_key) -> str` defines two OpenAI-style tool schemas (`web_search`, `fetch_page`) and loops up to `MAX_TOOL_ITERATIONS = 5` times: call the model with tools enabled, and if it responds with tool calls, execute each one for real (via `retrieval.py`) and feed the JSON-encoded results back in as `role: "tool"` messages before calling again. If the model still hasn't converged on a final answer after the cap, one last call strips the tools away entirely and asks it to just answer with what it has, so a model that never stops calling tools (a real risk with weaker BYOM models) can't loop forever. Tool-call round-tripping happens as plain dicts (not the raw provider objects LiteLLM returns), since that's the shape `messages` needs when replayed back into another `litellm.completion()` call.

### Wiring into `module_generation.py`
`_generate_activities_content` now checks `UserSettings.tavily_api_key`: if set, the prompt goes through `run_agent()` instead of a plain `complete()` call; if unset, behavior is unchanged from before this slice (plain completion, no citations), so a learner who hasn't configured Tavily sees no difference or degradation. `GeneratedActivitySchema` gained an optional `citations: list[CitationSchema] | None` field (`CitationSchema` is just `{label, url}`, matching the frontend's existing `Citation` type exactly, which already had a citations-rendering `ActivityCard` component built in Phase 0 that had nothing to feed it until now). The `LLM_TEST_MODE` mock path's reading activity now includes one `[MOCK]` citation, so the full citations round-trip (schema -> content file -> `Activity.to_dict()` -> frontend) is exercised even without a real Tavily key.

### Best-effort BYOM tool-calling, as disclosed in the PRD
Nothing in this slice special-cases the BYOM/hosted distinction: `run_agent` calls whatever model `resolve_model_config()` points at, with tools enabled, the same way regardless of tier. Hosted models (Anthropic, OpenAI) have reliable, well-tested tool-calling through LiteLLM. Local Ollama models' tool-calling support varies a lot by model and is much less consistently normalized through LiteLLM's Ollama integration; a model that doesn't honor the `tools` param at all will simply never produce `tool_calls`, so `run_agent` returns its first response as final without ever searching, degrading gracefully to the old plain-generation behavior rather than erroring. This matches the PRD's explicit "best-effort for BYOM" framing rather than trying to paper over it.

### Verified
Full test suite covers: `retrieval.py`'s mocked/real branches and Tavily request/response shape (`web_search`/`fetch_page`, including the HTTP-failure and no-results error paths); `complete_with_tools()`'s argument forwarding and raw-message return; `retrieval_agent.run_agent()`'s no-tool-call, single-tool-call (both `web_search` and `fetch_page`), and max-iterations-forces-a-final-answer cases, all via monkeypatched `litellm.completion` so no network call happens; and `module_generation.py`'s routing (Tavily key present -> `run_agent` used and its result validated/persisted with citations; key absent -> old plain path, unchanged). Not yet done: a live call against a real Tavily API key, since one isn't configured yet. That's the next step before this can be considered fully verified end-to-end, the same way BYOM model selection wasn't considered done until it was checked against a real running Ollama instance.

## Roadmap: AI evals (Phase 3, not yet built)

Added to the roadmap, not started. The schema validation built into `llm_schemas.py` catches *structural* problems (malformed JSON, missing fields) but says nothing about *quality*: a syntactically perfect interview question can still be unhelpful, a search result can be on-topic but useless, a generated lesson can be complete-looking but shallow or off-tone. The ask is a lightweight "AI grader" layer: for a given generated artifact plus a rubric, have a model score it and explain why, rather than only trusting schema validation and human spot-checks.

### Likely scope, once picked up
Three graders, one per artifact type called out:
- **Interview question helpfulness** — given the conversation so far and the question the model just asked, score whether it actually moves toward a useful course outline (relevant, non-redundant, appropriately scoped) rather than generic or off-target.
- **Search result relevance** — given a `web_search` query and the results `retrieval.py` returned, score whether the results are actually relevant and credible enough to ground lesson content in.
- **Lesson/activity quality** — given a generated module activity (reading, quiz, essay, etc.) and its source module/course context, score completeness (does it cover the stated learning outcomes), tone (matches the learner's configured feedback tone), and general quality.

### Likely shape
Each grader is probably its own small rubric prompt (as a `.md` file, same pattern as the generation prompts) plus a Pydantic schema for the grader's output (e.g. `score: int` 1-5 plus `rationale: str` per dimension), reusing `validate_llm_json` so a malformed grade fails the same clear way a malformed generation would. Graders are themselves LLM calls, so they cost tokens; they don't belong in the `pytest`/`LLM_TEST_MODE` suite that must stay free and fast, so they're probably a separate on-demand script/CLI command run against real (or recorded) generations rather than something that runs on every commit.

### Open questions to resolve when this is actually picked up
Score scale and pass/fail threshold (if any); whether evals run against live freshly-generated content or a fixed set of recorded "golden" examples for repeatability; which model grades (same provider/model the learner configured, or a fixed grading model independent of their settings, to avoid a model grading its own output); and how results get surfaced (console report, a file, something in the UI) — none of this is decided yet.

## In-course visual aids for reading activities (Phase 2, DONE)

Built as scoped below, no material changes. Retrieval-based, not generation: illustrates concepts *within* a reading activity's body text using Tavily image search, separate from Phase 2's generated course/module thumbnails.

Slots into the existing per-activity generation loop in `module_generation.py`'s `_generate_activities_content()`: after a `reading`-type activity's body is generated, and only if `UserSettings.visual_aids_enabled` is on and a Tavily key is configured, `_add_visual_aids()` calls a new prompt (`app/prompts/lesson_visual_aids.md`, validated via a new `VisualAidPlanSchema` in `llm_schemas.py`) that reviews the finished body and returns 0-3 `{query, caption, anchorText}` entries. For each, a new `image_search(query, api_key)` in `retrieval.py` calls Tavily's `/search` endpoint with `include_images`/`include_image_descriptions` — confirmed live against a real Tavily key that the response shape is `images: [{url, description}]` (with `description` sometimes a real `null`, not just absent, for some hosts) — and the top result is spliced into the body as `![caption](url)` right after `anchorText`. Images are hotlinked, not downloaded/cached. An aid whose `anchorText` isn't found verbatim in the body, or whose image search returns nothing, is silently skipped. Gated behind `UserSettings.visual_aids_enabled` (Boolean, default `False`), same `deep_search_enabled` opt-in precedent. Frontend: `Markdown.tsx`'s block-level renderer gained an `img` override rendering a real `<figure>`/`<figcaption>` (the caption travels as markdown's alt-text position, which is otherwise invisible to a sighted user) instead of react-markdown's unstyled default. Live-verified end-to-end: a real image with a real caption and a genuine Tavily-hosted URL landed in a generated reading's body.

## Opt-in web-search supplementing for document-grounded courses (Phase 2, DONE)

Built as scoped below. Reconciled the PRD against what had shipped: the PRD's Retrieval & Citation section always said a document-grounded course's retrieval agent should "supplement [the document] with web search rather than replacing it," but `_generate_activities_content()` skipped search entirely whenever a course had source materials. Fixed by making it an explicit per-course opt-in rather than an implicit always-skip.

New `Course.web_search_supplement_enabled` (Boolean, default `False`) — OR'd in, not overwritten, across multiple document uploads on different interview turns, so opting in once keeps it on for the course. Surfaced as a small inline `Toggle` next to `CreateCourse.tsx`'s attached-file chips (only shown when files are attached in that submission), sent as a plain `supplementWithWebSearch` form field rather than folded into the free-text interview — a binary preference doesn't need an LLM to parse it, and unlike the interview's own questions, a weak model misreading "yes"/"no" here would silently produce the wrong grounding behavior with no visible failure. `module_generation.py`'s branch condition became `if not module.course.source_materials or module.course.web_search_supplement_enabled` — the only functional change needed, since everything downstream (search planning, Tavily fetch, chunk, embed, unified per-activity vector retrieval) already existed from the document-RAG work; a supplemented course's index just ends up with both document and web chunks. Live-verified: a course with an uploaded document and the toggle on came back with citations correctly blending the document (no url) and three genuine web sources (with real urls).

## "Keep going / dive deeper / branch off" from a completed course (Phase 2, DONE)

Closes the last gap the PRD had already named ("From a completed course, a learner can start a new one that goes deeper into the same topic... or branches into a related topic. Either path creates a new course rather than editing the finished one.") but that nothing in the code actually detected: `Course.stage` only ever reached `interview -> outline_review -> active`, `"completed"` was never assigned anywhere, and `complete_activity()` silently did nothing when there was no next module to unlock.

Two small changes, no new mechanism: `app/routes/activities.py::complete_activity()` now sets `course.stage = "completed"` in the branch where `next_module is None` (this was the last module), instead of the unlock-next-module logic that branch used to only skip past. "Keep going" and "branch into something related" are, per the PRD's own framing, the *same* mechanism — the distinction is the learner's stated intent in the interview that follows, not two code paths — so this reuses the existing Branch Off machinery (`Course.parent_course_id`, `start_course(..., parent_course_id=...)`) rather than building anything new.

Frontend: `CourseHome.tsx` gained a `course.stage === 'completed'` branch ahead of the existing "currently on" card, showing a "Course complete" state with a "Keep going" button that calls `navigate('/create', { state: { parentCourseId: course.id } })` — identical to `Lesson.tsx`'s existing "Branch off" button. `CourseCard.tsx` (used by `MyCourses.tsx`) shows a small "Completed" `Badge` next to the title. `ModuleCompletionModal.tsx`'s `onChangeThisCourse` prop became optional; `Lesson.tsx` omits it when the just-finished module was the course's last one (nothing ahead left to redirect), and the modal's caption text adjusts accordingly. `Library.tsx`/`Today.tsx` deliberately left unchanged — surfacing completed courses there is a plausible follow-up, not part of this scope. No migration needed (`Course.stage` was already a plain string column, `CourseStage` already included `'completed'` on the frontend). Live-verified end-to-end against the real dev backend and real Ollama: completed every remaining activity of a real seeded course (generating its last two modules' content live along the way), confirmed `stage` flipped to `"completed"` and persisted across a fresh `GET`, and confirmed in the browser that `CourseHome` shows the new completed state and `MyCourses` shows the badge.

## Learning Objectives — weekly activity-count goal (Phase 2, DONE)

Per the PRD's Learning Objectives section: an optional, standing (not per-course) personal goal for how
many activities to complete each week, shown as progress on the Today dashboard, no penalty for missing
it.

New nullable `Activity.completed_at` (`DateTime`), set in `app/routes/activities.py::complete_activity()`
alongside `status = "completed"`, serialized as `completedAt` (ISO string or `null`). New nullable
`UserSettings.weekly_goal_activities` (`Integer`) — `None` doubles as both "no goal set" and the "cleared"
state, so `PUT /api/settings`'s existing `if "key" in body: settings.field = body["key"]` pattern needed
no new logic to support clearing (a JSON `null` in the body already assigns `None`); the route rejects a
non-positive provided value with a 400. One migration for both new nullable columns, no `server_default`
needed.

Deliberately **no new backend endpoint**: the frontend already fetches every course (and now every
activity's `completedAt`) on load, so "how many activities completed this week" is computed client-side
from data already in hand — new `frontend/src/lib/weekHelpers.ts` (`startOfWeek()`, most recent Monday
00:00 local time; `countActivitiesCompletedSince()`, flattens every course → module → activity). This
recomputes live from real timestamps with no stored/reset state to manage, matching the project's
preference for the smallest solution that fits.

Frontend: `Settings.tsx` gained a "Learning Objectives" `Card` following the existing
toggle-enables-a-companion-field pattern (same as `embeddingUseCompletionCredentials`) — a `Toggle` keyed
off `weeklyGoalActivities != null`, and when on, a number `Input` using the established
local-draft/`onBlur`-save pattern; turning the toggle off clears the goal immediately (`{
weeklyGoalActivities: null }`), not deferred to blur. `Today.tsx` gained a small progress card ("X of Y
activities this week" + `ProgressBar`), shown only when a goal is set, placed above the existing
"Continue learning" card — no color-coding or messaging for under/over goal, per the PRD's no-penalty
framing. Live-verified against the real dev backend: set a goal via `PUT /api/settings`, completed a real
activity via the actual HTTP API, confirmed `completedAt` landed correctly and the goal set/cleared
correctly through the real endpoint.

## Course thumbnail image generation (Phase 2, DONE)

Per the PRD: real generated images for course/module thumbnails, replacing today's placeholders. Scoped
with the user to **course thumbnails only** — Module has no thumbnail field or UI slot today, real added
scope not part of this pass. Confirmed via direct inspection of the installed `litellm==1.56.4`:
`image_generation()` only supports OpenAI and Azure — no Anthropic, no Ollama/BYOM. Built and structurally
verified without a real OpenAI call (the dev environment had no key configured at the time); the user
does the first live verification themselves once they add one.

New independently-configurable model role, mirroring the embedding-model role exactly: `UserSettings`
gained `image_generation_model`/`image_generation_use_completion_credentials`/`image_generation_api_key`,
and `model_selection.py::resolve_image_generation_config()` mirrors `resolve_embedding_config()`'s tier
branching (raises `ImageGenerationNotConfiguredError` when unset, outside test mode). New
`app/services/image_generation.py::generate_thumbnail_image()`, mirroring `embedding.py`'s mock-branch/
real-branch structure — the real branch requests `response_format="b64_json"` from
`litellm.image_generation()` specifically so the image is saved permanently on disk rather than a
provider-hosted URL that can expire. New `app/services/thumbnail_storage.py` (mirrors
`content_storage.py`/`source_material_storage.py`'s instance-relative path convention) and new
`Course.thumbnail_image_path` column — `thumbnail_url` itself is untouched, still always the gradient
fallback string every course gets by default.

Generation triggers in `course_generation.py::approve_outline()`, right where course-context compaction
already runs (the first point a course has a real title/description, unlike creation time when it's still
"New Course"), wrapped in a best-effort helper (`_generate_thumbnail_if_enabled()`) that never raises —
an unconfigured or failing model just leaves the course on its gradient fallback, same "don't let an
optional enhancement break the core flow" precedent as visual aids. New `GET /api/courses/<id>/thumbnail`
route serves the image inline; `Course.to_dict()` gained a new `thumbnailImageUrl` field (not an overload
of `thumbnailUrl`, so the frontend never has to guess whether that string is a CSS class fragment or a
URL) pointing at it when an image exists. Frontend: all 3 render sites (`CourseCard.tsx`, `Today.tsx`,
`CourseHome.tsx`) gained the same conditional (`thumbnailImageUrl` present → real `<img>`, else the
existing gradient `<div>`); `Settings.tsx`'s hosted-tier branch gained an "Image generation model"
sub-section, structurally identical to the embedding-model one right above it; the pre-existing but
previously-dead `thumbnailGenerationEnabled` toggle is now real and its description updated accordingly.

**Verification**: 372 backend tests passing (was 346) — new `test_image_generation.py`/
`test_thumbnail_storage.py`, extended `test_model_selection.py`/`test_course_generation.py`/
`test_courses_routes.py`/`test_settings_routes.py`. A real-mode structural test (monkeypatched
`litellm.image_generation`) proves the correct request gets built, substituting for a live call. Migration
verified upgrade/downgrade/upgrade against the real dev DB. The fallback path itself *was* live-verified
against the real dev backend: with no image model configured (the actual dev state), approving a real
course's outline through the real HTTP API against real Ollama succeeded normally, `thumbnailImageUrl`
stayed `null`, and `thumbnailUrl` was untouched.

## Phase 1: Docker Compose for local development

Thirteenth build slice. The PRD's Technical Constraints section says deployment isn't Docker-first, to keep the door open for a later Electron/Tauri desktop wrapper; that's about how the app eventually gets *packaged and distributed*, and is unchanged by this slice. This is purely a local development convenience: `docker compose up --build` now replaces manually running `npm run dev` and `python run.py` in two terminals.

### `backend/Dockerfile` and `frontend/Dockerfile`
Both are dev-mode images, not production builds: the backend runs `flask db upgrade && python seed.py && python run.py` (Flask's own debug reloader, same as native), and the frontend runs `vite --host 0.0.0.0` (Vite's own dev server, same as native `npm run dev`). Neither does a multi-stage/production build (no gunicorn, no nginx, no static asset bundling); that's out of scope for what was asked and would need its own decisions about a WSGI server and a static file host if it's ever needed.

### `docker-compose.yml`
Bind-mounts `./backend:/app` and `./frontend:/app` into their respective containers, so edits to source on the host take effect immediately without a rebuild, matching the native hot-reload workflow this is replacing. Bind-mounting the whole `backend/` directory also means `instance/bonsai.db` and generated module content land directly on the host filesystem (no separate named volume needed), so data survives `docker compose down` the same way it survives stopping the native dev server. The frontend adds an anonymous volume over `/app/node_modules` so the container's own `npm install` (run at build time, for the container's Linux/architecture) isn't shadowed by whatever `node_modules` exists on the host.

### `run.py`: `BONSAI_HOST`
Flask's dev server binds to `127.0.0.1` by default, which is unreachable from the host machine despite Docker's port mapping (`127.0.0.1` inside a container refers to the container's own loopback, not the host's). Rather than hardcode `0.0.0.0` (which would expose the dev server on the LAN for native runs too), added a `BONSAI_HOST` env var, defaulting to the old `127.0.0.1` behavior for native runs; `docker-compose.yml` sets it to `0.0.0.0` for the containerized case only.

### Verified
Docker wasn't available in this dev environment at first (WSL without Docker Desktop's WSL integration enabled); once enabled, `docker compose up --build` was run for real. Both containers built and started cleanly: migrations applied, seed skipped (courses already existed in the bind-mounted `instance/bonsai.db`), Flask and Vite both serving on `0.0.0.0`. Confirmed reachable from the host (`curl localhost:5000/api/health`, `localhost:5173` in a browser) and confirmed hot reload actually works (editing `content_storage.py` while the container ran triggered Flask's reloader; editing `tailwind.config.ts` triggered a Vite page reload), both visible in `docker logs`.

Running the same persistent SQLite database across native and containerized environments (via the bind mount) surfaced two real, pre-existing bugs neither environment alone had exposed:

**`Activity.content_path` was stored as an absolute host path.** `content_storage.py`'s `save_activity_content` returned `str(directory / filename)` where `directory` was built from `current_app.instance_path` — an absolute path that's necessarily different inside a container (`/app/instance/...`) than on the host (`/home/.../backend/instance/...`), even though bind-mounting means it's literally the same file. Activities generated natively 404'd when read from inside the container. Fixed: `content_path` is now stored relative to `instance_path` (`module_content/<id>.json`), reconstituted against `current_app.instance_path` at read time; `load_activity_content` still accepts a legacy absolute path too (checked via `Path.is_absolute()`), so nothing already-generated broke further. The 10 activities already in the shared dev database (with old absolute paths) were repaired in place with a one-off script rewriting `content_path` to be instance-relative.

**Course thumbnail gradients silently depended on stale Tailwind dev-server cache.** `Course.thumbnailUrl` (e.g. `"from-emerald-950 to-emerald-800"`) is a Tailwind class-pair chosen server-side (`seed.py`, `course_generation.py`) and only ever appears as a template-literal-interpolated value in frontend components (`CourseCard.tsx`, `CourseHome.tsx`, `Today.tsx`) — the literal strings never appear in any file Tailwind's `content` glob scans, so its JIT compiler has no way to know these utility classes are needed. This coincidentally rendered fine in a long-running native `npm run dev` process only because those exact literal strings used to live in frontend fixture files from Phase 0 (removed once the frontend switched to real API data) — Tailwind's JIT accumulates discovered classes for a dev server's lifetime and doesn't prune them, so an old, continuously-running dev server kept "remembering" them. A fresh container's `npm install` + cold `vite` start has no such memory and never generates the CSS at all. Fixed with an explicit `safelist` in `tailwind.config.ts` listing every gradient pair currently in use (a small, known, finite set today; `thumbnailUrl` becoming an actual generated-image URL later, per the PRD's image-generation plans, would make this whole scheme moot anyway, so a bigger dynamic-safelist mechanism isn't worth building now).

## Phase 1: Generated content is never "locked"; only "not yet generated" is

Fourteenth build slice. The activity/module lock model previously treated "locked" as meaning two different things: a module whose content hasn't been generated yet (correct, still true), and an activity within an already-generated module that just hasn't been reached in position order yet (wrong, per this slice). The latter contradicts Bonsai's whole premise: the learner reshapes their own path, so if a lesson already exists, they should be able to jump to it, not be gated by having finished the ones before it.

This was possible to fix cleanly because of how generation already works: `module_generation.py` creates all of a module's activities in a single call. There's no state where some of a module's activities exist and others don't — a module's content is either fully generated or not generated at all. So "locked" only ever needed to describe a whole module, never an individual activity within one that already exists.

### Backend
`module_generation.py` now marks every generated activity `"available"` (previously only the first one; the rest were `"locked"`). `routes/activities.py`'s `complete_activity` dropped the per-activity unlock-cascade entirely (there's nothing left to unlock: nothing is ever created locked), keeping only the module-level cascade — completing a module's last activity marks it completed and flips the next module from `locked` to `in_progress`, which still triggers generation via `CourseHome.tsx`'s existing lazy trigger. `seed.py`'s Module 2 fixture used to include three additional `"locked"` activities (previewing titles for lessons that, in the real app, wouldn't exist as rows at all until generated) — removed, since that pattern no longer reflects reality; the module now just has the three activities that would actually exist at this point in a real course. The three stray `"locked"` activities already sitting in the shared dev database were deleted directly to match.

### Frontend
`ActivityStatus` dropped `'locked'` (now just `'available' | 'completed'`); `ModuleStatus` keeps it, since a module not yet generated is still a real, valid state. `CourseHome.tsx` and `TableOfContents.tsx` both had an `isLocked`-branching activity row (grayed out, no `<Link>`, a lock icon) that's now dead by construction — simplified both to always wrap an activity row in a `<Link>`, distinguishing only completed (checkmark) vs. not-yet-completed (circle). Module-level locking (grayed out, unclickable, "Not generated yet") is unchanged — that's the one place "locked" still means something real.

### Verified
Backend: full test suite (`test_module_generation.py`'s activity-status assertions, `test_activities_routes.py`'s unlock-cascade tests, both updated to the new model) passes, 121 tests. Frontend: `tsc --noEmit` and `npm run build` both pass with `'locked'` removed from `ActivityStatus`, and both running Docker containers picked up every change live (`docker logs` shows the backend reloading and the frontend hot-updating `CourseHome.tsx`/`TableOfContents.tsx`/`types/course.ts`) without a rebuild.

## Phase 1: Course progress estimates ungenerated modules as remaining work

Fifteenth build slice, small. `Course.progress_percent` was computed purely from generated activities (`completed / total_generated`), so a course showing 100% only meant "every module generated *so far* is done" — a course with 2 of 4 modules generated, both fully completed, read as 100% even though half the course doesn't exist yet. Caught by inspecting live dev data after the previous slice.

`Course.progress_percent` (`app/models.py`) now counts a module with no activities (not generated yet) as `ASSUMED_ACTIVITIES_PER_UNGENERATED_MODULE = 5` activities of unfinished work in the denominator, instead of contributing nothing. `5` is a rough placeholder matching `module_generation.md`'s own "3 to 6 activities" instruction to the model, not a value meant to be hit exactly — the goal is just "don't show 100% while most of the course hasn't been built," not a precise remaining-time estimate. A course with every module already generated is unaffected (denominator is exactly the real activity count, same as before).

### Verified
`test_models.py` covers the new case directly (1 completed activity in a generated module + 1 ungenerated module = `1 / (1 + 5)` ≈ 16.7%, not 100%); the existing single-fully-generated-module test in `test_serialization.py` still asserts a clean 100% to confirm the estimate doesn't kick in when it shouldn't. Full suite passes (122 tests). Checked against the live dev database via `docker exec`: `gpu-programming` (2 of 4 modules generated) now reads 41.2% instead of 100%; the two courses with only their first module generated read close to 0%, correctly reflecting that most of the course is still unbuilt.

## Phase 1: `docs/todo.md` cleanup — progress rounding, stuck-generation retry, About page, content-policy prompts

Sixteenth build slice, five small independent items batched from `docs/todo.md`, cleared from that file once done.

`Course.progress_percent` now returns `round(100 * completed / total)` (a whole int) instead of `round(x, 1)` — the extra decimal digit read as false precision for what's already a rough estimate (see the previous slice).

The "Generating..." state in `CourseHome.tsx` could hang forever on a failed request: the `useEffect` that auto-triggers `generateModuleActivities` for the first zero-activity `in_progress` module fired-and-forgot with no error handling. `AppDataContext.generateModuleActivities` now rethrows after logging (it was swallowing the error); `CourseHome.tsx` tracks a `failedModuleId` and renders "Generation failed." plus a Retry button (re-invokes the same call) instead of leaving the placeholder spinning indefinitely.

The About page (`About.tsx`) was redesigned: a logo badge (`h-16 w-16`) and "Bonsai" title (`text-4xl`) sit inline with a tight gap, tagline below, and the whole page content is vertically centered (`min-h-full flex flex-col justify-center`) rather than starting at the top. Copyright moved off the About page entirely into a persistent, discreet fixed element in `AppShell.tsx` (`fixed bottom-2 right-3 text-gray-400`, "Nigel Story © {year}"), visible on every page instead of only the one a learner might never visit.

`UserPolicy.tsx` claimed an "automated check at course-creation time" for content policy that didn't actually exist anywhere in code. Fixed by making the claim true: policy enforcement was split into three tiers (provider-level safety the hosted LLM already handles / Bonsai-enforced in its own prompts / disclosed-only, left to the model), and a "Content policy" section was added to all three generation prompts then in use (`course_interview.md`, `course_outline.md`, `module_generation.md` — the last one was later deleted by the module-generation rework below, but its content-policy wording carried over to `module_activity_generation.md`): decline illegal topics, require medical/legal disclaimers, flag esoteric topics against consensus, stay neutral on religion/politics. `docs/bonsai_initial_idea.md`'s "Restrictions & Disclaimers" section (the original six-item list) is the source both the PRD's condensed version and this prompt wording trace back to.

## Phase 1: Settings secret-key save feedback

Seventeenth build slice. The API-key and Tavily-key fields in `Settings.tsx` are write-only drafts (never re-show a stored secret, per the earlier API-key-display design) that cleared on blur regardless of whether the save actually succeeded — a silent failure looked identical to success, and a failed save threw away whatever the learner had just typed. Caught from a real user report, not proactively.

`AppDataContext.updateUserSettings` now rethrows after a failed call (matching `generateModuleActivities`'s pattern from the previous slice) instead of only logging. A new `KeyInput` wrapper component (`Settings.tsx`) shows a green check or red X inline in the field plus "Saved." / "Failed to save — try again." text below it, and keeps the draft on failure instead of clearing it, using the same save-on-blur convention as every other Settings field. Every other `updateUserSettings` call site (toggles, segmented controls, model-name fields, `UserMenu`'s username edit) was routed through a small `save()` wrapper (or an inline `.catch(() => {})`) so the new rethrow doesn't surface as an unhandled-rejection warning at those call sites, which don't need per-field feedback the way a secret does. Also removed stale Tavily-card copy that still claimed "the retrieval agent isn't built" — it was, by the Twelfth build slice.

`docs/course_creation_websearch_flow.md` was added this slice too: a design note (not code) sketching the intended shape of course-context compaction, per-activity search planning, and sequential activity generation with a learning-history digest. It's the source document the next slice's plan is built from.

## Phase 1: Module-generation rework — planned activities, deterministic per-activity search, sequential generation, learning-history digest

Eighteenth build slice, and the largest single rearchitecture since course creation itself. Rolled out as six reviewed sub-slices (A–F) against a plan matching `docs/course_creation_websearch_flow.md`. Supersedes the Twelfth build slice's `retrieval_agent.py`/`run_agent()` tool-calling loop for module generation: that file and its tests are kept as-is in the repo (a possible future in-course Q&A feature could reuse it) but are no longer called from anywhere in the generation path.

The problem being solved: the old flow decided a module's activities and did all of a module's Tavily searching *inside a single model call* via tool-calling (`run_agent`), which is unreliable on weaker BYOM models (a model that never emits `tool_calls` just silently never searches) and gives the model no visibility into what a module will actually contain until it's already generating it.

**A — Schema foundation.** Added `Course.context_summary` (JSON, nullable), `Module.activity_plan` (JSON, default `[]`), `ConversationMessage.module_id` (nullable FK to modules, so a digest message can be tied to the module it summarizes), `UserSettings.deep_search_enabled` (bool, default `False`). Migration `08d567a6683f`, hand-fixed to add `server_default` for the two `NOT NULL` columns so it applies cleanly against the real dev DB's existing rows (matching the existing `stage` column's precedent), and to name the new FK constraint explicitly.

**B — Outline gains activity plans.** `CourseModuleSchema` (`llm_schemas.py`) gained `plannedActivities: list[PlannedActivitySchema]` (`{type, title, plan}`, defaulting to `[]` for graceful degradation against older/weaker model output). `course_outline.md` now asks for a per-module 3–6-activity plan (mix of formats, ending in an assessment or capstone) — this is the same guidance that used to live in `module_generation.md` alone, now decided at outline time instead of module-generation time. `_apply_outline()` populates `Module.activity_plan` from the schema.

**C — Course-context compaction.** New `CourseContextSchema{summary, learnerProfile, keyDecisions}` and `app/prompts/course_context_compaction.md`; new `app/services/course_context.py` with `compact_course_context()`, `render_course_context()`, and `assemble_learning_history(course, up_to_module_position=None)` (course context plus prior modules' digest messages, sorted by module position — not insertion order, since a learner could revisit modules out of sequence). `approve_outline()` calls `compact_course_context()` right after flipping `stage` to `"active"`, storing the result on `Course.context_summary`.

**D — Deep-search toggle.** `retrieval.py`'s `web_search()` gained `search_depth: str = "basic"`, threaded into the Tavily request body. Surfaced as `UserSettings.deepSearchEnabled`, with a matching toggle in the Settings.tsx Retrieval (Tavily) card. Not yet read by anything generation-side — that's Slice E.

**E — Per-module search planning + retrieval.** New `ActivitySearchPlanSchema`/`ModuleSearchPlanSchema` and `app/prompts/module_search_terms.md`; new `app/services/module_retrieval.py`: `plan_activity_searches(module, model_config)` makes one LLM call per module (sees the whole `activity_plan` at once, returns search terms per activity index, validated to cover every planned activity exactly once) and `retrieve_for_module(module, search_plan, tavily_api_key, deep_search)` runs the actual searches (up to 3 terms per activity, deduped by URL, capped at 3 results per activity; `deep_search=True` threads `search_depth="advanced"` from Slice D; no Tavily key means every activity maps to `[]`, no network calls). Results are in-memory only for the one `generate_module_activities()` call that uses them — nothing new is persisted beyond what per-activity `citations` already capture. Nothing calls this module yet; wiring it in is Slice F.

**F — Sequential chat-history generation + digest, and cleanup.** `module_generation.py` rewritten: `_generate_activities_content()` calls `plan_activity_searches()` + `retrieve_for_module()` once per module, then generates activities one at a time, each call's `messages` list carrying every prior turn (seed message plus each earlier activity's turn and response) so activity N's prompt genuinely includes activity N-1's actual generated content, for cohesion across a module. After all activities persist, one more call produces a `ModuleDigestSchema`, stored as a `module_learning_digest` `ConversationMessage` row — this is what `assemble_learning_history` (Slice C) feeds to later modules. New prompts `module_activity_generation.md` and `module_digest.md`; per-activity turn messages are built in plain Python (`_activity_turn_message()`), matching the project's convention that structured-data formatting stays in code while only real instructional wording lives in `.md` files. **Deleted**: `app/prompts/module_generation.md`, `ModuleActivitiesSchema`, and the `run_agent`/Tavily-key-conditional branch in `module_generation.py` — the new flow removes tool-calling reliance from module generation entirely, a reliability improvement for BYOM as much as an architectural one, per an explicit confirmation with the user not to keep the old path as a fallback.

Two incidental fixes surfaced by this slice's real-Ollama verification, unrelated to the rearchitecture itself: `course_context_compaction.md` didn't state strongly enough that `summary`/`learnerProfile` must be plain strings, so real llama3 nested them as objects and failed schema validation — tightened the prompt wording. Separately, `validate_llm_json()`'s strict `json.loads()` rejected literal newlines inside JSON string values, which real models (confirmed with llama3) routinely emit in long free-text fields despite being told not to — switched to `json.loads(text, strict=False)`.

### A disclosed BYOM limitation, not fixed
Real end-to-end verification against local llama3 (interview → outline → compaction → first module) worked cleanly through the first activity, but the second activity's response came back as an unterminated JSON string — confirmed via a raw `litellm` call that this wasn't a hard `max_tokens` cutoff. The likely cause: Ollama's default context window (`num_ctx`, often ~2048 tokens for llama3) getting pressured by the sequential design itself, since each activity's prompt carries every prior activity's full generated content, so cumulative prompt size grows within a module. This is a real operational risk of the chosen design specific to small-context local/BYOM models, not a bug in the wiring, schema validation, or control flow. Flagged to the user rather than silently patched; the user's decision was to accept it as a disclosed limitation for now (documented in `module_generation.py`'s module docstring, mirroring `retrieval_agent.py`'s earlier tool-use-reliability caveat) rather than add `num_ctx`/`max_tokens` config or history-trimming — revisit if this proves common in practice.

### Verified
Backend test suite grew from 122 to 165 tests across the six sub-slices (schema/model tests for A; outline/mock tests for B; nine compaction tests including an out-of-insertion-order digest test for C; retrieval/settings tests for D; ten tests covering both index-validation failure modes, dedup, cap, and deep-search threading for E; and F's rewritten `test_module_generation.py`/`test_module_generation_llm_validation.py`/`test_module_generation_retrieval.py`, including a real-mode test proving module 2's search-plan prompt actually contains module 1's digest text). Each migration (`08d567a6683f`) was verified upgrade → downgrade → upgrade against the real `instance/bonsai.db`, not just the test suite. `seed.py`'s ungenerated modules got hand-written `activity_plan`s so they remain generatable under the new flow. A follow-up parallelized `module_retrieval.py`'s per-activity searches with a `ThreadPoolExecutor` (independent I/O, no extra Tavily credits spent, just less wall-clock time), needing the Flask app context explicitly propagated into each worker thread since `current_app` doesn't cross thread boundaries on its own; 2 more tests, one proving real concurrency. 167 tests passing overall by the end of this slice.

## Phase 1: Real document ingestion

Nineteenth build slice, six sub-slices, closing out the Phase 1 gap flagged since the course-creation slice: attached documents were UI-only (`URL.createObjectURL`, nothing parsed or persisted). Real extraction now informs the interview from the first attached file onward, grounds the outline, and — when a course has source materials — module generation skips Tavily search entirely and grounds activities in the document text instead.

**1 — Text extraction.** New `app/services/document_extraction.py`: `extract_text(filename, content) -> str` dispatches on extension (`.txt` decoded with `errors="replace"`; `.docx` via `python-docx`, paragraphs only; `.pdf` via `pypdf`, per-page text). `MAX_EXTRACTED_CHARS = 20_000` hard cap applied once here, so no downstream caller needs its own. Unsupported extension, a parse failure, or an empty/whitespace-only result all raise a single `DocumentExtractionError`. New deps `pypdf`, `python-docx`. Deterministic parsing, no `LLM_TEST_MODE` branch needed.

**2 — Storage.** `SourceMaterial.file_path` renamed to `text_path` (it points at the *extracted* text, not the original file, mirroring `Activity.content_path`'s naming). Migration `9cac6fd7dd41`, hand-fixed into a real column rename (Alembic's autogenerated add+drop would have failed `NOT NULL` against the real dev DB's existing seeded row). New `app/services/source_material_storage.py` mirrors `content_storage.py`'s pattern (plain `.txt`, not JSON, since there's only one field). `seed.py`'s fake `SourceMaterial` fixture on the GPU Programming demo course (never pointed at a real file) was dropped — it would have crashed the document-grounded generation branch added in Slice 5.

**3 — Upload routes + `course_generation.py`.** `POST /api/courses` and `POST /api/courses/<id>/interview-messages` switched from JSON to multipart form data (`message`/`answer` as form fields, `files` as zero or more file parts). New `course_generation.py::_ingest_source_materials(course, files)` extracts and saves each file's text and adds a `SourceMaterial` row, called **before** `_advance_interview()` (so the first follow-up question can already reflect an attached document) and before the function's single `db.session.commit()`, so a `DocumentExtractionError` mid-call leaves nothing persisted — not the course, not the interview message, not any file already processed in that same call. Route layer turns `DocumentExtractionError` into `422` via `jsonify(...)` directly (not `abort()`, which returns HTML the frontend would just discard).

**4 — Interview + outline prompt grounding.** New `course_context.py::render_source_materials(course, max_chars=None)` (each material's text under a `--- filename ---` header). `_next_interview_step()` passes it with a tighter `INTERVIEW_SOURCE_MATERIAL_CHAR_BUDGET = 6_000` cap (re-sent every turn, so it needs its own budget on top of extraction's 20,000-char cap); `_generate_outline_content()` passes it uncapped (a one-shot call). Both prompts gained a `${source_materials}` block. **A real bug caught by this slice's own tests**: Slice 3's `_ingest_source_materials()` had been setting `SourceMaterial.course_id` by hand and calling `db.session.add()` instead of appending to the `course.source_materials` ORM relationship, so `course.source_materials` stayed empty in-memory for the rest of that same request — meaning the interview question and outline would never actually have reflected an attached document, despite Slice 3's own (HTTP-response-only) tests passing. Fixed by appending to the relationship instead.

**5 — Module generation skips search when document-grounded.** `_generate_activities_content()`'s real-mode branch now checks `if module.course.source_materials:` — true skips `plan_activity_searches()`/`retrieve_for_module()` entirely (`search_results = {}`); false is the unchanged search-grounded path from the previous slice. `_seed_prompt()` passes `render_source_materials(module.course)` into `module_activity_generation.md`, which gained its own `${source_materials}` block and reworded citation instructions: citations only for real web results, omitted entirely for document-grounded content.

**6 — Frontend wiring.** New `ApiError` class in `api.ts` (distinguishes a backend-supplied user-facing message from a generic network/status failure); `request()` stops hardcoding a JSON `Content-Type` when the body is `FormData`. `startCourse`/`submitInterviewAnswer` now take a `files: File[]` param and send `FormData`. `CreateCourse.tsx`'s `handleSubmit` sends `attachedFiles` with both calls, clears them only on success (kept on failure so a learner can drop the bad file and retry), and catches `ApiError` specifically to show the real backend message instead of a generic one; file input `accept` restricted to `.txt,.docx,.pdf`. `OutlineReview.tsx` dropped its old `location.state.files` read (a Phase-0-era workaround from before real persistence existed) and renders `course.sourceMaterials` from the already-fetched course instead.

### Verified
Backend suite grew from 177 (start of this slice) to 199 tests, including two real bugs caught by the slice's own tests (Slice 4's relationship-vs-manual-FK bug above) rather than found later. Real end-to-end verification against local Ollama/llama3 with no Tavily key configured at all and a real `.txt` document attached: the interview's first question already reflected the document's actual content, the outline title matched the paper almost verbatim, compaction captured it correctly, and module generation succeeded fully grounded in the document text — proving the skip-search branch works in the real pipeline, not just under mocks. Frontend: `tsc --noEmit` and `npm run build` both clean (no frontend test suite exists in this repo). Manual click-through of the upload flow in a real browser is the one step this session couldn't do itself and is still pending from the user.

## Phase 1: Interview/generation polish, then prompt-construction rework

Twentieth build slice. Started with a few small fixes found in live dev use: a "Parsing document..." chat placeholder in `CreateCourse.tsx` during file upload (a new `sending` state disables the input while a request is in flight); the interview's 10-question cap (`MAX_INTERVIEW_QUESTIONS`) made a real hard stop in code for real-mode calls too, not only the `LLM_TEST_MODE` mock; `course_interview.md` reworded to bias the model toward a broad default course scope instead of drilling into specifics the learner never asked for.

Then a three-slice prompt-construction rework (plan-driven, one review checkpoint per slice): every `complete()` call now uses the standard `[{"role": "system", ...}, {"role": "user"/"assistant", ...}, ...]` message-list shape, replacing the old pattern of one giant `role: "user"` string with instructions, flattened history, and data all mashed together. Attached documents also gained a short (≤3 sentence) LLM-generated summary (`SourceMaterial.interview_summary`, migration `e7fd71b62979`) used to shape interview questions, in place of the raw extracted text truncated at 6,000 chars from the previous slice's `INTERVIEW_SOURCE_MATERIAL_CHAR_BUDGET` — outline and module generation are unchanged, still grounded in the full document text.

**Slice 1 (document summaries).** New `document_summary.md`, `DocumentSummarySchema`, `summarize_document_for_interview()` and `render_source_material_summaries()` in `course_context.py`, wired into `_ingest_source_materials()`. Caught a real bug along the way: `resolve_model_config()` calls `UserSettings.get_or_create()`, which commits on first use — once ingestion started calling it, that would have prematurely flushed a not-yet-validated course/message if a *later* attached file in the same call then failed extraction. Fixed by reordering `start_course()`/`submit_interview_answer()` to ingest files before adding the course/message to the session, restoring the "nothing persists on extraction failure" invariant from the Third build slice of the ingestion work above.

**Slice 2 (real conversation turns).** New `conversation_turns(course, kinds)` in `course_context.py`, replacing `_format_history()` everywhere. Since `Course.conversation` already logs everything needed (interview Q&A, revision requests, the presented outline, approval), turning it into real per-role message turns let `course_interview.md`, `course_outline.md`, and `course_context_compaction.md` drop their `${history}`/`${topic}`/`${revision_section}`/`${outline}` placeholders entirely and become pure system-message instructional text.

**Slice 3 (one-shot calls).** Same system+user split applied to `module_digest.md`, `module_search_terms.md`, and `module_activity_generation.md`'s seed message — system stays pure instructions, a Python-built data message (mirroring `_activity_turn_message()`'s existing convention) carries each call's actual structured data.

### Verified
Every slice verified end-to-end against real Ollama/llama3, not just mocks. Backend suite grew from 200 (start of the day) to 209 tests; Slice 2 needed few new tests since most existing coverage ran under `LLM_TEST_MODE`, which never exercised the real prompt-building code path — explicit real-mode structure tests were added for all three call sites rather than relying on old assertions happening to still pass.

## Phase 1: JSON-mode reliability, course-list management, real quiz feedback

Twenty-first build slice, three unrelated fixes/features found in the same live-dev-use session.

**JSON-mode reliability.** A real user-reported bug: the interview would occasionally stop dead with a blank chat bubble. Root cause, found via the actual stuck course in the dev DB: the model had returned `{"done": false, "question": ""}`, which passed `InterviewStepSchema`'s field types (question is legitimately `str | None`) but left nothing to answer. Fixed at the schema level with a `model_validator` requiring a non-empty question when `done` is false, turning the degenerate case into the same clear 502 every other malformed response gets. Investigating further surfaced a second, harder failure mode against real Ollama: the model would return syntactically valid JSON that simply didn't match the requested shape at all (`response_format: {"type": "json_object"}`, added earlier, only forces *valid JSON*, not *this* JSON). Fixed by making `complete()`'s `schema` param drive real schema-constrained decoding — Ollama's native `format` field accepting a JSON schema (not just `"json"`), OpenAI's Structured Outputs, and Anthropic's forced-tool-call translation (confirmed via LiteLLM's own source that it unwraps the tool-call result back into a normal content string). This needed the user to upgrade their local Ollama past 0.5 (older versions hard-reject a schema-shaped `format`, confirmed via direct reproduction) — now documented as a real prerequisite in `README.md`, not just a recommendation. `model_selection.py`'s BYOM routing also switched from `"ollama/<model>"` to `"ollama_chat/<model>"` in the same pass (the plain prefix has a real bug in the installed LiteLLM version when combined with any JSON-format request). A quiz/assessment-specific follow-up below (correctAnswer→correctAnswerIndex) came from the same investigation.

**Course-list management.** `MyCourses.tsx` now filters out courses still mid-interview/outline-review (no real content yet, no way to resume from that list). New "Edit Courses" mode (a new `outline` `Button` variant, green border/text on white — added since no existing variant matched the "New Course" button's green without being visually identical to its solid-fill primary style): toggles select circles on every `CourseCard` (restructured so the circle sits outside the card's `<Link>`, not nested inside it) and swaps the button into an "Actions" dropdown (Delete, disabled until something's selected; Cancel, clears selection and exits). New backend `DELETE /api/courses/<id>` + `delete_course()` in `course_generation.py`: deletes on-disk content (`Activity.content_path`/`SourceMaterial.text_path` files) before the DB row, since SQLAlchemy's `cascade="all, delete-orphan"` only knows about DB rows.

**Real quiz/assessment feedback.** Found while addressing an unrelated user report ("quizzes don't tell you if you're right"): `GeneratedActivitySchema` never captured a correct answer or explanation at all, and the frontend's quiz feedback (`lib/feedback.ts`) was literally Phase-0 placeholder copy, by its own comment "standing in for real LLM-generated feedback." Fixed by having generation produce a `correctAnswerIndex`/`explanation` pair, validated by a new `model_validator` (index must be in range, explanation non-empty). First attempt asked for the correct answer's *text*, required — real-Ollama testing showed this still failed ~50% of the time, since a plain JSON Schema string field can't express "must equal one of these other array values" (a cross-field constraint), so nothing stopped the model from paraphrasing an option instead of copying it verbatim. Switched to an index instead: a small integer is far harder to get wrong than reproducing a string exactly, and any out-of-range value is trivially rejected by the existing validator. Verified 6/6 clean against real Ollama after the switch, versus 3/6 failures with the text-based version. `ActivityCard.tsx`'s `QuizBlock` now locks an option only once it's correct, so learners can retry as many times as they want; right/wrong isn't revealed until a genuine attempt (no leaking the answer on a wrong guess).

### Verified
Real quiz feedback and the JSON-mode fix both verified against real (then real-upgraded) Ollama, including the specific failure modes each fix targeted, not just passing test-suite runs. Course-list management verified via a live smoke test against the running dev backend (create → delete → 404) plus a CORS preflight check for the new `DELETE` method. Backend suite grew to 227 tests.

## Phase 1: Change-direction / fork mid-course — Branch Off and Change This Course

Twenty-second build slice, the last substantive item on Phase 1's deferred list (AI evals having moved to Phase 2 scope in the same session — see the Roadmap section below). Per the PRD's Change-of-Direction section, extended per user direction into two choices at the module-completion check-in, both going through a real multi-turn interview rather than a single feedback box:

- **Branch Off** — a new, separate course (`Course.parent_course_id`, previously unused groundwork from the module-generation rework), original course and its remaining modules untouched. Pulls forward the mechanism Phase 2's "branch off from a *completed* course" will also need.
- **Change This Course** — the PRD's originally-described in-place behavior: discard not-yet-reached modules, generate new ones.

The frontend entry point already existed from Phase 0 — `ModuleCompletionModal.tsx`, rendered by `Lesson.tsx` the moment a module's last activity completes — its `onChangeDirection` callback was a no-op.

**Branch Off turned out to need almost no new machinery.** `start_course()` already does everything it needs (creates a `Course` row immediately, runs interview → outline → approve), so it just gained an optional `parent_course_id` param and a `_parent_context(course)` helper feeding a new `${parent_context}` section in `course_interview.md`/`course_outline.md`. Key simplification found during implementation: no module-position tracking needed at all — a module only gets a `module_learning_digest` once its content is actually generated (lazy, on first reach), so `assemble_learning_history(parent)` with no cutoff already naturally stops exactly at the branch point. `CreateCourse.tsx` reused as-is, parameterized via router state.

**Change This Course needed a genuinely new, smaller flow**, since it doesn't create a course or reach outline *approval* — it replaces modules on an already-`active` course, which has no equivalent "not live yet" stage to hold a pending proposal in. Five new module-scoped service functions in `course_generation.py` (`start_direction_change`/`submit_direction_change_answer`/`generate_direction_change_outline`/`submit_direction_change_feedback`/`approve_direction_change`) mirror the course-creation flow's shape, but the proposed modules are held as a `direction_outline_presented` `ConversationMessage` (JSON dump), re-parsed back at approval time, rather than persisted as real `Module` rows until committed. `approve_direction_change` deletes every module past the completed one and creates new ones from the approved proposal — safe because module generation is lazy, so nothing past a just-completed module has ever had `Activity` rows to begin with. New shared infra: `_add_message`/`conversation_turns` both gained an optional `module_id` filter (backward compatible) so this mini-interview's turns stay scoped to one module's check-in, tagged via `ConversationMessage.module_id`. Two new prompts (`module_direction_interview.md`/`module_direction_outline.md`) and a new `CourseDirectionChangeSchema{modules}` (no title/description/prerequisites — only what's ahead changes). Two new frontend pages, `ChangeDirection.tsx`/`ChangeDirectionReview.tsx`, adapting `CreateCourse.tsx`/`OutlineReview.tsx`'s existing chat/review UI; `ChangeDirectionReview.tsx` reads its proposal from router state rather than re-fetching by id, since unlike course creation's outline there's no persisted resource yet to re-fetch until approval (a hard refresh mid-review loses the unsaved proposal — accepted as a minor edge case, not hardened against).

### Verified
Both slices verified twice: once via direct service-layer calls against real Ollama, once via real `curl` HTTP requests against the live dev backend. A full direction pivot (a GPU/ML course → front-end web dev) stayed on-topic through the interview, the proposal was coherent, revision feedback was honored, and approval correctly preserved the completed module untouched while replacing the rest with properly unlocked new ones. Backend suite grew to 252 tests (18 new: interview/proposal/approval behavior, module-scoped turn isolation, learning-history threading into both new prompts).

## Phase 1: Data export/import — closes out Phase 1

Twenty-third build slice, the last item on Phase 1's deferred list. Per the PRD's Data Export & Import section: courses, module content, and progress as a single portable archive; API keys and other credentials never included. The frontend UI was already fully built from Phase 0 — `UserMenu.tsx` has real "Export My Data"/"Import User Data" menu items, a `.zip`-only file picker, and `ConfirmDialog`/`NoticeDialog` flows with copy that already matched the PRD almost verbatim. Both ended in a "Not wired up yet" notice; this slice is wiring only, no new frontend interaction design.

**Export is a JSON manifest, not a raw SQLite file copy.** Zipping the live DB file directly would risk a snapshot mid-write and require scrubbing two secret columns from a binary copy; instead, `data_export.py`'s `export_data()` dumps every row via the ORM into `data.json`, plus the actual on-disk content files (`module_content/*.json`, `source_material_text/*.txt`) the manifest's `content_path`/`text_path` values point to — the same hybrid storage model this app already uses everywhere else, archived instead of live. The dump is generic (`{column.name: getattr(instance, column.name) for column in instance.__table__.columns}`, one special case for `ConversationMessage.created_at`, the only `DateTime` column anywhere in the schema) rather than a hand-maintained field list per model, so it survives future schema changes without needing separate upkeep.

**Import is a restore, not a merge.** Every existing `Course` (and everything cascading from it, including its on-disk content files) is deleted first, then rows are re-created from the manifest in FK-safe order. `ConversationMessage.id` (auto-increment, nothing else FKs to it by value) is dropped from the restored fields and left to the target database's own sequence, rather than forcing back the original id and risking a collision. `UserSettings` is the one exception to "restore, not merge": only non-secret fields are overwritten on the existing single row, so whatever API keys are already configured on the *target* installation are left completely untouched — the archive never had them to begin with, and re-importing onto an already-configured installation shouldn't force re-entering keys that still work. New `GET /api/data/export` (streams the zip via `send_file` over an in-memory `BytesIO`) and `POST /api/data/import` (multipart, 422 with a message for `DataImportError` on a garbage/non-Bonsai archive) in a new `app/routes/data.py`.

### Verified
Backend suite grew to 266 tests (14 new): export/import round-trip, secret exclusion, content-file fidelity, replace-not-merge semantics, settings-merge semantics, invalid-archive rejection. Also verified against the real dev database directly: exported all 63 real seeded/test courses, confirmed secrets excluded, then imported that real archive into an isolated throwaway database (not the live one, since import is destructive) and confirmed every course round-tripped correctly — proving the archive is genuinely portable to a new installation, not just internally consistent under test.

**Phase 1 is now complete.** Every item on the Milestones' Phase 1 line is built and verified against real Ollama: course creation (interview → outline → approval, document-grounded or branched), incremental retrieval-grounded module generation, exercises/assessments with real feedback, change-direction/fork behavior, and data export/import. What's ahead is Phase 2 (rich media, in-course visual aids, "keep going/branch off" from a *completed* course, BYOM refinement, learning objectives) and Phase 3 (polish, semantic search, community readiness).

## Document RAG: chunking + vector store (Phase 1 continuation, DONE)

Same day as Phase 1's completion, prompted by a real problem the earlier module-generation rework hadn't solved: a document's full (20K-char-capped) raw text went into the outline prompt once, then into *every* module's growing chat history again, so a bigger document made every generation call more expensive and more likely to hit the context-window truncation already disclosed in the module-generation-rework section above. Planned via `/plan` (compared FAISS, ChromaDB, sqlite-vec, and LangChain's FAISS wrapper; landed on plain `faiss-cpu`, no LangChain), built in 7 reviewed slices, each verified live against real Ollama.

- **Page-aware chunking.** `document_extraction.py` gained `extract_pages()` (`(page_number, text)` pairs; `page_number` is `None` for `.txt`/`.docx`) underneath the existing `extract_text()`. New `document_chunking.py::chunk_pages()`: recursive paragraph → sentence → hard-character-split fallback, packed back up toward `CHUNK_SIZE=1_500` chars with `CHUNK_OVERLAP=150`, never spanning two pages (so every chunk has one unambiguous page for citations).
- **Embeddings + vector store infra.** New deps `faiss-cpu`, `numpy`. `model_selection.py::resolve_embedding_config()` mirrors `resolve_model_config()`'s tier branch, raising `EmbeddingNotConfiguredError` if unset (no safe universal default embedding model exists across both tiers, unlike completion). New `embedding.py::embed()`. Found and worked around a real upstream bug: the installed `litellm==1.56.4`'s Ollama embeddings path (`ollama_aembeddings`) raises `TypeError: object dict can't be used in 'await' expression`, confirmed live; fixed by calling Ollama's own `/api/embed` endpoint directly via `requests` for `ollama/`-prefixed models, bypassing `litellm.embedding()` for that case only (hosted-tier embeddings still go through litellm normally). New `vector_store.py`: one FAISS `IndexIDMap(IndexFlatIP(...))` per *course* (not per document, since a course's modules should draw from every attached material jointly), L2-normalized vectors for cosine similarity, flat/exact search (deliberate: tens-to-hundreds of chunks per course is trivial at brute force). `build_or_update_index()` (incremental), `query()`, `rank_chunks()` (ranks an in-memory chunk list against a query without touching the persisted index, needed so a document's own ingestion-time summary doesn't blend other attached documents' chunks), `delete_vector_index()` (wired into `delete_course()`). New `Course.vector_index_path` + `UserSettings.embedding_use_completion_credentials`/`embedding_api_key` columns (migration `f8628ffc61a8`).
- **Settings UI**: the previously-standalone "Embedding Model" card merged into "Model Provider." Hosted tier: model name + a "use the same API key as completion" toggle (default on) with a conditional dedicated key field when off. BYOM tier: model name only (reuses the completion endpoint).
- **Ingestion rewire.** `_ingest_source_materials()` now chunks + embeds + updates `course.vector_index_path` for every uploaded file. `summarize_document_for_interview()` retrieves the document's own top-8 chunks against a fixed "overview and main topics" query (via `rank_chunks()`) and summarizes those, not raw full text.
- **Outline stops using raw text.** `_generate_outline_content()` switched from `render_source_materials()` to `render_source_material_summaries()`.
- **The crucial slice: module generation's per-activity vector retrieval.** Replaced the old hard branch (source materials → dump full text into the seed message; else → web search) with: a course with `vector_index_path` retrieves each activity's top-`MAX_CHUNKS_PER_ACTIVITY=4` chunks directly (activity title+plan, embedded, *is* the query; no LLM query-planning call needed, unlike web search, since there's no need to creatively phrase a query against material already in hand); a course with source materials but no index (ingested before this feature existed, or embedding failed) falls back to the old whole-document-in-seed-message behavior; otherwise, unchanged web search (later superseded, see below). `_activity_turn_message()` generalized to a source-agnostic `{"source": str, "content": str}` shape. **Citations for document-grounded reading activities are now attached deterministically in code from the chunks actually retrieved**, not model-authored. Same "don't trust the model with something code can guarantee" reasoning as `correctAnswerIndex` replacing text-matching for quizzes. `CitationSchema.url` → `str | None` (a document citation has no URL).
- **Raised the ceiling, fixed the other named root cause.** `MAX_EXTRACTED_CHARS` 20,000 → 500,000 (~100-125 pages), safe now that nothing downstream dumps the whole thing into one prompt. Separately, `llm.py::complete()` now sets an explicit `num_ctx=8192` (4x Ollama's ~2048 default) for every `ollama`-prefixed model, the other fix `docs/todo.md` had named for the outline/module-generation truncation failures.

### Verified
313 backend tests (was 269 at the start of this feature). Live-verified end-to-end against real Ollama + `nomic-embed-text`: real embeddings, real FAISS round-trip, a semantic query about "GPU parallel threads" correctly retrieved the warp-scheduling chunk over unrelated biology chunks with the right page number, and a full upload → interview → outline → approve → module-generation pass grounded entirely in an attached document with correct deterministic citations. Ollama's `/api/ps` confirmed `context_length: 8192` actually took effect, not just an unused kwarg.

## Multi-document support (Phase 1 continuation, DONE)

User asked for multi-document attachment with a shared vector store keyed by file name. Researched via subagent first rather than assuming, and found this was **already fully implemented** by the RAG rework's own design: one FAISS index per *course*, not per document, was deliberate from the start. `_ingest_source_materials()`'s per-file loop already sets `course.vector_index_path` after each file, so later files in the same call (or a document attached on a later interview turn) append to the same index; the frontend file input already had `multiple`. The one real gap was test coverage: nothing exercised two documents end-to-end. Added 4 tests (multi-file-in-one-call, shared index, a second document attached on a later turn, citations correctly attributing chunks to the right file when two documents are both in the index). No production code changes needed. 317 tests passing (was 313).

## RAG extended to web-search-grounded courses (Phase 1 continuation, DONE)

Before this, web-grounded courses were the one remaining place still using the old pattern: `module_retrieval.py` fetched Tavily results per-activity, `module_generation.py` threaded the raw `{title, url, content}` dicts directly into the prompt, and citations were model-authored. This unified web content onto the exact same per-course FAISS index a document gets, retrieved through the exact same per-activity mechanism (scope deliberately limited to unifying the storage/retrieval *mechanism*; the separate product-level question of a document-grounded course *also* using web search is the "Opt-in web-search supplementing" feature below, planned and built after this).

`document_chunking.py::Chunk` renamed `file_name` → `source` (a field called "file_name" holding a web page's title was wrong, not just incomplete) and gained `url: str | None`. Web content is chunked via the same recursive splitter as documents (`chunk_pages(title, [(None, content)], url=url)`, since a web page has no page concept either). `module_generation.py`'s web-grounded branch still plans + fetches unconditionally (matching prior behavior exactly, including without a Tavily key) but now chunks+embeds the fetched results into `course.vector_index_path` (guarded by `if web_chunks:` so a key-less or empty-results course never pays for an embedding call); a single unified block then queries the vector store per-activity regardless of *why* the index exists. **Web citations are now deterministic too**, same reasoning as documents. `_activity_turn_message()` dropped its `results_label` parameter (no longer varies by source); `module_activity_generation.md` simplified to tell the model to never write `citations` at all.

### Verified
320 backend tests (was 317). Live-verified against real Ollama + a real configured Tavily key: a course created with no documents, after module generation, gained a `vector_index_path`, and a reading activity's citations were four real, deterministically-attached web sources (Britannica, Wikipedia, etc.) with genuine URLs, not the model's own invention.

## Embedding-model fallback for grounding (Phase 1 continuation, DONE)

A real bug found while syncing the PRD against shipped behavior (2026-08-05), not a planned feature: since the RAG rework above, `_generate_activities_content()` called `resolve_embedding_config()` unconditionally in two places, once to embed freshly-fetched web results and once to query an existing `vector_index_path`. That call raises `EmbeddingNotConfiguredError` if no embedding model is set in Settings. Neither call site was guarded, and `POST /api/modules/<id>/generate-activities` didn't catch the exception, so a learner who configured only a Tavily key (never touched the embedding role) got a raw 500 generating any module with search results to ground on, something that worked fine before embeddings existed in this codebase at all. A second, rarer crash point: a course whose index was built earlier (embedding worked at the time) crashes the same way if the embedding model is later cleared from Settings.

Fixed with a best-effort resolver, `_try_resolve_embedding_config()` (returns `None` instead of raising), called once at the top of `_generate_activities_content()`. Both former unconditional call sites now gate on the resolved config being truthy:
- **Web branch**: with no embedding model, skip chunking/indexing entirely and ground each activity directly on its own raw fetched Tavily results (`retrieve_for_module()` already returns them keyed per activity). Citations are still deterministic, since which result went to which activity is already known; just without semantic per-activity relevance ranking.
- **Chunk-retrieval branch**: `if module.course.vector_index_path and embedding_config` (previously just the first half). When false, falls through to `_module_seed_data_message()`'s whole-document raw-text fallback, whose triggering condition changed from "`source_materials` and no `vector_index_path`" to an explicit `use_raw_source_materials` flag the caller computes (`source_materials` present and *no usable index for this call*, which now also covers "index exists but no embedding model to query it with," not just "index was never built").

Also fixed two Settings.tsx copy strings that dated from before this feature and were stale in the opposite direction: one claimed hosted-tier tool-use reliability affects citations (no longer true, citations are code-attached), the other undersold the embedding model's role as document-only (it grounds web retrieval too since the RAG-extension slice above). Added the disclaimer this fix's PRD write-up promised: both embedding-model fields now say what happens without one configured (falls back to raw source text, lower quality).

### Verified
324 backend tests (was 322): two new tests, one per crash point. A web-only course with a Tavily key and no embedding model (asserts `litellm.embedding` is never called, raw content reaches the prompt, citation is still correct) and a document-grounded course with a stale `vector_index_path` and no embedding model (asserts `query_vector_store` is never called, raw document text reaches the seed prompt). Full existing suite re-run clean, no regressions. Frontend `tsc --noEmit` clean.

## Video embedding (Phase 2, DONE)

Closes out Phase 2 entirely — the last item on its Milestones list. Built as scoped, no material changes; full plan at `/home/nastory/.claude/plans/cuddly-hatching-snowglobe.md`, rolled out in 6 slices with review between each. A real YouTube `<iframe>` embed as its own standalone module activity, not AI video generation and not spliced inline into a reading like visual aids. `ActivityType`'s `'video'` and `ActivityCard.tsx`'s old placeholder ("Video embedding arrives in Phase 2.") had been dormant since Phase 0; `GeneratedActivitySchema`/`PlannedActivitySchema` still deliberately exclude `"video"` — see below for why that stayed true even after shipping.

New `UserSettings.video_embedding_enabled` (Boolean, default `False`, migration `3233479dcbab`) — same opt-in/cost-consent precedent as `deep_search_enabled`/`visual_aids_enabled`; only attempted when it's on *and* a Tavily key is configured, independent of document- vs. web-grounding (video is never chunked/embedded into the RAG vector store, unlike everything else that course context feeds into).

**Query and position piggyback on the existing per-module search-plan call, no new LLM call for that part.** `ModuleSearchPlanSchema` (`module_search_terms.md`) gained two *unconditionally required* fields — `videoSearchQuery: str` (empty string = no video fits this module) and `videoPosition: int` (0-based index in the module's final activity list, ignored when the query is empty) — required rather than an `Optional` pair guarded by a validator, per the `InterviewStepSchema` lesson that schema-constrained decoding doesn't enforce a validator's conditional logic, only a field's own required-ness. The prompt tells the model a video could fit anywhere in the module (start/middle/end) based on content, not fixed relative to the closing assessment — confirmed live that the model does place it at different positions run to run, not just at the end.

**A real architectural gap found during implementation, not anticipated in scoping**: `plan_activity_searches()` only ran inside the existing web/document-supplement branch, so a purely document-grounded course with no web supplement never called it at all — which would have silently made video embedding web-only despite the design explicitly committing to "independent of grounding source." Fixed by hoisting a `needs_search_plan` check in `_generate_activities_content()` that also fires when `video_embedding_enabled` is on, regardless of source materials — the one case where enabling the toggle genuinely adds a new LLM call for a course that would otherwise skip search planning entirely. Verified live: a document-grounded course with the toggle on got a video without ever calling `web_search`.

**Model picks among a few real Tavily candidates and writes a caption** — diverges from visual aids' deterministic top-result pick, per explicit user direction. New `video_search(query, api_key)` in `retrieval.py` (mirrors `web_search()`/`image_search()`'s Tavily `/search` wrapper) restricts results via `include_domains=["youtube.com", "youtu.be"]`; a new `extract_youtube_video_id(url)` regex then filters out anything that isn't a real parseable watch/shorts/short-link (a channel, playlist, or search page that slipped past the domain filter). The surviving candidates go to a new prompt (`module_video_selection.md`, new `VideoSelectionSchema{selectedIndex: int, caption: str}`, `selectedIndex: -1` for "none of these fit," both fields unconditionally required same as `ModuleSearchPlanSchema`'s new fields). The model chooses and captions; extracting the actual embeddable video ID from the *chosen* result's real URL stays deterministic code, never model-authored — same "code verifies/attaches what it can" reasoning as citations and `correctAnswerIndex`.

**Never flows through `GeneratedActivitySchema`/`PlannedActivitySchema`** — video content isn't LLM-generated prose, so it doesn't need that schema's `Literal` to include `"video"` at all. It's built directly in `module_generation.py` by a new `_maybe_build_video_spec()` (no-ops gracefully at every failure point: toggle/key off, no query suggested, no candidate with a real id, or the model declining every candidate — all just mean no video this module, not an error) and a new `_ActivitySpec` dataclass + `_generated_to_spec()` adapter, so `generate_module_activities()`'s persistence step builds one uniform `list[_ActivitySpec]` (converted text activities plus the optional video spec inserted at its clamped position) instead of working straight off `GeneratedActivitySchema`. The existing "video" schema-rejection tests needed zero changes, and there's no risk of schema-constrained decoding ever emitting a stray `type: "video"` for an ordinary text activity, since that value is never in either schema's accepted set.

**Frontend**: `Activity` gained `videoUrl`/`videoId`/`caption` as distinct fields; `ActivityCard.tsx`'s placeholder replaced with a real `VideoBlock` — a responsive `aspect-video` `<iframe src="https://www.youtube.com/embed/{videoId}">` in a `<figure>`, caption as a real `<figcaption>` below it, matching `Markdown.tsx`'s `img`-override precedent for embedded external media with a visible caption. New toggle in `Settings.tsx`'s Retrieval (Tavily) card, same `Toggle`/`save()` pattern as `visualAidsEnabled`.

### Verified
344 backend tests (was 322 before this feature — 22 across `test_retrieval.py`/`test_user_settings.py`/`test_settings_routes.py` for Slices A-B, plus 2 for Slice C's new fields, plus 7 in a new `test_module_generation_video.py` and 1 in `test_module_generation_source_materials.py` for Slice D's orchestration and the document-grounded cross-cutting case). Migration verified upgrade → downgrade → upgrade against the real dev DB. Frontend `tsc --noEmit`/`npm run build` clean throughout. **Live-verified end-to-end against the real dev backend, real Ollama (`qwen2.5:7b-instruct`), and a real Tavily key**: ran the actual pipeline inside the running `bonsai-backend-1` container (not just the host, which lacked write permission to the container-owned `instance/` directory) against two different real course/module topics. The model's own judgment on "should this module get one" varied by run and topic — consistent with this project's already-documented pattern of a 7B instruct model being an imperfect but not broken follower of "try to include, don't force it" style instructions (see the interview checklist/coverage-field history above) — but a real video was found, selected, and embedded end-to-end at least once: a genuine Tavily search for "python for and while loops explanation" returned 5 real YouTube results, the model selected one and wrote an accurate caption, the video id (`gD8ePxAhjUM`) was extracted correctly, and it was inserted at the model's chosen position (the very start of the module), with the other two activities shifting down. Verification script not part of the repo.

## BYOM local-model refinement (Phase 2, DONE)

Marked done retrospectively (2026-08-05) rather than as its own build slice. Originally listed as a discrete Phase 2 deliverable, then dropped as "too open-ended to complete as a single item" back on 2026-08-04 — but by the time Phase 2's other items were finished, real BYOM-reliability work had actually landed repeatedly along the way, each time a BYOM-specific failure surfaced during another item's *live* verification (this project's standing practice of never calling a feature done on mocks alone). Revisited and reclassified as done once that pattern was pointed out, rather than reopened as new scope.

What actually shipped, all already narrated in their own build-slice sections above:
- **Ollama routing fix**: `model_selection.py`'s BYOM branch and `llm.py`'s schema-decoding path both route through `"ollama_chat/<model>"` instead of `"ollama/<model>"` — the plain prefix hits a real bug in the installed LiteLLM version (`KeyError: 'name'`) when combined with any JSON-format request, confirmed via direct reproduction.
- **Schema-constrained decoding, unified across tiers**: Ollama models get the Pydantic schema passed via its native `format` field directly (once the user upgraded their local Ollama to a version supporting real JSON-schema-constrained output, not just the literal string `"json"`); hosted providers get `response_format: {"type": "json_schema", ...}`. Found and fixed a *second*, subtler class of bug this exposed: schema-constrained decoding only enforces a field's own required-ness, not a Pydantic validator's conditional logic — `InterviewStepSchema.question` had to become unconditionally required (a discarded placeholder string when `done` is true) rather than `Optional`-plus-validator, after a real reproduction of the exact degenerate `{"done": false, "question": null}` crash. This lesson is now applied by default to every new schema in this codebase, including video embedding's `ModuleSearchPlanSchema`/`VideoSelectionSchema` fields.
- **Explicit context window**: `llm.py::complete()` sets `num_ctx=8192` (4x Ollama's ~2048 default) for every `ollama`-prefixed model, fixing a real context-window-truncation failure class first observed during the module-generation-rework's sequential activity generation.
- **Ollama embeddings bug workaround**: the installed LiteLLM version's `ollama_aembeddings()` path raises `TypeError: object dict can't be used in 'await' expression`, confirmed live; `embedding.py` bypasses `litellm.embedding()` entirely for `ollama/`-prefixed models and calls Ollama's own `/api/embed` endpoint directly via `requests` instead.
- **Interview prompt redesign**: `course_interview.md` reworked around a fixed checklist of 4 topics, each asked about once, plus a required `coverage` scratchpad field the model must fill in before `done`/`question` — a genuine "think before answering" forcing function (Pydantic field order carries through to JSON schema property order, which schema-constrained decoding generates in order), measurably reducing (though on this project's specific weak local model, not fully eliminating) the originally-reported repeat-question behavior.

What's still a disclosed, not "fixed," limitation: a weak local model's multi-turn state tracking (the `coverage` field's own text can be internally inconsistent turn to turn) and the sequential-activity-generation context-growth tradeoff are both named in this codebase as real, accepted BYOM limitations rather than problems Phase 2 solved — refinement here meant "measurably better and several real bugs fixed," not "BYOM now matches hosted quality." That distinction is exactly why this was correctly *not* treated as a single completable item; the incidental fixes above are genuine, verified improvements, not a claim that local-model quality parity was reached.
