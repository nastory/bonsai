import { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ArrowLeft, List, Paperclip } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { activityPath } from '../lib/courseHelpers';
import { ActivityCard } from '../components/lesson/ActivityCard';
import { TableOfContents } from '../components/lesson/TableOfContents';
import { ModuleCompletionModal } from '../components/lesson/ModuleCompletionModal';
import { SourceMaterialsPanel } from '../components/lesson/SourceMaterialsPanel';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export function Lesson() {
  const { courseId, moduleId, activityId } = useParams();
  const { getCourse, completeActivity } = useAppData();
  const navigate = useNavigate();
  const [tocOpen, setTocOpen] = useState(false);
  const [sourceMaterialsOpen, setSourceMaterialsOpen] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);

  const course = courseId ? getCourse(courseId) : undefined;
  const module = course?.modules.find((m) => m.id === moduleId);
  const activityIndex = module?.activities.findIndex((a) => a.id === activityId) ?? -1;
  const activity = activityIndex >= 0 ? module?.activities[activityIndex] : undefined;

  if (!course || !module || !activity) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">
          This content hasn't been generated yet.{' '}
          <Link to="/courses" className="font-medium text-bonsai-green">
            Back to My Courses
          </Link>
          .
        </p>
      </div>
    );
  }

  const isLastInModule = activityIndex === module.activities.length - 1;
  const nextActivity = !isLastInModule ? module.activities[activityIndex + 1] : undefined;
  const prevActivity = activityIndex > 0 ? module.activities[activityIndex - 1] : undefined;

  const goToNextModuleOrHome = () => {
    const moduleIndex = course.modules.findIndex((m) => m.id === module.id);
    const nextModule = course.modules[moduleIndex + 1];
    if (nextModule && nextModule.activities.length > 0) {
      navigate(activityPath(course.id, nextModule.id, nextModule.activities[0].id));
    } else {
      navigate('/courses');
    }
  };

  const handleContinue = () => {
    completeActivity(activity.id);
    if (nextActivity) {
      navigate(activityPath(course.id, module.id, nextActivity.id));
    } else {
      setShowCompletionModal(true);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate(`/courses/${course.id}`)}
          className="flex items-center gap-2 text-sm font-medium text-bonsai-text hover:text-bonsai-green"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm text-bonsai-text-muted">
            Lesson {activityIndex + 1} of {module.activities.length}
          </span>
          {course.sourceMaterials && course.sourceMaterials.length > 0 && (
            <button
              onClick={() => setSourceMaterialsOpen(true)}
              aria-label="Source materials"
              className="flex items-center gap-1 text-sm text-bonsai-text-muted hover:text-bonsai-text"
            >
              <Paperclip className="h-4 w-4" />
              Source Materials
            </button>
          )}
          <button
            onClick={() => setTocOpen(true)}
            aria-label="Course contents"
            className="flex items-center gap-1.5 rounded-lg border border-bonsai-border px-2.5 py-1.5 text-sm text-bonsai-text-muted hover:bg-bonsai-cream hover:text-bonsai-text"
          >
            <List className="h-4 w-4" />
            Contents
          </button>
        </div>
      </div>

      <Badge>{module.title}</Badge>
      <h1 className="mt-1 text-2xl font-semibold text-bonsai-text">{activity.title}</h1>

      <div className="mt-5">
        <ActivityCard activity={activity} />
      </div>

      <div className="mt-6 flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={() => (prevActivity ? navigate(activityPath(course.id, module.id, prevActivity.id)) : navigate('/courses'))}
        >
          Back
        </Button>
        <Button onClick={handleContinue}>{isLastInModule ? 'Finish module' : 'Continue'}</Button>
      </div>

      {tocOpen && (
        <TableOfContents course={course} currentActivityId={activity.id} onClose={() => setTocOpen(false)} />
      )}

      {sourceMaterialsOpen && course.sourceMaterials && (
        <SourceMaterialsPanel materials={course.sourceMaterials} onClose={() => setSourceMaterialsOpen(false)} />
      )}

      {showCompletionModal && (
        <ModuleCompletionModal
          moduleTitle={module.title}
          onKeepGoing={() => {
            setShowCompletionModal(false);
            goToNextModuleOrHome();
          }}
          onBranchOff={() => {
            setShowCompletionModal(false);
            navigate('/create', { state: { parentCourseId: course.id } });
          }}
          onChangeThisCourse={() => {
            setShowCompletionModal(false);
            navigate(`/courses/${course.id}/modules/${module.id}/change-direction`);
          }}
        />
      )}
    </div>
  );
}
