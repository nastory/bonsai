import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { generateQuizSet } from '../lib/api';
import { QuizQuestionBlock } from '../components/lesson/QuizQuestionBlock';
import { Card } from '../components/ui/Card';
import { InlineMarkdown } from '../components/ui/Markdown';
import type { QuizSet } from '../types/course';

export function QuizMeSession() {
  const { courseId, moduleId } = useParams();
  const { getCourse } = useAppData();
  const [quizSet, setQuizSet] = useState<QuizSet | null>(null);
  const [error, setError] = useState(false);

  const course = courseId ? getCourse(courseId) : undefined;
  const module = course?.modules.find((m) => m.id === moduleId);

  // Idempotent backend (a module's quiz is generated once and reused
  // forever), safe to call every time this page is opened.
  useEffect(() => {
    if (!moduleId) return;
    setQuizSet(null);
    setError(false);
    generateQuizSet(moduleId)
      .then(setQuizSet)
      .catch(() => setError(true));
  }, [moduleId]);

  if (!course || !module) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <p className="text-sm text-bonsai-text-muted">
          That module couldn't be found.{' '}
          <Link to="/resources/quiz-me" className="font-medium text-bonsai-green">
            Back to Quiz Me
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <Link to="/resources/quiz-me" className="text-sm font-medium text-bonsai-green hover:underline">
        &larr; Quiz Me
      </Link>
      <h1 className="mt-2 text-2xl font-semibold text-bonsai-text">
        <InlineMarkdown>{module.title}</InlineMarkdown>
      </h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">
        <InlineMarkdown>{course.title}</InlineMarkdown>
      </p>

      {error && <p className="mt-6 text-sm text-red-600">Couldn't generate a quiz for this module. Try again later.</p>}

      {!quizSet && !error && (
        <div className="mt-6 flex items-center gap-2 text-sm text-bonsai-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating your quiz...
        </div>
      )}

      {quizSet && (
        <Card className="mt-6 space-y-6">
          {quizSet.questions.map((question, index) => (
            <QuizQuestionBlock key={index} question={question} index={index} total={quizSet.questions.length} />
          ))}
        </Card>
      )}
    </div>
  );
}
