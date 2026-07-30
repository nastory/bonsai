import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import logo from '../../assets/logo.svg';

interface ModuleCompletionModalProps {
  moduleTitle: string;
  onKeepGoing: () => void;
  onChangeDirection: (feedback: string) => void;
}

export function ModuleCompletionModal({
  moduleTitle,
  onKeepGoing,
  onChangeDirection,
}: ModuleCompletionModalProps) {
  const [changingDirection, setChangingDirection] = useState(false);
  const [feedback, setFeedback] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <Card className="w-full max-w-md">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bonsai-cream">
            <img src={logo} alt="Bonsai" className="h-4 w-4" />
          </span>
          <div>
            <p className="font-semibold text-bonsai-text">Nice work finishing {moduleTitle}!</p>
            <p className="text-sm text-bonsai-text-muted">How's it going so far?</p>
          </div>
        </div>

        {!changingDirection ? (
          <div className="mt-5 flex flex-col gap-2">
            <Button onClick={onKeepGoing}>Keep going as planned</Button>
            <Button variant="secondary" onClick={() => setChangingDirection(true)}>
              I'd like to change directions...
            </Button>
          </div>
        ) : (
          <form
            className="mt-5 flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!feedback.trim()) return;
              onChangeDirection(feedback);
            }}
          >
            <Input
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="What would you like to focus on instead?"
              autoFocus
            />
            <Button type="submit" disabled={!feedback.trim()}>
              Update remaining modules
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
