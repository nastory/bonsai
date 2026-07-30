import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { Course } from '../../types/course';
import { ProgressBar } from '../ui/ProgressBar';

export function CourseCard({ course }: { course: Course }) {
  const lessonCount = course.modules.reduce((sum, m) => sum + m.activities.length, 0);

  return (
    <Link
      to={`/courses/${course.id}`}
      className="flex items-center gap-4 rounded-xl border border-bonsai-border bg-white p-4 hover:bg-bonsai-cream"
    >
      <div className={`h-14 w-14 shrink-0 rounded-lg bg-gradient-to-br ${course.thumbnailUrl}`} />
      <div className="flex-1">
        <p className="font-semibold text-bonsai-text">{course.title}</p>
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
  );
}
