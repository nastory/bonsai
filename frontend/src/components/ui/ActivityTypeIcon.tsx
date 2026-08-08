import { Award, BookOpen, ClipboardCheck, HelpCircle, MessageCircle, PenLine, Play, Wrench } from 'lucide-react';
import type { ActivityType } from '../../types/course';
import { cn } from './cn';

const ACTIVITY_TYPE_ICONS: Record<ActivityType, typeof BookOpen> = {
  reading: BookOpen,
  video: Play,
  quiz: HelpCircle,
  essay: PenLine,
  project: Wrench,
  discussion: MessageCircle,
  assessment: ClipboardCheck,
  capstone: Award,
};

/**
 * A small round icon identifying an activity's type, filled in dark green
 * once completed (not-completed stays an outline) - used anywhere a
 * module's activities are listed, replacing a plain completion
 * checkmark/circle so the same glance also shows what kind of activity it is.
 */
export function ActivityTypeIcon({ type, completed }: { type: ActivityType; completed: boolean }) {
  const Icon = ACTIVITY_TYPE_ICONS[type];
  return (
    <span
      className={cn(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
        completed ? 'bg-bonsai-green text-white' : 'border border-bonsai-border text-bonsai-text-muted',
      )}
    >
      <Icon className="h-3 w-3" />
    </span>
  );
}
