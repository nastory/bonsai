export type ActivityType =
  | 'reading'
  | 'video'
  | 'quiz'
  | 'essay'
  | 'project'
  | 'discussion'
  | 'assessment';

export type ActivityStatus = 'locked' | 'available' | 'completed';

export type ModuleStatus = 'locked' | 'in_progress' | 'completed';

export interface Citation {
  label: string;
  url: string;
}

export interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  status: ActivityStatus;
  estimatedMinutes?: number;
  /** Reading/video body text, may include inline citation markers like [1]. */
  body?: string;
  citations?: Citation[];
  /** Quiz-specific fields. */
  question?: string;
  options?: string[];
  /** Essay/project/discussion seed prompt. */
  prompt?: string;
  /** True when this activity is a capstone/practicum-style project. */
  isCapstone?: boolean;
  /** Optional short comprehension check embedded at the end of a reading, rendered distinctly from the main content. */
  checkPrompt?: string;
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
  progressPercent: number;
  stage: CourseStage;
  modules: Module[];
  /** Present only for courses created from uploaded documents rather than a typed topic. */
  sourceMaterials?: SourceMaterial[];
}

/** The result of starting or answering into the course-creation interview. */
export interface InterviewStep {
  courseId: string;
  done: boolean;
  question: string | null;
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
   * PRD's model-roles requirement. Not used by anything yet (retrieval and
   * semantic search aren't built), but settable in advance.
   */
  embeddingModel?: string;
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
}
