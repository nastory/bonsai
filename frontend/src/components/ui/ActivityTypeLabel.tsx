import type { ActivityType } from '../../types/course';

const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  reading: 'Reading',
  video: 'Video',
  quiz: 'Quiz',
  essay: 'Essay',
  project: 'Project',
  discussion: 'Discussion',
  assessment: 'Assessment',
  capstone: 'Capstone',
};

/** Identifies an activity's type - used anywhere a module's activities are listed, under the title. */
export function ActivityTypeLabel({ type }: { type: ActivityType }) {
  return <span className="block text-xs font-normal text-bonsai-green">{ACTIVITY_TYPE_LABELS[type]}</span>;
}
