import type { ButtonHTMLAttributes } from 'react';
import { cn } from './cn';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-bonsai-green text-white hover:bg-bonsai-green-hover disabled:opacity-50',
  secondary:
    'bg-white text-bonsai-text border border-bonsai-border hover:bg-bonsai-cream disabled:opacity-50',
  ghost: 'bg-transparent text-bonsai-text hover:bg-bonsai-cream disabled:opacity-50',
};

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed',
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
