import { cn } from './cn';

interface ProgressBarProps {
  percent: number;
  className?: string;
}

export function ProgressBar({ percent, className }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percent));

  return (
    <div
      className={cn('h-1.5 w-full rounded-full bg-bonsai-border', className)}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-1.5 rounded-full bg-bonsai-green transition-all"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
