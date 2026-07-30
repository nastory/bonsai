import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

interface NoticeDialogProps {
  title: string;
  message: string;
  onClose: () => void;
}

export function NoticeDialog({ title, message, onClose }: NoticeDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4" onClick={onClose}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <p className="font-semibold text-bonsai-text">{title}</p>
        <p className="mt-2 text-sm text-bonsai-text-muted">{message}</p>
        <div className="mt-5 flex justify-end">
          <Button onClick={onClose}>Close</Button>
        </div>
      </Card>
    </div>
  );
}
