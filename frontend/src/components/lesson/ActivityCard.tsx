import { useState } from 'react';
import { PlayCircle } from 'lucide-react';
import type { Activity } from '../../types/course';
import { useAppData } from '../../context/AppDataContext';
import { getFeedbackMessage } from '../../lib/feedback';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { ChatBubble } from '../chat/ChatBubble';

function ReadingBody({ body }: { body: string }) {
  const lines = body.split('\n').filter(Boolean);
  return (
    <div className="space-y-2 text-sm leading-relaxed text-bonsai-text">
      {lines.map((line, i) => {
        const numbered = line.match(/^(\d+)\.\s+(.*)$/);
        if (numbered) {
          const [, index, rest] = numbered;
          const [label, ...detail] = rest.split(': ');
          return (
            <div key={i} className="flex items-start gap-3 rounded-lg bg-bonsai-cream px-3 py-2">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-bonsai-green">
                {index}
              </span>
              <p>
                <span className="font-medium">{label}</span>
                {detail.length > 0 && <span className="text-bonsai-text-muted">: {detail.join(': ')}</span>}
              </p>
            </div>
          );
        }
        return <p key={i}>{line}</p>;
      })}
    </div>
  );
}

function Citations({ citations }: { citations: NonNullable<Activity['citations']> }) {
  return (
    <ul className="mt-4 space-y-1 border-t border-bonsai-border pt-3 text-xs text-bonsai-text-muted">
      {citations.map((citation) => (
        <li key={citation.url}>
          <a href={citation.url} target="_blank" rel="noreferrer" className="hover:text-bonsai-green hover:underline">
            {citation.label}
          </a>
        </li>
      ))}
    </ul>
  );
}

function CheckUnderstanding({ prompt, tone }: { prompt: string; tone: 'encouraging' | 'straightforward' }) {
  const [answer, setAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="mt-5 rounded-lg border border-bonsai-green/30 bg-emerald-50 p-4">
      <p className="text-sm font-medium text-bonsai-green">Check your understanding</p>
      <p className="mt-1 text-sm text-bonsai-text">{prompt}</p>
      <div className="mt-3 flex gap-2">
        <Input
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Write your answer..."
          disabled={submitted}
        />
        <Button
          variant="primary"
          disabled={!answer.trim() || submitted}
          onClick={() => setSubmitted(true)}
        >
          Check
        </Button>
      </div>
      {submitted && <p className="mt-2 text-sm text-bonsai-green">{getFeedbackMessage(tone, 'check')}</p>}
    </div>
  );
}

function QuizBlock({ activity, tone }: { activity: Activity; tone: 'encouraging' | 'straightforward' }) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div>
      <p className="text-sm font-medium text-bonsai-text">{activity.question}</p>
      <div className="mt-3 space-y-2">
        {activity.options?.map((option) => (
          <button
            key={option}
            onClick={() => setSelected(option)}
            className={`w-full rounded-lg border px-4 py-2.5 text-left text-sm transition-colors ${
              selected === option
                ? 'border-bonsai-green bg-emerald-50 text-bonsai-text'
                : 'border-bonsai-border bg-white text-bonsai-text hover:bg-bonsai-cream'
            }`}
          >
            {option}
          </button>
        ))}
      </div>
      {selected && (
        <p className="mt-3 text-sm text-bonsai-green">{getFeedbackMessage(tone, 'quiz')}</p>
      )}
    </div>
  );
}

function OpenResponseBlock({
  activity,
  tone,
  kind,
}: {
  activity: Activity;
  tone: 'encouraging' | 'straightforward';
  kind: 'essay' | 'project';
}) {
  const [response, setResponse] = useState('');
  const [submitted, setSubmitted] = useState(false);

  return (
    <div>
      <p className="text-sm text-bonsai-text">{activity.prompt}</p>
      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        disabled={submitted}
        rows={5}
        placeholder={kind === 'project' ? 'Describe what you built or tried...' : 'Write your response...'}
        className="mt-3 w-full rounded-lg border border-bonsai-border bg-white px-4 py-3 text-sm text-bonsai-text placeholder:text-bonsai-text-muted focus:outline-none focus:ring-2 focus:ring-bonsai-green/40"
      />
      <Button className="mt-3" disabled={!response.trim() || submitted} onClick={() => setSubmitted(true)}>
        Submit
      </Button>
      {submitted && <p className="mt-3 text-sm text-bonsai-green">{getFeedbackMessage(tone, kind)}</p>}
    </div>
  );
}

function DiscussionBlock({ activity, tone }: { activity: Activity; tone: 'encouraging' | 'straightforward' }) {
  const [reply, setReply] = useState('');
  const [sent, setSent] = useState(false);

  return (
    <div className="space-y-3">
      <ChatBubble from="bonsai">{activity.prompt}</ChatBubble>
      {sent && <ChatBubble from="user">{reply}</ChatBubble>}
      {sent && <ChatBubble from="bonsai">{getFeedbackMessage(tone, 'discussion')}</ChatBubble>}
      {!sent && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!reply.trim()) return;
            setSent(true);
          }}
          className="flex gap-2"
        >
          <Input value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Type your reply..." />
          <Button type="submit" disabled={!reply.trim()}>
            Send
          </Button>
        </form>
      )}
    </div>
  );
}

export function ActivityCard({ activity }: { activity: Activity }) {
  const { user } = useAppData();
  const tone = user.feedbackTone;

  return (
    <Card>
      {activity.type === 'reading' && activity.body && (
        <>
          <ReadingBody body={activity.body} />
          {activity.citations && <Citations citations={activity.citations} />}
          {activity.checkPrompt && <CheckUnderstanding prompt={activity.checkPrompt} tone={tone} />}
        </>
      )}

      {activity.type === 'video' && (
        <div className="flex flex-col items-center justify-center rounded-lg bg-bonsai-cream py-16 text-center">
          <PlayCircle className="h-10 w-10 text-bonsai-text-muted" />
          <p className="mt-3 text-sm text-bonsai-text-muted">Video embedding arrives in Phase 2.</p>
        </div>
      )}

      {(activity.type === 'quiz' || activity.type === 'assessment') && (
        <QuizBlock activity={activity} tone={tone} />
      )}

      {activity.type === 'essay' && <OpenResponseBlock activity={activity} tone={tone} kind="essay" />}

      {activity.type === 'project' && <OpenResponseBlock activity={activity} tone={tone} kind="project" />}

      {activity.type === 'discussion' && <DiscussionBlock activity={activity} tone={tone} />}
    </Card>
  );
}
