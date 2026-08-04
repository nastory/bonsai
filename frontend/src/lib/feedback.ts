import type { UserSettings } from '../types/course';

type FeedbackKind = 'check' | 'essay' | 'project' | 'discussion';

// Canned copy standing in for real LLM-generated feedback (Phase 1). Bonsai
// never grades — this always reads as a response to think about, not a score.
// Quizzes/assessments don't use this: they get a real per-question
// correctAnswer/explanation from generation instead (see ActivityCard.tsx's
// QuizBlock).
const MESSAGES: Record<FeedbackKind, Record<UserSettings['feedbackTone'], string>> = {
  check: {
    encouraging: "Good instinct. That's exactly the kind of question worth sitting with as you keep going.",
    straightforward: "Worth revisiting once you've seen the next lesson if that wasn't immediately clear.",
  },
  essay: {
    encouraging: "Thanks for writing that out. You're making real connections here. Keep pushing on the parts that felt fuzzy.",
    straightforward: 'Recorded. The parts you hedged on are worth a second pass later.',
  },
  project: {
    encouraging: "Nice work getting hands-on with this. That's where it actually sinks in.",
    straightforward: 'Submission recorded. Compare your result against the module description if anything felt off.',
  },
  discussion: {
    encouraging: "Good thread to pull on. That's exactly the kind of question that deepens understanding.",
    straightforward: 'Reasonable take. Consider the counterexamples before moving on.',
  },
};

export function getFeedbackMessage(tone: UserSettings['feedbackTone'], kind: FeedbackKind): string {
  return MESSAGES[kind][tone];
}
