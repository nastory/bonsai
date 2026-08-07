import { useState, type FormEvent } from 'react';
import { Loader2 } from 'lucide-react';
import type { Activity, DiscussionMessage } from '../../types/course';
import { generateActivityFeedback, submitDiscussionReply } from '../../lib/api';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Markdown, InlineMarkdown } from '../ui/Markdown';
import { ChatBubble } from '../chat/ChatBubble';
import { Citations } from '../chat/Citations';
import { QuizQuestionBlock } from './QuizQuestionBlock';

function ReadingBody({ body }: { body: string }) {
  return (
    <div className="space-y-3 text-base leading-relaxed text-bonsai-text">
      <Markdown>{body}</Markdown>
    </div>
  );
}

function VideoBlock({ activity }: { activity: Activity }) {
  if (!activity.videoId) {
    return null;
  }
  return (
    <figure>
      <div className="aspect-video w-full overflow-hidden rounded-lg bg-black">
        <iframe
          className="h-full w-full"
          src={`https://www.youtube.com/embed/${activity.videoId}`}
          title={activity.title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
      {activity.caption && (
        <figcaption className="mt-2 text-sm text-bonsai-text-muted">
          <InlineMarkdown>{activity.caption}</InlineMarkdown>
        </figcaption>
      )}
    </figure>
  );
}

type FeedbackStatus = 'idle' | 'loading' | 'done' | 'error';

/**
 * Calls the real feedback endpoint (POST /api/activities/:id/feedback) for a
 * free-text response, instead of the fixed canned copy this used to show
 * regardless of what was actually written. The backend reads the learner's
 * configured feedback tone itself, so nothing here needs to know or pass it.
 */
function useActivityFeedback(activityId: string) {
  const [status, setStatus] = useState<FeedbackStatus>('idle');
  const [feedback, setFeedback] = useState('');

  const submit = async (response: string) => {
    setStatus('loading');
    try {
      const result = await generateActivityFeedback(activityId, response);
      setFeedback(result.feedback);
      setStatus('done');
    } catch (err) {
      console.error('Failed to generate feedback:', err);
      setFeedback("Thanks for writing that — couldn't generate feedback just now, but it's worth revisiting later.");
      setStatus('error');
    }
  };

  return { status, feedback, submit };
}

function CheckUnderstanding({ activityId, prompt }: { activityId: string; prompt: string }) {
  const [answer, setAnswer] = useState('');
  const { status, feedback, submit } = useActivityFeedback(activityId);
  const done = status === 'done' || status === 'error';

  return (
    <div className="mt-5 rounded-lg border border-bonsai-green/30 bg-emerald-50 p-4">
      <p className="text-sm font-medium text-bonsai-green">Check your understanding</p>
      <p className="mt-1 text-sm text-bonsai-text">
        <InlineMarkdown>{prompt}</InlineMarkdown>
      </p>
      <div className="mt-3 flex gap-2">
        <Input
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Write your answer..."
          disabled={status === 'loading' || done}
        />
        <Button
          variant="primary"
          disabled={!answer.trim() || status === 'loading' || done}
          onClick={() => submit(answer.trim())}
        >
          {status === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Check'}
        </Button>
      </div>
      {done && <p className="mt-2 text-sm text-bonsai-green">{feedback}</p>}
    </div>
  );
}

function QuizBlock({ activity }: { activity: Activity }) {
  const questions = activity.questions ?? [];

  return (
    <div className="space-y-6">
      {questions.map((question, index) => (
        <QuizQuestionBlock key={index} question={question} index={index} total={questions.length} />
      ))}
    </div>
  );
}

function OpenResponseBlock({ activity, kind }: { activity: Activity; kind: 'essay' | 'project' | 'capstone' }) {
  const [response, setResponse] = useState('');
  const { status, feedback, submit } = useActivityFeedback(activity.id);
  const done = status === 'done' || status === 'error';

  return (
    <div>
      <p className="text-sm text-bonsai-text">
        <InlineMarkdown>{activity.prompt ?? ''}</InlineMarkdown>
      </p>
      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        disabled={status === 'loading' || done}
        rows={5}
        placeholder={kind === 'essay' ? 'Write your response...' : 'Describe what you built or tried...'}
        className="mt-3 w-full rounded-lg border border-bonsai-border bg-white px-4 py-3 text-sm text-bonsai-text placeholder:text-bonsai-text-muted focus:outline-none focus:ring-2 focus:ring-bonsai-green/40"
      />
      <Button
        className="mt-3"
        disabled={!response.trim() || status === 'loading' || done}
        onClick={() => submit(response.trim())}
      >
        {status === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit'}
      </Button>
      {done && <p className="mt-3 text-sm text-bonsai-green">{feedback}</p>}
    </div>
  );
}

function DiscussionBlock({ activity }: { activity: Activity }) {
  // A real multi-turn conversation (target 3, hard cap 5 exchanges - see
  // app/services/discussion.py), not the single-shot submit-and-get-feedback
  // flow the other free-response blocks use. Seeded from the activity's
  // already-persisted thread (activity.messages/discussionDone) so a page
  // refresh picks up right where an in-progress discussion left off, with
  // no separate fetch needed - the course reload that already happens on
  // mount already carries this.
  const [messages, setMessages] = useState<DiscussionMessage[]>(activity.messages ?? []);
  const [done, setDone] = useState(activity.discussionDone ?? false);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending || done) return;

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setSending(true);
    setError(false);

    try {
      const result = await submitDiscussionReply(activity.id, trimmed);
      setMessages((prev) => [...prev, { role: 'assistant', content: result.message }]);
      setDone(result.done);
    } catch {
      setError(true);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-3">
      <ChatBubble from="bonsai">{activity.prompt ?? ''}</ChatBubble>
      {messages.map((message, i) => (
        <ChatBubble key={i} from={message.role === 'user' ? 'user' : 'bonsai'}>
          {message.content}
        </ChatBubble>
      ))}
      {sending && (
        <div className="flex items-center gap-2 pl-11 text-sm text-bonsai-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Thinking about your reply...
        </div>
      )}
      {error && <p className="pl-11 text-sm text-red-600">Couldn't send that — try again.</p>}
      {!done && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your reply..."
            disabled={sending}
          />
          <Button type="submit" disabled={!input.trim() || sending}>
            Send
          </Button>
        </form>
      )}
    </div>
  );
}

export function ActivityCard({ activity }: { activity: Activity }) {
  return (
    <Card>
      {activity.type === 'reading' && activity.body && (
        <>
          <ReadingBody body={activity.body} />
          {activity.citations && <Citations citations={activity.citations} />}
          {activity.checkPrompt && <CheckUnderstanding activityId={activity.id} prompt={activity.checkPrompt} />}
        </>
      )}

      {activity.type === 'video' && <VideoBlock activity={activity} />}

      {(activity.type === 'quiz' || activity.type === 'assessment') && (
        <QuizBlock activity={activity} />
      )}

      {activity.type === 'essay' && <OpenResponseBlock activity={activity} kind="essay" />}

      {activity.type === 'project' && <OpenResponseBlock activity={activity} kind="project" />}

      {activity.type === 'discussion' && <DiscussionBlock activity={activity} />}

      {activity.type === 'capstone' && <OpenResponseBlock activity={activity} kind="capstone" />}
    </Card>
  );
}
