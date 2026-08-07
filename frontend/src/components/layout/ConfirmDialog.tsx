import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

interface ConfirmDialogProps {
  title: string;
  description: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
  /**
   * When set, the confirm button stays disabled until the user types this
   * exact word - for actions dangerous enough to need more than a click
   * (e.g. resetting all of Bonsai's data). Also switches the confirm
   * button to a destructive red, since every other use of this dialog
   * (export, import, single-course delete) doesn't need one.
   */
  confirmWord?: string;
}

export function ConfirmDialog({ title, description, confirmLabel, onCancel, onConfirm, confirmWord }: ConfirmDialogProps) {
  const [typed, setTyped] = useState('');
  const locked = confirmWord !== undefined && typed !== confirmWord;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4" onClick={onCancel}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <p className="font-semibold text-bonsai-text">{title}</p>
        <p className="mt-2 text-sm text-bonsai-text-muted">{description}</p>
        {confirmWord && (
          <div className="mt-4">
            <label className="text-xs font-medium text-bonsai-text-muted">
              Type <span className="font-semibold text-bonsai-text">{confirmWord}</span> to confirm
            </label>
            <Input value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus className="mt-1" />
          </div>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={locked}
            className={confirmWord ? 'bg-red-600 hover:bg-red-700 disabled:opacity-50' : undefined}
          >
            {confirmLabel}
          </Button>
        </div>
      </Card>
    </div>
  );
}
