import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { InlineMarkdown } from '../components/ui/Markdown';

/**
 * Shared course -> module picker for Flash Cards and Quiz Me, whose landing
 * pages are otherwise identical: pick a course, then a generated module,
 * then navigate to that feature's session page.
 */
export function ResourcePicker({ title, description, basePath }: { title: string; description: string; basePath: string }) {
  const { courses } = useAppData();
  const navigate = useNavigate();
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);

  const visibleCourses = courses.filter((c) => c.stage === 'active' || c.stage === 'completed');
  const selectedCourse = visibleCourses.find((c) => c.id === selectedCourseId);
  // Same "hasContent" gate CourseHome uses: a learner can't target a
  // locked, never-generated module through this feature - that generation
  // trigger stays exclusively CourseHome's job.
  const availableModules = selectedCourse?.modules.filter((m) => m.activities.length > 0) ?? [];

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">{title}</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">{description}</p>

      {!selectedCourse ? (
        <div className="mt-6 space-y-2">
          {visibleCourses.length === 0 && (
            <p className="text-sm text-bonsai-text-muted">Create a course first to use this here.</p>
          )}
          {visibleCourses.map((course) => (
            <button
              key={course.id}
              onClick={() => setSelectedCourseId(course.id)}
              className="flex w-full items-center justify-between rounded-lg border border-bonsai-border bg-white px-4 py-3 text-left hover:bg-bonsai-cream"
            >
              <span className="text-sm font-medium text-bonsai-text">
                <InlineMarkdown>{course.title}</InlineMarkdown>
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
            </button>
          ))}
        </div>
      ) : (
        <div className="mt-6">
          <button
            onClick={() => setSelectedCourseId(null)}
            className="text-sm font-medium text-bonsai-green hover:underline"
          >
            &larr; Choose a different course
          </button>
          <div className="mt-4 space-y-2">
            {availableModules.length === 0 && (
              <p className="text-sm text-bonsai-text-muted">
                No modules with generated content yet in this course.
              </p>
            )}
            {availableModules.map((module) => (
              <button
                key={module.id}
                onClick={() => navigate(`${basePath}/${selectedCourse.id}/${module.id}`)}
                className="flex w-full items-center justify-between rounded-lg border border-bonsai-border bg-white px-4 py-3 text-left hover:bg-bonsai-cream"
              >
                <span className="text-sm font-medium text-bonsai-text">
                  <InlineMarkdown>{module.title}</InlineMarkdown>
                </span>
                <ChevronRight className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
