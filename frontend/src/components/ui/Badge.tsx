import type { HTMLAttributes } from 'react';
import { cn } from './cn';

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'text-xs font-semibold uppercase tracking-wide text-bonsai-green',
        className,
      )}
      {...props}
    />
  );
}
