import { X } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Course } from '../../types/course';
import { cn } from '../ui/cn';
import { InlineMarkdown } from '../ui/Markdown';
import { ActivityTypeLabel } from '../ui/ActivityTypeLabel';
import { ActivityTypeIcon } from '../ui/ActivityTypeIcon';
import { activityPath } from '../../lib/courseHelpers';

interface TableOfContentsProps {
  course: Course;
  currentActivityId: string;
  onClose: () => void;
}

export function TableOfContents({ course, currentActivityId, onClose }: TableOfContentsProps) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="flex h-full w-96 flex-col overflow-y-auto bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <p className="font-semibold text-bonsai-text">
            <InlineMarkdown>{course.title}</InlineMarkdown>
          </p>
          <button onClick={onClose} aria-label="Close">
            <X className="h-4 w-4 text-bonsai-text-muted" />
          </button>
        </div>

        <div className="space-y-6">
          {course.modules.map((module) => (
            <div key={module.id}>
              <p
                className={cn(
                  'text-sm font-semibold',
                  module.status === 'locked' ? 'text-bonsai-text-muted' : 'text-bonsai-text',
                )}
              >
                <InlineMarkdown>{module.title}</InlineMarkdown>
              </p>

              {module.activities.length === 0 ? (
                <p className="mt-1 text-xs text-bonsai-text-muted">
                  {module.status === 'locked'
                    ? 'Not generated yet. Unlocks when you reach it.'
                    : 'Generating...'}
                </p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {module.activities.map((activity) => {
                    const isCurrent = activity.id === currentActivityId;

                    return (
                      <li key={activity.id}>
                        <Link
                          to={activityPath(course.id, module.id, activity.id)}
                          onClick={onClose}
                          className={cn(
                            'flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm',
                            isCurrent ? 'bg-bonsai-cream font-medium text-bonsai-green' : 'text-bonsai-text hover:bg-bonsai-cream',
                          )}
                        >
                          <ActivityTypeIcon type={activity.type} completed={activity.status === 'completed'} />
                          <span className="flex-1">
                            <InlineMarkdown>{activity.title}</InlineMarkdown>
                            <ActivityTypeLabel type={activity.type} />
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
