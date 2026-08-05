import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FileText, Loader2 } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { InlineMarkdown } from '../components/ui/Markdown';
import { useAppData } from '../context/AppDataContext';
import { fetchCourse, submitOutlineFeedback, approveOutline } from '../lib/api';
import type { Course } from '../types/course';

export function OutlineReview() {
  const navigate = useNavigate();
  const { courseId } = useParams();
  const { refreshCourses } = useAppData();

  const [course, setCourse] = useState<Course | null>(null);
  const [feedback, setFeedback] = useState('');
  const [requested, setRequested] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [revising, setRevising] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    fetchCourse(courseId)
      .then(setCourse)
      .catch((err) => console.error('Failed to load the generated outline:', err));
  }, [courseId]);

  const handleRequestChanges = async (e: FormEvent) => {
    e.preventDefault();
    if (!feedback.trim() || !courseId) return;
    setSubmitting(true);
    setRevising(true);
    try {
      const updated = await submitOutlineFeedback(courseId, feedback);
      setCourse(updated);
      setRequested(true);
      setFeedback('');
    } catch (err) {
      console.error('Failed to revise the outline:', err);
    } finally {
      setSubmitting(false);
      setRevising(false);
    }
  };

  const handleStartLearning = async () => {
    if (!courseId) return;
    setSubmitting(true);
    try {
      await approveOutline(courseId);
      await refreshCourses();
      navigate('/courses');
    } catch (err) {
      console.error('Failed to start the course:', err);
      setSubmitting(false);
    }
  };

  if (!course) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">Drafting your course outline...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Here's your course outline</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">Review it, ask for changes, or start learning.</p>

      <Card className="mt-6">
        <p className="text-lg font-semibold text-bonsai-text">
          <InlineMarkdown>{course.title}</InlineMarkdown>
        </p>
        <p className="mt-2 text-sm text-bonsai-text-muted">
          <InlineMarkdown>{course.description}</InlineMarkdown>
        </p>

        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-bonsai-text-muted">Estimated timeline</dt>
            <dd className="font-medium text-bonsai-text">
              <InlineMarkdown>{course.estimatedTimeline}</InlineMarkdown>
            </dd>
          </div>
          <div>
            <dt className="text-bonsai-text-muted">Prerequisites</dt>
            <dd className="font-medium text-bonsai-text">
              {course.prerequisites.length > 0 ? (
                <InlineMarkdown>{course.prerequisites.join(', ')}</InlineMarkdown>
              ) : (
                'None'
              )}
            </dd>
          </div>
        </dl>

        <div className="mt-6 space-y-3">
          {course.modules.map((module, i) => (
            <div key={module.id} className="rounded-lg border border-bonsai-border p-3">
              <Badge>Module {i + 1}</Badge>
              <p className="mt-1 font-medium text-bonsai-text">
                <InlineMarkdown>{module.title}</InlineMarkdown>
              </p>
              <p className="mt-0.5 text-sm text-bonsai-text-muted">
                <InlineMarkdown>{module.description}</InlineMarkdown>
              </p>
            </div>
          ))}
        </div>

        {course.sourceMaterials && course.sourceMaterials.length > 0 && (
          <div className="mt-6 border-t border-bonsai-border pt-4">
            <p className="text-sm font-medium text-bonsai-text">Source Materials</p>
            <ul className="mt-2 space-y-2">
              {course.sourceMaterials.map((material) => (
                <li
                  key={material.id}
                  className="flex items-center gap-2 rounded-lg border border-bonsai-border px-3 py-2 text-sm text-bonsai-text"
                >
                  <FileText className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
                  {material.fileName}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <form onSubmit={handleRequestChanges} className="mt-6 flex items-center gap-2">
        <Input
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Ask for changes, e.g. “add more on troubleshooting”"
          disabled={submitting}
        />
        <Button type="submit" variant="secondary" disabled={submitting || !feedback.trim()}>
          Request
        </Button>
      </form>
      {requested && <p className="mt-2 text-sm text-bonsai-green">Outline updated with your feedback.</p>}

      <Button className="mt-6 w-full" onClick={handleStartLearning} disabled={submitting}>
        Start Learning
      </Button>

      {revising && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <Card className="flex w-full max-w-sm flex-col items-center gap-3 py-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-bonsai-green" />
            <p className="font-semibold text-bonsai-text">Updating your course outline...</p>
            <p className="text-sm text-bonsai-text-muted">
              This can take a little while, especially with a local model.
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
