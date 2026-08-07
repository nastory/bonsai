export type ActivityType =
  | 'reading'
  | 'video'
  | 'quiz'
  | 'essay'
  | 'project'
  | 'discussion'
  | 'assessment'
  | 'capstone';

// No 'locked': a module's activities are always generated together (see
// module_generation.py), so an activity either doesn't exist yet (the
// module itself is locked/ungenerated) or is fully reachable. Only
// ModuleStatus needs a 'locked' state.
export type ActivityStatus = 'available' | 'completed';

export type ModuleStatus = 'locked' | 'in_progress' | 'completed';

export interface Citation {
  label: string;
  /** Absent for a document source-material citation (e.g. "paper.pdf, p. 4") - only a web citation has a real URL. */
  url?: string;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  /** Which of "options" is correct (by index), and why. */
  correctAnswerIndex: number;
  explanation: string;
}

export interface DiscussionMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  status: ActivityStatus;
  estimatedMinutes?: number;
  /** ISO timestamp of when this activity was marked completed; null until then. */
  completedAt?: string | null;
  /** Reading body text, may include inline citation markers like [1]. */
  body?: string;
  citations?: Citation[];
  /** Video-specific fields — a real YouTube embed, not AI-generated video. */
  videoUrl?: string;
  videoId?: string;
  caption?: string;
  /** Quiz/assessment-only: 1-3 questions for a quiz, 10-15 for the course's closing assessment. */
  questions?: QuizQuestion[];
  /** Essay/project/discussion/capstone seed prompt — for discussion, this is the opening line, not persisted as a message itself. */
  prompt?: string;
  /** Discussion-only: the real back-and-forth so far (the opening "prompt" line isn't included here). */
  messages?: DiscussionMessage[];
  /** Discussion-only: true once the conversation has reached its closing turn. */
  discussionDone?: boolean;
  /** Optional short comprehension check embedded at the end of a reading, rendered distinctly from the main content. */
  checkPrompt?: string;
}

export interface FlashCard {
  question: string;
  answer: string;
}

export interface FlashCardSet {
  id: string;
  moduleId: string;
  cards: FlashCard[];
}

export interface QuizSet {
  id: string;
  moduleId: string;
  questions: QuizQuestion[];
}

export interface AMAMessage {
  role: 'user' | 'assistant';
  content: string;
  /** Assistant-only: sources drawn from course material, when the reply used any. */
  citations?: Citation[];
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

export type CourseStage = 'interview' | 'outline_review' | 'active' | 'completed';

export interface Course {
  id: string;
  title: string;
  description: string;
  prerequisites: string[];
  estimatedTimeline: string;
  thumbnailUrl: string;
  /** URL to a real generated thumbnail image, when one exists. Falls back to the thumbnailUrl gradient otherwise. */
  thumbnailImageUrl?: string | null;
  progressPercent: number;
  stage: CourseStage;
  /** Set when this course was created via "Branch Off" from another course. */
  parentCourseId?: string | null;
  modules: Module[];
  /** Present only for courses created from uploaded documents rather than a typed topic. */
  sourceMaterials?: SourceMaterial[];
}

/** The result of starting or answering into the course-creation interview. */
export interface InterviewStep {
  courseId: string;
  done: boolean;
  question: string | null;
  /** The course's full accumulated source materials, not just any attached this turn. */
  sourceMaterials: SourceMaterial[];
  /** Out of 5 fixed interview topics - real progress through the checklist, not just turns taken. */
  topicsCoveredCount: number;
}

/** The result of starting or answering into a mid-course "Change This Course" check-in interview. */
export interface DirectionChangeInterviewStep {
  done: boolean;
  question: string | null;
}

/** One activity within a DirectionChangeProposal module — planned only, no content yet. */
export interface PlannedActivity {
  type: ActivityType;
  title: string;
  plan: string;
}

/** One proposed module within a DirectionChangeProposal — not yet real, no id/status until approved. */
export interface PlannedModule {
  title: string;
  description: string;
  estimatedTimeline: string;
  learningOutcomes: string[];
  plannedActivities: PlannedActivity[];
}

/** A proposed replacement for everything ahead of a module, pending review/approval. */
export interface DirectionChangeProposal {
  modules: PlannedModule[];
}

export interface ModelProviderSettings {
  tier: 'hosted' | 'byom';
  hostedProvider?: 'anthropic' | 'openai';
  /** Which model to use at the hosted provider (e.g. "claude-3-5-sonnet-20241022"). Blank uses a sensible default. */
  hostedModel?: string;
  /** Whether a key is stored on the backend. The raw key is never sent back on read. */
  hasApiKey: boolean;
  byomEndpoint?: string;
  /** Which model to ask for at the BYOM endpoint (e.g. "llama3"). */
  byomModel?: string;
}

export interface UserSettings {
  name: string;
  feedbackTone: 'encouraging' | 'straightforward';
  thumbnailGenerationEnabled: boolean;
  modelProvider: ModelProviderSettings;
  /**
   * Independently configurable from the completion model above, per the
   * PRD's model-roles requirement. Powers document-grounded course
   * generation (chunking and retrieval over uploaded source materials).
   */
  embeddingModel?: string;
  /** Hosted tier only: whether the embedding model reuses modelProvider's API key. */
  embeddingUseCompletionCredentials: boolean;
  /** Whether a dedicated embedding API key is stored on the backend. The raw key is never sent back on read. */
  hasEmbeddingApiKey: boolean;
  /** Independently configurable from the completion model, powers course thumbnail generation. */
  imageGenerationModel?: string;
  /** Hosted tier only: whether the image generation model reuses modelProvider's API key. */
  imageGenerationUseCompletionCredentials: boolean;
  /** Whether a dedicated image generation API key is stored on the backend. The raw key is never sent back on read. */
  hasImageGenerationApiKey: boolean;
  /** Whether a Tavily key is stored on the backend. The raw key is never sent back on read. */
  hasTavilyApiKey: boolean;
  /** Uses Tavily's slower, more thorough "advanced" search mode for module-generation searches. */
  deepSearchEnabled: boolean;
  /** Illustrates reading activities with a retrieved image, when one is available. Needs a Tavily key. */
  visualAidsEnabled: boolean;
  /** Tries to add one relevant YouTube video activity per module, when a good match is found. Needs a Tavily key. */
  videoEmbeddingEnabled: boolean;
  /** Optional personal goal: activities to complete each calendar week. Null means no goal is set. */
  weeklyGoalActivities: number | null;
  /** False only for a brand-new install - gates the first-time OnboardingModal. */
  onboardingCompleted: boolean;
}

/**
 * A partial update sent to PUT /api/settings. Omitted fields (including
 * nested modelProvider fields) are left untouched by the backend.
 * `apiKey` is write-only here: it exists to set a new key, never to read one.
 */
export interface UserSettingsPatch {
  name?: string;
  feedbackTone?: 'encouraging' | 'straightforward';
  thumbnailGenerationEnabled?: boolean;
  modelProvider?: {
    tier?: 'hosted' | 'byom';
    hostedProvider?: 'anthropic' | 'openai';
    hostedModel?: string;
    apiKey?: string;
    byomEndpoint?: string;
    byomModel?: string;
  };
  embeddingModel?: string;
  embeddingUseCompletionCredentials?: boolean;
  /** Write-only, like apiKey: sets a new embedding API key, never reads one back. */
  embeddingApiKey?: string;
  imageGenerationModel?: string;
  imageGenerationUseCompletionCredentials?: boolean;
  /** Write-only, like apiKey: sets a new image generation API key, never reads one back. */
  imageGenerationApiKey?: string;
  /** Write-only, like apiKey: sets a new Tavily key, never reads one back. */
  tavilyApiKey?: string;
  deepSearchEnabled?: boolean;
  visualAidsEnabled?: boolean;
  videoEmbeddingEnabled?: boolean;
  weeklyGoalActivities?: number | null;
  onboardingCompleted?: boolean;
}
