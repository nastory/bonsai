import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Paperclip, X } from 'lucide-react';
import { ChatBubble } from '../components/chat/ChatBubble';
import { Input } from '../components/ui/Input';
import { cn } from '../components/ui/cn';

interface Message {
  from: 'bonsai' | 'user';
  text: string;
}

// In the real product these are generated dynamically based on the topic and
// prior answers (see PRD "Course Creation & Interview Flow"). Phase 0 scripts
// a fixed, open-ended sequence to exercise the same free-text UI.
const FOLLOW_UP_QUESTIONS = [
  'What is your current experience level with this?',
  "What's motivating you to learn this right now?",
  'Would you like a broad working foundation, or go deep enough to specialize?',
  'Is there a specific area you want to make sure we cover?',
];

const TOTAL_STEPS = FOLLOW_UP_QUESTIONS.length + 1;

export function CreateCourse() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [messages, setMessages] = useState<Message[]>([
    {
      from: 'bonsai',
      text: "What would you like to learn? Be as specific or broad as you like, or attach a document (a paper, an article) and I'll build a course around it.",
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [generating, setGenerating] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
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

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const answer = inputValue.trim();
    if (!answer || generating) return;

    const userMessage: Message = { from: 'user', text: answer };
    setInputValue('');

    if (step === 0) {
      setMessages((prev) => [
        ...prev,
        userMessage,
        {
          from: 'bonsai',
          text: 'Great! To build the right course for you, I have a few quick questions.',
        },
        { from: 'bonsai', text: FOLLOW_UP_QUESTIONS[0] },
      ]);
      setStep(1);
      return;
    }

    const nextQuestion = FOLLOW_UP_QUESTIONS[step];
    if (nextQuestion) {
      setMessages((prev) => [...prev, userMessage, { from: 'bonsai', text: nextQuestion }]);
      setStep((s) => s + 1);
      return;
    }

    // Last question just answered — hand off to the outline.
    setMessages((prev) => [
      ...prev,
      userMessage,
      { from: 'bonsai', text: "Perfect, that's everything I need. Drafting your course outline..." },
    ]);
    setGenerating(true);
    setTimeout(() => navigate('/create/review', { state: { files: attachedFiles } }), 900);
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-bonsai-text">New Course</h1>

      <div className="flex-1 space-y-4 overflow-y-auto">
        {messages.map((message, i) => (
          <ChatBubble key={i} from={message.from}>
            {message.text}
          </ChatBubble>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {attachedFiles.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
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
      )}

      <form onSubmit={handleSubmit} className="mt-6 flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            handleFilesSelected(e.target.files);
            e.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={generating}
          aria-label="Attach documents"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-bonsai-border text-bonsai-text-muted hover:bg-bonsai-cream disabled:opacity-40"
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your answer..."
          disabled={generating}
          autoFocus
        />
        <button
          type="submit"
          disabled={generating || !inputValue.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-bonsai-green text-white disabled:opacity-40"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-4 flex justify-center gap-2">
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
          <span
            key={i}
            className={cn(
              'h-2 w-2 rounded-full',
              i < step ? 'bg-bonsai-green' : i === step ? 'bg-bonsai-green/50' : 'bg-bonsai-border',
            )}
          />
        ))}
      </div>
    </div>
  );
}
