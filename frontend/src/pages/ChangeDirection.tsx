import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
import { ChatBubble } from '../components/chat/ChatBubble';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { cn } from '../components/ui/cn';
import { ApiError, startDirectionChange, submitDirectionChangeAnswer, generateDirectionChangeOutline } from '../lib/api';

interface Message {
  from: 'bonsai' | 'user';
  text: string;
}

// Matches the backend's MAX_INTERVIEW_QUESTIONS, reused for this interview too
// (app/services/course_generation.py). Not shared code between frontend/backend
// yet, just kept in sync by hand - this drifted out of sync once already (was
// 10 here after the backend dropped to 7), so double-check this value against
// that constant directly before trusting it again.
const MAX_QUESTIONS = 7;

export function ChangeDirection() {
  const navigate = useNavigate();
  const { courseId, moduleId } = useParams();
  const [started, setStarted] = useState(false);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [messages, setMessages] = useState<Message[]>([
    {
      from: 'bonsai',
      text: "What would you like different going forward? Be as specific or broad as you like — I'll build on what you've already covered, not repeat it.",
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text || !moduleId || generating || sending) return;

    setMessages((prev) => [...prev, { from: 'user', text }]);
    setInputValue('');
    setSending(true);

    try {
      const step = started
        ? await submitDirectionChangeAnswer(moduleId, text)
        : await startDirectionChange(moduleId, text);
      setStarted(true);
      setQuestionsAnswered((n) => n + 1);

      setMessages((prev) => [
        ...prev,
        {
          from: 'bonsai',
          text: step.done
            ? "I have what I need. I'll draft a new set of modules for the rest of this course now."
            : step.question ?? '',
        },
      ]);

      if (step.done) {
        setGenerating(true);
        const proposal = await generateDirectionChangeOutline(moduleId);
        navigate(`/courses/${courseId}/modules/${moduleId}/change-direction/review`, { state: { proposal } });
      }
    } catch (err) {
      console.error('Direction-change interview failed:', err);
      const text =
        err instanceof ApiError ? err.message : "Something went wrong on my end. Mind trying that again?";
      setMessages((prev) => [...prev, { from: 'bonsai', text }]);
      setGenerating(false);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-bonsai-text">Change This Course</h1>

      <div className="flex-1 space-y-4 overflow-y-auto">
        {messages.map((message, i) => (
          <ChatBubble key={i} from={message.from}>
            {message.text}
          </ChatBubble>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex items-center gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your answer..."
          disabled={generating || sending}
          autoFocus
        />
        <button
          type="submit"
          disabled={generating || sending || !inputValue.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-bonsai-green text-white disabled:opacity-40"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-4 flex justify-center gap-2">
        {Array.from({ length: MAX_QUESTIONS }).map((_, i) => (
          <span
            key={i}
            className={cn(
              'h-2 w-2 rounded-full',
              i < questionsAnswered ? 'bg-bonsai-green' : 'bg-bonsai-border',
            )}
          />
        ))}
      </div>

      {generating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <Card className="flex w-full max-w-sm flex-col items-center gap-3 py-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-bonsai-green" />
            <p className="font-semibold text-bonsai-text">Drafting the rest of your course...</p>
            <p className="text-sm text-bonsai-text-muted">
              This can take a little while, especially with a local model.
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
