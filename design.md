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
