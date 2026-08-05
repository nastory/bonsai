import { InlineMarkdown } from '../ui/Markdown';
import logo from '../../assets/logo.svg';

interface ChatBubbleProps {
  from: 'bonsai' | 'user';
  children: string;
}

export function ChatBubble({ from, children }: ChatBubbleProps) {
  if (from === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-md rounded-2xl rounded-tr-sm bg-bonsai-green px-4 py-3 text-sm text-white">
          <InlineMarkdown>{children}</InlineMarkdown>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bonsai-cream">
        <img src={logo} alt="Bonsai" className="h-4 w-4" />
      </span>
      <div className="max-w-md rounded-2xl rounded-tl-sm bg-bonsai-cream px-4 py-3 text-sm text-bonsai-text">
        <InlineMarkdown>{children}</InlineMarkdown>
      </div>
    </div>
  );
}
