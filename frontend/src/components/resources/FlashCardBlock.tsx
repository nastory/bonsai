import { useState } from 'react';
import type { FlashCard } from '../../types/course';
import { Card } from '../ui/Card';
import { InlineMarkdown } from '../ui/Markdown';

/**
 * Click-to-reveal answer, mirroring QuizQuestionBlock's reveal-on-click
 * interaction. No flip animation - nothing in this app does transform
 * animations today beyond a spinner; a real flip is optional future polish.
 */
export function FlashCardBlock({ card }: { card: FlashCard }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-bonsai-text-muted">Question</p>
      <p className="mt-1 text-sm font-medium text-bonsai-text">
        <InlineMarkdown>{card.question}</InlineMarkdown>
      </p>
      {revealed ? (
        <div className="mt-4 rounded-lg bg-bonsai-cream p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-bonsai-text-muted">Answer</p>
          <p className="mt-1 text-sm text-bonsai-text">
            <InlineMarkdown>{card.answer}</InlineMarkdown>
          </p>
        </div>
      ) : (
        <button
          onClick={() => setRevealed(true)}
          className="mt-4 text-sm font-medium text-bonsai-green hover:underline"
        >
          Reveal answer
        </button>
      )}
    </Card>
  );
}
