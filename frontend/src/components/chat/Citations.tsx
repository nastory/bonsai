import type { Citation } from '../../types/course';

/** Exported: reused as-is by Ask Me Anything (see pages/AskMeAnything.tsx), not just reading activities. */
export function Citations({ citations }: { citations: Citation[] }) {
  return (
    <ul className="mt-4 space-y-1 border-t border-bonsai-border pt-3 text-xs text-bonsai-text-muted">
      {citations.map((citation, i) => (
        <li key={`${citation.label}-${i}`}>
          {citation.url ? (
            <a
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="hover:text-bonsai-green hover:underline"
            >
              {citation.label}
            </a>
          ) : (
            citation.label
          )}
        </li>
      ))}
    </ul>
  );
}
