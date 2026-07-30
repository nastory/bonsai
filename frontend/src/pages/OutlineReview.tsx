import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';

// Phase 0 shows a fixed sample outline rather than one generated from the
// interview answers — real generation is Phase 1. "Start Learning" returns to
// My Courses rather than inserting this into the fixture data, since proving
// the review/approve interaction is the point here, not full course creation.
const SAMPLE_OUTLINE = {
  title: 'Sourdough Bread Baking',
  description:
    'A hands-on path from your first starter to consistently good loaves, covering the fermentation science along the way.',
  prerequisites: ['None, just an oven and some patience'],
  estimatedTimeline: '3 weeks',
  modules: [
    {
      title: 'Building & Maintaining a Starter',
      description: 'What a starter actually is, and how to keep one alive.',
    },
    {
      title: 'Dough Fundamentals',
      description: 'Hydration, gluten development, and reading your dough.',
    },
    {
      title: 'Fermentation & Timing',
      description: 'Bulk fermentation, proofing, and adjusting for your kitchen.',
    },
    {
      title: 'Shaping, Scoring & Baking Capstone',
      description: 'Bring it together with your own loaf, start to finish.',
    },
  ],
};

export function OutlineReview() {
  const navigate = useNavigate();
  const location = useLocation();
  const attachedFiles = (location.state as { files?: File[] } | null)?.files ?? [];
  const [feedback, setFeedback] = useState('');
  const [requested, setRequested] = useState(false);

  const handleRequestChanges = (e: FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    setRequested(true);
    setFeedback('');
  };

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Here's your course outline</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">Review it, ask for changes, or start learning.</p>

      <Card className="mt-6">
        <p className="text-lg font-semibold text-bonsai-text">{SAMPLE_OUTLINE.title}</p>
        <p className="mt-2 text-sm text-bonsai-text-muted">{SAMPLE_OUTLINE.description}</p>

        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-bonsai-text-muted">Estimated timeline</dt>
            <dd className="font-medium text-bonsai-text">{SAMPLE_OUTLINE.estimatedTimeline}</dd>
          </div>
          <div>
            <dt className="text-bonsai-text-muted">Prerequisites</dt>
            <dd className="font-medium text-bonsai-text">{SAMPLE_OUTLINE.prerequisites.join(', ')}</dd>
          </div>
        </dl>

        <div className="mt-6 space-y-3">
          {SAMPLE_OUTLINE.modules.map((module, i) => (
            <div key={module.title} className="rounded-lg border border-bonsai-border p-3">
              <Badge>Module {i + 1}</Badge>
              <p className="mt-1 font-medium text-bonsai-text">{module.title}</p>
              <p className="mt-0.5 text-sm text-bonsai-text-muted">{module.description}</p>
            </div>
          ))}
        </div>

        {attachedFiles.length > 0 && (
          <div className="mt-6 border-t border-bonsai-border pt-4">
            <p className="text-sm font-medium text-bonsai-text">Source Materials</p>
            <ul className="mt-2 space-y-2">
              {attachedFiles.map((file, i) => (
                <li
                  key={`${file.name}-${i}`}
                  className="flex items-center gap-2 rounded-lg border border-bonsai-border px-3 py-2 text-sm text-bonsai-text"
                >
                  <FileText className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
                  {file.name}
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
        />
        <Button type="submit" variant="secondary">
          Request
        </Button>
      </form>
      {requested && (
        <p className="mt-2 text-sm text-bonsai-green">
          Got it. In the full product this would regenerate the outline with your feedback.
        </p>
      )}

      <Button className="mt-6 w-full" onClick={() => navigate('/courses')}>
        Start Learning
      </Button>
    </div>
  );
}
