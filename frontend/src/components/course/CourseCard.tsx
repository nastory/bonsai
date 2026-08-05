import { Link } from 'react-router-dom';
import { Check, ChevronRight } from 'lucide-react';
import type { Course } from '../../types/course';
import { ProgressBar } from '../ui/ProgressBar';
import { Badge } from '../ui/Badge';
import { InlineMarkdown } from '../ui/Markdown';
import { cn } from '../ui/cn';

interface CourseCardProps {
  course: Course;
  /** Shows a select circle and disables navigation-on-click when true. */
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: () => void;
}

export function CourseCard({ course, selectable, selected, onToggleSelect }: CourseCardProps) {
  const lessonCount = course.modules.reduce((sum, m) => sum + m.activities.length, 0);

  return (
    <div className="flex items-center gap-3">
      {selectable && (
        <button
          type="button"
          onClick={onToggleSelect}
          aria-label={selected ? `Deselect ${course.title}` : `Select ${course.title}`}
          aria-pressed={selected}
          className={cn(
            'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
            selected ? 'border-bonsai-green bg-bonsai-green' : 'border-bonsai-border bg-white',
          )}
        >
          {selected && <Check className="h-3 w-3 text-white" />}
        </button>
      )}
      <Link
        to={`/courses/${course.id}`}
        className="flex flex-1 items-center gap-4 rounded-xl border border-bonsai-border bg-white p-4 hover:bg-bonsai-cream"
      >
        {course.thumbnailImageUrl ? (
          <img
            src={course.thumbnailImageUrl}
            alt=""
            className="h-14 w-14 shrink-0 rounded-lg object-cover"
          />
        ) : (
          <div className={`h-14 w-14 shrink-0 rounded-lg bg-gradient-to-br ${course.thumbnailUrl}`} />
        )}
        <div className="flex-1">
          <p className="flex items-center gap-2 font-semibold text-bonsai-text">
            <InlineMarkdown>{course.title}</InlineMarkdown>
            {course.stage === 'completed' && <Badge>Completed</Badge>}
          </p>
          <p className="text-sm text-bonsai-text-muted">
            {course.modules.length} modules
            {lessonCount > 0 ? ` • ${lessonCount} lessons` : ''}
          </p>
        </div>
        <div className="w-32 shrink-0">
          <ProgressBar percent={course.progressPercent} />
          <p className="mt-1 text-right text-xs text-bonsai-text-muted">{course.progressPercent}%</p>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
      </Link>
    </div>
  );
}
