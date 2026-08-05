import ReactMarkdown, { type Components } from 'react-markdown';

const sharedComponents: Components = {
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-bonsai-green hover:underline">
      {children}
    </a>
  ),
  code: ({ children }) => <code className="rounded bg-bonsai-cream px-1 py-0.5 text-sm">{children}</code>,
};

/** Full block-level markdown - paragraphs, headings, lists. For long-form content like a reading's body. */
export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        ...sharedComponents,
        p: ({ children }) => <p>{children}</p>,
        h1: ({ children }) => <h1 className="mt-4 text-lg font-semibold first:mt-0">{children}</h1>,
        h2: ({ children }) => <h2 className="mt-4 text-base font-semibold first:mt-0">{children}</h2>,
        h3: ({ children }) => <h3 className="mt-3 text-base font-semibold first:mt-0">{children}</h3>,
        ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        // A visual aid's caption travels as markdown's "alt text" position
        // (![caption](url) - see module_generation.py's _add_visual_aids()),
        // shown as a real, visible caption here rather than left invisible
        // the way a bare <img alt> normally would be.
        img: ({ src, alt }) => (
          <figure className="my-3">
            <img src={src} alt={alt} loading="lazy" className="max-w-full rounded-lg" />
            {alt && <figcaption className="mt-1 text-xs text-bonsai-text-muted">{alt}</figcaption>}
          </figure>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

/**
 * Inline markdown - bold/italic/links/code only, no block-level wrapping. Safe to nest inside
 * headings, badges, buttons, and other elements that can't contain a <p>/<ul>/<h*>. For short,
 * single-line LLM output: titles, quiz questions/options, chat messages.
 */
export function InlineMarkdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        ...sharedComponents,
        p: ({ children }) => <>{children}</>,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
