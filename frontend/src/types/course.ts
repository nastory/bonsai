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
    apiKey?: string;
    byomEndpoint?: string;
  };
}
