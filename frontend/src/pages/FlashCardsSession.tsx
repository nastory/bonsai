import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { generateFlashCards } from '../lib/api';
import { FlashCardBlock } from '../components/resources/FlashCardBlock';
import { InlineMarkdown } from '../components/ui/Markdown';
import type { FlashCardSet } from '../types/course';

export function FlashCardsSession() {
  const { courseId, moduleId } = useParams();
  const { getCourse } = useAppData();
  const [flashCardSet, setFlashCardSet] = useState<FlashCardSet | null>(null);
  const [error, setError] = useState(false);

  const course = courseId ? getCourse(courseId) : undefined;
  const module = course?.modules.find((m) => m.id === moduleId);

  // Idempotent backend (a module's flash cards are generated once and
  // reused forever), safe to call every time this page is opened.
  useEffect(() => {
    if (!moduleId) return;
    setFlashCardSet(null);
    setError(false);
    generateFlashCards(moduleId)
      .then(setFlashCardSet)
      .catch(() => setError(true));
  }, [moduleId]);

  if (!course || !module) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">
          That module couldn't be found.{' '}
          <Link to="/resources/flash-cards" className="font-medium text-bonsai-green">
            Back to Flash Cards
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <Link to="/resources/flash-cards" className="text-sm font-medium text-bonsai-green hover:underline">
        &larr; Flash Cards
      </Link>
      <h1 className="mt-2 text-2xl font-semibold text-bonsai-text">
        <InlineMarkdown>{module.title}</InlineMarkdown>
      </h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">
        <InlineMarkdown>{course.title}</InlineMarkdown>
      </p>

      {error && (
        <p className="mt-6 text-sm text-red-600">Couldn't generate flash cards for this module. Try again later.</p>
      )}

      {!flashCardSet && !error && (
        <div className="mt-6 flex items-center gap-2 text-sm text-bonsai-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating flash cards...
        </div>
      )}

      {flashCardSet && (
        <div className="mt-6 space-y-4">
          {flashCardSet.cards.map((card, i) => (
            <FlashCardBlock key={i} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}
