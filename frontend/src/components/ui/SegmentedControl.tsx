import { cn } from './cn';

/** Extracted from Settings.tsx - also used by OnboardingModal.tsx for the same tier/provider toggle pattern. */
export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-bonsai-border bg-white p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            value === option.value
              ? 'bg-bonsai-green text-white'
              : 'text-bonsai-text-muted hover:text-bonsai-text',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
