import { useState } from 'react';
import type { QuizQuestion } from '../../types/course';
import { InlineMarkdown } from '../ui/Markdown';

/** Exported: reused as-is by Quiz Me (see pages/QuizMeSession.tsx), not just in-lesson quiz/assessment activities. */
export function QuizQuestionBlock({ question, index, total }: { question: QuizQuestion; index: number; total: number }) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const answered = selectedIndex !== null;
  const isCorrect = answered && selectedIndex === question.correctAnswerIndex;

  return (
    <div>
      <p className="text-sm font-medium text-bonsai-text">
        {total > 1 && <span className="text-bonsai-text-muted">Question {index + 1} of {total}. </span>}
        <InlineMarkdown>{question.question}</InlineMarkdown>
      </p>
      <div className="mt-3 space-y-2">
        {question.options.map((option, optionIndex) => {
          const isCorrectOption = optionIndex === question.correctAnswerIndex;
          const isPickedWrong = answered && optionIndex === selectedIndex && !isCorrectOption;
          return (
            <button
              key={option}
              onClick={() => setSelectedIndex(optionIndex)}
              disabled={isCorrect}
              className={`w-full rounded-lg border px-4 py-2.5 text-left text-sm transition-colors disabled:cursor-not-allowed ${
                isCorrect && isCorrectOption
                  ? 'border-bonsai-green bg-emerald-50 text-bonsai-text'
                  : isPickedWrong
                    ? 'border-red-300 bg-red-50 text-bonsai-text'
                    : 'border-bonsai-border bg-white text-bonsai-text hover:bg-bonsai-cream'
              }`}
            >
              <InlineMarkdown>{option}</InlineMarkdown>
            </button>
          );
        })}
      </div>
      {answered && (
        <div className="mt-3 rounded-lg bg-bonsai-cream p-3">
          <p className={`text-sm font-medium ${isCorrect ? 'text-bonsai-green' : 'text-red-600'}`}>
            {isCorrect ? 'Correct!' : 'Not quite — try again.'}
          </p>
          {isCorrect && question.explanation && (
            <p className="mt-1 text-sm text-bonsai-text-muted">
              <InlineMarkdown>{question.explanation}</InlineMarkdown>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
