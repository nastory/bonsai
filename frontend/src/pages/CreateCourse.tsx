import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, Paperclip, X } from 'lucide-react';
import { ChatBubble } from '../components/chat/ChatBubble';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Toggle } from '../components/ui/Toggle';
import { cn } from '../components/ui/cn';
import { ApiError, startCourse, submitInterviewAnswer, generateOutline } from '../lib/api';

interface Message {
  from: 'bonsai' | 'user';
  text: string;
}

interface CreateCourseLocationState {
  /** Set when arriving here via "Branch Off" from a module-completion check-in. */
  parentCourseId?: string;
}

// Matches the backend's MAX_INTERVIEW_QUESTIONS (app/services/course_generation.py).
// Not shared code between frontend/backend yet, just kept in sync by hand -
// this drifted out of sync once already (was 10 here after the backend
// dropped to 7), so double-check this value against that constant directly
// before trusting it again.
const MAX_QUESTIONS = 7;

export function CreateCourse() {
  const navigate = useNavigate();
  const location = useLocation();
  const parentCourseId = (location.state as CreateCourseLocationState | null)?.parentCourseId;
  const [courseId, setCourseId] = useState<string | null>(null);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [messages, setMessages] = useState<Message[]>([
    {
      from: 'bonsai',
      text: parentCourseId
        ? "What would you like to explore next, building on what you've already covered? Be as specific or broad as you like."
        : "What would you like to learn? Be as specific or broad as you like, or attach a document (a paper, an article) and I'll build a course around it.",
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [supplementWithWebSearch, setSupplementWithWebSearch] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleFilesSelected = (fileList: FileList | null) => {
    if (!fileList) return;
    setAttachedFiles((prev) => [...prev, ...Array.from(fileList)]);
  };

  const removeFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text || generating || sending) return;

    const filesToSend = attachedFiles;
    const hasFiles = filesToSend.length > 0;

    setMessages((prev) => [
      ...prev,
      { from: 'user', text },
      ...(hasFiles
        ? [{ from: 'bonsai', text: filesToSend.length > 1 ? 'Parsing documents...' : 'Parsing document...' } as Message]
        : []),
    ]);
    setInputValue('');
    setSending(true);

    try {
      const step = courseId
        ? await submitInterviewAnswer(courseId, text, filesToSend, supplementWithWebSearch)
        : await startCourse(text, filesToSend, parentCourseId, supplementWithWebSearch);
      if (!courseId) setCourseId(step.courseId);
      setQuestionsAnswered((n) => n + 1);
      setAttachedFiles([]);
      setSupplementWithWebSearch(false);

      setMessages((prev) => {
        const base = hasFiles ? prev.slice(0, -1) : prev;
        const text = step.done
          ? "I have all the info I need. I'll draft a course outline for you now."
          : step.question ?? '';
        return [...base, { from: 'bonsai', text }];
      });

      if (step.done) {
        setGenerating(true);
        const course = await generateOutline(step.courseId);
        navigate(`/create/review/${course.id}`);
      }
    } catch (err) {
      console.error('Course creation failed:', err);
      const text =
        err instanceof ApiError ? err.message : "Something went wrong on my end. Mind trying that again?";
      setMessages((prev) => {
        const base = hasFiles ? prev.slice(0, -1) : prev;
        return [...base, { from: 'bonsai', text }];
      });
      setGenerating(false);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-bonsai-text">
        {parentCourseId ? 'Branch Off' : 'New Course'}
      </h1>

      <div className="flex-1 space-y-4 overflow-y-auto">
        {messages.map((message, i) => (
          <ChatBubble key={i} from={message.from}>
            {message.text}
          </ChatBubble>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {attachedFiles.length > 0 && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {attachedFiles.map((file, i) => (
              <span
                key={`${file.name}-${i}`}
                className="flex items-center gap-2 rounded-full border border-bonsai-border bg-white px-3 py-1 text-xs text-bonsai-text"
              >
                <Paperclip className="h-3 w-3 text-bonsai-text-muted" />
                {file.name}
                <button onClick={() => removeFile(i)} aria-label={`Remove ${file.name}`}>
                  <X className="h-3 w-3 text-bonsai-text-muted hover:text-bonsai-text" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex items-center justify-between rounded-lg border border-bonsai-border bg-white px-3 py-2">
            <span className="text-xs text-bonsai-text">Also search the web to supplement this document</span>
            <Toggle checked={supplementWithWebSearch} onChange={setSupplementWithWebSearch} />
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-6 flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".txt,.docx,.pdf"
          className="hidden"
          onChange={(e) => {
            handleFilesSelected(e.target.files);
            e.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={generating || sending}
          aria-label="Attach documents"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-bonsai-border text-bonsai-text-muted hover:bg-bonsai-cream disabled:opacity-40"
        >
          <Paperclip className="h-4 w-4" />
        </button>
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
            <p className="font-semibold text-bonsai-text">Drafting your course outline...</p>
            <p className="text-sm text-bonsai-text-muted">
              This can take a little while, especially with a local model.
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
