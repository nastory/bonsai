import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { InlineMarkdown } from '../components/ui/Markdown';
import { useAppData } from '../context/AppDataContext';
import { submitDirectionChangeFeedback, approveDirectionChange } from '../lib/api';
import type { DirectionChangeProposal } from '../types/course';

interface ChangeDirectionReviewLocationState {
  proposal?: DirectionChangeProposal;
}

export function ChangeDirectionReview() {
  const navigate = useNavigate();
  const location = useLocation();
  const { courseId, moduleId } = useParams();
  const { refreshCourses } = useAppData();

  const [proposal, setProposal] = useState<DirectionChangeProposal | null>(
    (location.state as ChangeDirectionReviewLocationState | null)?.proposal ?? null,
  );
  const [feedback, setFeedback] = useState('');
  const [requested, setRequested] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleRequestChanges = async (e: FormEvent) => {
    e.preventDefault();
    if (!feedback.trim() || !moduleId) return;
    setSubmitting(true);
    try {
      const updated = await submitDirectionChangeFeedback(moduleId, feedback);
      setProposal(updated);
      setRequested(true);
      setFeedback('');
    } catch (err) {
      console.error('Failed to revise the proposal:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!moduleId) return;
    setSubmitting(true);
    try {
      await approveDirectionChange(moduleId);
      await refreshCourses();
      navigate(`/courses/${courseId}`);
    } catch (err) {
      console.error('Failed to apply the new direction:', err);
      setSubmitting(false);
    }
  };

  if (!proposal) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">
          Nothing to review here.{' '}
          <Link to={`/courses/${courseId}`} className="font-medium text-bonsai-green">
            Back to course
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Here's the rest of your course, updated</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">
        Review it, ask for changes, or continue with it. Everything you've already finished stays exactly as it is.
      </p>

      <Card className="mt-6">
        <div className="space-y-3">
          {proposal.modules.map((module, i) => (
            <div key={i} className="rounded-lg border border-bonsai-border p-3">
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
      {requested && <p className="mt-2 text-sm text-bonsai-green">Updated with your feedback.</p>}

      <Button className="mt-6 w-full" onClick={handleApprove} disabled={submitting}>
        Continue With This
      </Button>
    </div>
  );
}
