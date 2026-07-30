import type { InputHTMLAttributes } from 'react';
import { cn } from './cn';

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'w-full rounded-lg border border-bonsai-border bg-white px-4 py-2.5 text-sm text-bonsai-text placeholder:text-bonsai-text-muted focus:outline-none focus:ring-2 focus:ring-bonsai-green/40',
        className,
      )}
      {...props}
    />
  );
}
