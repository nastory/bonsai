import { Link } from 'react-router-dom';
import { FileText, PlayCircle } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { findCurrentActivity, activityPath } from '../lib/courseHelpers';
import { startOfWeek, countActivitiesCompletedSince } from '../lib/weekHelpers';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ProgressBar } from '../components/ui/ProgressBar';
import { InlineMarkdown } from '../components/ui/Markdown';

function timeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function Today() {
  const { user, courses } = useAppData();

  const inProgressCourse = courses.find((c) => findCurrentActivity(c));
  const current = inProgressCourse && findCurrentActivity(inProgressCourse);

  const weeklyGoal = user.weeklyGoalActivities;
  const completedThisWeek = weeklyGoal != null ? countActivitiesCompletedSince(courses, startOfWeek(new Date())) : 0;

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">
        {timeOfDayGreeting()}, {user.name.split(' ')[0]}.
      </h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">Ready to grow your knowledge?</p>

      {weeklyGoal != null && (
        <Card className="mt-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-bonsai-text-muted">This week's goal</p>
            <span className="text-sm font-medium text-bonsai-text">
              {completedThisWeek} of {weeklyGoal} activities
            </span>
          </div>
          <ProgressBar percent={Math.min(100, Math.round((completedThisWeek / weeklyGoal) * 100))} className="mt-2" />
        </Card>
      )}

      {current && inProgressCourse ? (
        <Card className="mt-6">
          <p className="mb-3 text-sm font-medium text-bonsai-text-muted">Continue learning</p>
          <div className="flex gap-4">
            {inProgressCourse.thumbnailImageUrl ? (
              <img
                src={inProgressCourse.thumbnailImageUrl}
                alt=""
                className="h-20 w-20 shrink-0 rounded-lg object-cover"
              />
            ) : (
              <div
                className={`h-20 w-20 shrink-0 rounded-lg bg-gradient-to-br ${inProgressCourse.thumbnailUrl}`}
              />
            )}
            <div className="flex-1">
              <p className="font-semibold text-bonsai-text">
                <InlineMarkdown>{inProgressCourse.title}</InlineMarkdown>
              </p>
              <p className="mt-0.5 text-sm text-bonsai-text-muted">
                <InlineMarkdown>{current.module.title}</InlineMarkdown> •{' '}
                <InlineMarkdown>{current.activity.title}</InlineMarkdown>
              </p>
              <div className="mt-3 flex items-center gap-3">
                <ProgressBar percent={inProgressCourse.progressPercent} className="flex-1" />
                <span className="text-xs text-bonsai-text-muted">{inProgressCourse.progressPercent}%</span>
              </div>
            </div>
          </div>
          <Link
            to={activityPath(inProgressCourse.id, current.module.id, current.activity.id)}
            className="mt-4 block"
          >
            <Button className="w-full">Continue lesson</Button>
          </Link>
        </Card>
      ) : (
        <Card className="mt-6">
          <p className="text-sm text-bonsai-text-muted">
            No course in progress yet.{' '}
            <Link to="/create" className="font-medium text-bonsai-green">
              Start one
            </Link>
            .
          </p>
        </Card>
      )}

      {current && inProgressCourse && (
        <div className="mt-6">
          <p className="mb-2 text-sm font-medium text-bonsai-text-muted">Up next</p>
          <Link
            to={activityPath(inProgressCourse.id, current.module.id, current.activity.id)}
            className="flex items-center gap-3 rounded-lg border border-bonsai-border bg-white px-4 py-3 hover:bg-bonsai-cream"
          >
            {current.activity.type === 'video' ? (
              <PlayCircle className="h-5 w-5 text-bonsai-text-muted" />
            ) : (
              <FileText className="h-5 w-5 text-bonsai-text-muted" />
            )}
            <div>
              <p className="text-sm font-medium text-bonsai-text">
                <InlineMarkdown>{current.activity.title}</InlineMarkdown>
              </p>
              {current.activity.estimatedMinutes && (
                <p className="text-xs text-bonsai-text-muted">
                  Lesson {current.indexInModule + 1} • {current.activity.estimatedMinutes} min
                </p>
              )}
            </div>
          </Link>
        </div>
      )}
    </div>
  );
}
