# Bonsai — Mockup Feedback (`bonsai_mockup.png`)

Feedback on the 5-screen UI mockup (Home/Today, Lesson View, In-Lesson Content, Course Creation, My Courses), with decisions.

- **Course creation flow is too rigid** — mockup shows fixed multiple-choice pills (Beginner/Some experience/Intermediate/Advanced), but per the original idea doc this should stay open-ended: dynamically generated questions with free-text answers, not preset options. **Decision: keep it open-ended, mockup was a shortcut.**
- **Course thumbnail images are AI-generated** — confirmed. **Decision: add a user setting to disable thumbnail generation, to save tokens.**
- **Screen 3 (In-Lesson Content) needs clearer visual separation** between the reference table (memory hierarchy) and the "Check your understanding" quiz card — both use similar light-gray card styling and compete for attention. Recommend distinct treatment (border/icon/color) for graded vs. reference content.
- **Lesson navigation is unclear** — no visible way to jump back to a previous module/lesson from the lesson view; "Back" reads as prev-step-within-lesson only. Needs a nav decision before build (could just be trimmed from mockup).
- **Brand touch worth keeping**: the sprout icon as the AI's avatar in chat bubbles ties the Bonsai theme into the interaction itself, not just the logo.

## Next Steps
- Revise course-creation screen to reflect open-ended Q&A flow.
- Add thumbnail-generation toggle to settings scope.
- Otherwise mockup is close to build-ready — candidate for turning into HTML/React once these are addressed.
