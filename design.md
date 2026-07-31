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
- **Document upload is UI-only in Phase 0.** Attached files live in browser memory via `URL.createObjectURL` for the duration of the session — nothing is parsed, persisted, or actually fed into course generation (there is no real generation yet). Real text extraction and grounding is Phase 1 work, per the PRD's Document Ingestion dependency. Since `OutlineReview`'s sample outline is already a fixed, canned example unrelated to the interview answers, attached files show up as a Source Materials list without changing that canned content.

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

## Roadmap: AI evals (not yet built)

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
