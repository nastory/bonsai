import { Check, X } from 'lucide-react';
import type { ComponentProps } from 'react';
import { Input } from './Input';
import { cn } from './cn';

/** Extracted from Settings.tsx - also used by OnboardingModal.tsx for the same draft-save-status key pattern. */
export type SaveStatus = 'idle' | 'saved' | 'error';

export function KeyInput({
  status,
  className,
  ...props
}: ComponentProps<typeof Input> & { status: SaveStatus }) {
  return (
    <div className={cn('relative', className)}>
      <Input className={cn(status !== 'idle' && 'pr-10')} {...props} />
      {status === 'saved' && (
        <Check className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-green-600" />
      )}
      {status === 'error' && (
        <X className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-red-600" />
      )}
    </div>
  );
}
