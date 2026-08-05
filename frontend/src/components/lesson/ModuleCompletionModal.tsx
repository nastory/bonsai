import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { InlineMarkdown } from '../ui/Markdown';
import logo from '../../assets/logo.svg';

interface ModuleCompletionModalProps {
  moduleTitle: string;
  onKeepGoing: () => void;
  onBranchOff: () => void;
  /** Omitted when the just-finished module was the course's last one — there's nothing ahead to change. */
  onChangeThisCourse?: () => void;
}

export function ModuleCompletionModal({
  moduleTitle,
  onKeepGoing,
  onBranchOff,
  onChangeThisCourse,
}: ModuleCompletionModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <Card className="w-full max-w-md">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bonsai-cream">
            <img src={logo} alt="Bonsai" className="h-4 w-4" />
          </span>
          <div>
            <p className="font-semibold text-bonsai-text">
              Nice work finishing <InlineMarkdown>{moduleTitle}</InlineMarkdown>!
            </p>
            <p className="text-sm text-bonsai-text-muted">How's it going so far?</p>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={onKeepGoing}>Keep going as planned</Button>
          <Button variant="secondary" onClick={onBranchOff}>
            Branch off into a new course
          </Button>
          {onChangeThisCourse && (
            <Button variant="secondary" onClick={onChangeThisCourse}>
              Change this course
            </Button>
          )}
        </div>
        <p className="mt-3 text-xs text-bonsai-text-muted">
          {onChangeThisCourse
            ? "Branching off starts a new course from here, keeping this one exactly as it is. Changing this course replaces what's ahead in this same course — what you've already finished stays intact either way."
            : "That was the last module. Branching off starts a new course from here, keeping this one exactly as it is."}
        </p>
      </Card>
    </div>
  );
}
