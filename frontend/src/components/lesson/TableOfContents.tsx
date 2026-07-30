import { X, Check, Lock, Circle } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Course } from '../../types/course';
import { cn } from '../ui/cn';
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
          <p className="font-semibold text-bonsai-text">{course.title}</p>
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
                {module.title}
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
                    const isLocked = activity.status === 'locked';

                    const row = (
                      <div
                        className={cn(
                          'flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm',
                          isCurrent && 'bg-bonsai-cream font-medium text-bonsai-green',
                          !isCurrent && !isLocked && 'text-bonsai-text hover:bg-bonsai-cream',
                          isLocked && 'text-bonsai-text-muted',
                        )}
                      >
                        {activity.status === 'completed' && <Check className="h-3.5 w-3.5 shrink-0 text-bonsai-green" />}
                        {activity.status === 'available' && <Circle className="h-3.5 w-3.5 shrink-0" />}
                        {activity.status === 'locked' && <Lock className="h-3.5 w-3.5 shrink-0" />}
                        <span>{activity.title}</span>
                      </div>
                    );

                    return (
                      <li key={activity.id}>
                        {isLocked ? (
                          row
                        ) : (
                          <Link to={activityPath(course.id, module.id, activity.id)} onClick={onClose}>
                            {row}
                          </Link>
                        )}
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
