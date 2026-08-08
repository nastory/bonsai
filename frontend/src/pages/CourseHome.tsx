import { useEffect, useRef, useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { findCurrentActivity, activityPath } from '../lib/courseHelpers';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ProgressBar } from '../components/ui/ProgressBar';
import { InlineMarkdown } from '../components/ui/Markdown';
import { ActivityTypeLabel } from '../components/ui/ActivityTypeLabel';
import { ActivityTypeIcon } from '../components/ui/ActivityTypeIcon';
import { NoticeDialog } from '../components/layout/NoticeDialog';
import { cn } from '../components/ui/cn';

export function CourseHome() {
  const { courseId } = useParams();
  const { getCourse, generateModuleActivities } = useAppData();
  const course = courseId ? getCourse(courseId) : undefined;
  const location = useLocation();
  const navigate = useNavigate();

  const [showNextModuleNotice, setShowNextModuleNotice] = useState(
    Boolean((location.state as { justFinishedModule?: boolean } | null)?.justFinishedModule),
  );

  // Clear the navigation state right away so refreshing (or navigating back
  // to this page later) doesn't re-show the notice.
  useEffect(() => {
    if (location.state) navigate(location.pathname, { replace: true, state: null });
    // Deliberately empty deps: this should run once, on arrival, only.
  }, []);

  const [expandedModules, setExpandedModules] = useState<Set<string>>(() => {
    if (!course) return new Set<string>();
    const current = findCurrentActivity(course);
    return new Set<string>(current ? [current.module.id] : []);
  });

  // A module that's in progress but hasn't had its activities generated yet
  // (e.g. the learner just reached it) needs a one-time trigger. Guarded by
  // this ref so a re-render (or the course refreshing mid-generation)
  // doesn't fire a duplicate request.
  const triggeredModuleIds = useRef<Set<string>>(new Set());
  const [failedModuleId, setFailedModuleId] = useState<string | null>(null);

  useEffect(() => {
    if (!course) return;
    const pendingModule = course.modules.find((m) => m.status === 'in_progress' && m.activities.length === 0);
    if (pendingModule && !triggeredModuleIds.current.has(pendingModule.id)) {
      triggeredModuleIds.current.add(pendingModule.id);
      generateModuleActivities(pendingModule.id).catch(() => setFailedModuleId(pendingModule.id));
    }
  }, [course, generateModuleActivities]);

  const retryGeneration = (moduleId: string) => {
    setFailedModuleId(null);
    generateModuleActivities(moduleId).catch(() => setFailedModuleId(moduleId));
  };

  if (!course) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">
          Course not found.{' '}
          <Link to="/courses" className="font-medium text-bonsai-green">
            Back to My Courses
          </Link>
          .
        </p>
      </div>
    );
  }

  const current = findCurrentActivity(course);

  const toggleModule = (moduleId: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="flex items-center gap-4">
        {course.thumbnailImageUrl ? (
          <img
            src={course.thumbnailImageUrl}
            alt=""
            className="h-16 w-16 shrink-0 rounded-lg object-cover"
          />
        ) : (
          <div className={`h-16 w-16 shrink-0 rounded-lg bg-gradient-to-br ${course.thumbnailUrl}`} />
        )}
        <div>
          <h1 className="text-2xl font-semibold text-bonsai-text">
            <InlineMarkdown>{course.title}</InlineMarkdown>
          </h1>
          <p className="mt-1 text-sm text-bonsai-text-muted">
            <InlineMarkdown>{course.description}</InlineMarkdown>
          </p>
        </div>
      </div>

      <Card className="mt-6">
        <div className="flex items-center gap-3">
          <ProgressBar percent={course.progressPercent} className="flex-1" />
          <span className="text-sm font-medium text-bonsai-text">{course.progressPercent}%</span>
        </div>

        {course.stage === 'completed' ? (
          <div className="mt-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-bonsai-text-muted">Course complete</p>
              <p className="text-sm font-medium text-bonsai-text">Nice work finishing this one.</p>
            </div>
            <Button onClick={() => navigate('/create', { state: { parentCourseId: course.id } })}>
              Keep going
            </Button>
          </div>
        ) : current ? (
          <div className="mt-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-bonsai-text-muted">Currently on</p>
              <p className="text-sm font-medium text-bonsai-text">
                <InlineMarkdown>{current.module.title}</InlineMarkdown> ·{' '}
                <InlineMarkdown>{current.activity.title}</InlineMarkdown>
              </p>
            </div>
            <Link to={activityPath(course.id, current.module.id, current.activity.id)}>
              <Button>Continue</Button>
            </Link>
          </div>
        ) : (
          <p className="mt-4 text-sm text-bonsai-text-muted">No lesson in progress right now.</p>
        )}
      </Card>

      <div className="mt-6 space-y-2">
        {course.modules.map((module) => {
          const hasContent = module.activities.length > 0;
          const isExpanded = expandedModules.has(module.id);

          return (
            <div key={module.id} className="rounded-xl border border-bonsai-border bg-white">
              {hasContent ? (
                <button
                  onClick={() => toggleModule(module.id)}
                  className="flex w-full items-center justify-between px-4 py-3 text-left"
                >
                  <p className="text-sm font-medium text-bonsai-text">
                    <InlineMarkdown>{module.title}</InlineMarkdown>
                  </p>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
                  )}
                </button>
              ) : (
                <div className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p
                      className={cn(
                        'text-sm font-medium',
                        module.status === 'locked' ? 'text-bonsai-text-muted' : 'text-bonsai-text',
                      )}
                    >
                      <InlineMarkdown>{module.title}</InlineMarkdown>
                    </p>
                    <p className="mt-0.5 text-xs text-bonsai-text-muted">
                      {module.status === 'locked'
                        ? 'Not generated yet. Unlocks when you reach it.'
                        : failedModuleId === module.id
                          ? 'Generation failed.'
                          : 'Generating...'}
                    </p>
                  </div>
                  {failedModuleId === module.id && (
                    <button
                      onClick={() => retryGeneration(module.id)}
                      className="text-xs font-medium text-bonsai-green hover:underline"
                    >
                      Retry
                    </button>
                  )}
                </div>
              )}

              {hasContent && isExpanded && (
                <ul className="space-y-1 border-t border-bonsai-border px-4 py-3">
                  {module.activities.map((activity) => (
                    <li key={activity.id}>
                      <Link
                        to={activityPath(course.id, module.id, activity.id)}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-bonsai-text hover:bg-bonsai-cream"
                      >
                        <ActivityTypeIcon type={activity.type} completed={activity.status === 'completed'} />
                        <span className="flex-1">
                          <InlineMarkdown>{activity.title}</InlineMarkdown>
                          <ActivityTypeLabel type={activity.type} />
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {showNextModuleNotice && (
        <NoticeDialog
          title="Nice work!"
          message="Alright, I'll start generating your next module."
          onClose={() => setShowNextModuleNotice(false)}
        />
      )}
    </div>
  );
}
