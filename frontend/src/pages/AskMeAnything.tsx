import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { askAMA } from '../lib/api';
import { ChatBubble } from '../components/chat/ChatBubble';
import { Citations } from '../components/chat/Citations';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import type { AMAMessage } from '../types/course';

/**
 * Mirrors DiscussionBlock closely (message-array state, inline loading row,
 * boolean error -> static retry text, one POST per turn), but this chat
 * never closes (no done/wrap-up concept) and renders citations under
 * assistant messages. No persistence - resets on reload, the client just
 * resends its own transcript each turn (see app/services/ama.py).
 */
export function AskMeAnything() {
  const { user } = useAppData();
  const [messages, setMessages] = useState<AMAMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);

  // A learner who's never configured an embedding model has zero AMA
  // coverage across every course - a distinct empty state, not the same
  // generic per-question decline used for genuinely off-topic questions.
  if (!user.embeddingModel) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-10">
        <h1 className="text-2xl font-semibold text-bonsai-text">Ask Me Anything</h1>
        <p className="mt-4 text-sm text-bonsai-text-muted">
          Ask Me Anything needs an embedding model configured to search your course materials.{' '}
          <Link to="/settings" className="font-medium text-bonsai-green hover:underline">
            Set one up in Settings
          </Link>
          .
        </p>
      </div>
    );
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const history = messages;
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setSending(true);
    setError(false);

    try {
      const result = await askAMA(trimmed, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply, citations: result.citations }]);
    } catch {
      setError(true);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Ask Me Anything</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">
        Chat about your course materials — Bonsai answers from what you've actually learned, not general knowledge.
      </p>

      <div className="mt-6 flex-1 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-bonsai-text-muted">Ask a question about any of your courses to get started.</p>
        )}
        {messages.map((message, i) => (
          <div key={i}>
            <ChatBubble from={message.role === 'user' ? 'user' : 'bonsai'}>{message.content}</ChatBubble>
            {message.citations && message.citations.length > 0 && (
              <div className="pl-11">
                <Citations citations={message.citations} />
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="flex items-center gap-2 pl-11 text-sm text-bonsai-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking...
          </div>
        )}
        {error && <p className="pl-11 text-sm text-red-600">Couldn't send that — try again.</p>}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your courses..."
          disabled={sending}
        />
        <Button type="submit" disabled={!input.trim() || sending}>
          Send
        </Button>
      </form>
    </div>
  );
}
