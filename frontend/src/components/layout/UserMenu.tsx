import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Info, FileText, Shield, ScrollText, Pencil, Download, Upload, Trash2 } from 'lucide-react';
import { useAppData } from '../../context/AppDataContext';
import { ApiError, exportData, importData, resetAllData } from '../../lib/api';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { cn } from '../ui/cn';
import { ConfirmDialog } from './ConfirmDialog';
import { NoticeDialog } from './NoticeDialog';

const INFO_LINKS = [
  { to: '/about', label: 'About Bonsai', icon: Info },
  { to: '/terms', label: 'Terms of Service', icon: FileText },
  { to: '/privacy', label: 'Privacy Policy', icon: Shield },
  { to: '/policy', label: 'User Policy', icon: ScrollText },
];

type DialogStep = 'idle' | 'confirm' | 'notice';

export function UserMenu() {
  const { user, updateUserSettings, refreshCourses } = useAppData();
  const [open, setOpen] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(user.name);
  const [exportStep, setExportStep] = useState<DialogStep>('idle');
  const [exportMessage, setExportMessage] = useState('');
  const [importStep, setImportStep] = useState<DialogStep>('idle');
  const [importMessage, setImportMessage] = useState('');
  const [resetStep, setResetStep] = useState<DialogStep>('idle');
  const [resetMessage, setResetMessage] = useState('');
  const [resetting, setResetting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const initials = user.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setEditingName(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const closeMenu = () => {
    setOpen(false);
    setEditingName(false);
  };

  const saveName = () => {
    const trimmed = nameDraft.trim();
    if (trimmed) updateUserSettings({ name: trimmed }).catch(() => {});
    setEditingName(false);
    setOpen(false);
  };

  const handleExport = async () => {
    try {
      const blob = await exportData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'bonsai-export.zip';
      link.click();
      URL.revokeObjectURL(url);
      setExportMessage('Your data has been downloaded as bonsai-export.zip.');
    } catch (err) {
      console.error('Failed to export data:', err);
      setExportMessage('Something went wrong exporting your data. Please try again.');
    } finally {
      setExportStep('notice');
    }
  };

  const handleImportFile = async (file: File) => {
    try {
      await importData(file);
      await refreshCourses();
      setImportMessage(
        'Your data has been restored. API keys already configured on this installation were left as they were — set them in Settings if this is a new installation.',
      );
    } catch (err) {
      console.error('Failed to import data:', err);
      setImportMessage(
        err instanceof ApiError ? err.message : 'Something went wrong importing your data. Please try again.',
      );
    } finally {
      setImportStep('notice');
    }
  };

  // No success notice: a full page reload is the confirmation itself - it
  // lands back on the first-time onboarding screen, since Settings
  // (including onboardingCompleted) was wiped along with everything else.
  const handleReset = async () => {
    setResetting(true);
    try {
      await resetAllData();
      window.location.reload();
    } catch (err) {
      console.error('Failed to reset Bonsai:', err);
      setResetMessage(
        err instanceof ApiError ? err.message : 'Something went wrong resetting your data. Please try again.',
      );
      setResetStep('notice');
      setResetting(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <input
        ref={importInputRef}
        type="file"
        accept=".zip"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            handleImportFile(file);
          }
          e.target.value = '';
        }}
      />

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-64 rounded-lg border border-bonsai-border bg-white p-2 shadow-lg">
          {editingName ? (
            <div className="flex flex-col gap-2 p-1">
              <Input
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && saveName()}
              />
              <Button onClick={saveName} disabled={!nameDraft.trim()}>
                Save
              </Button>
            </div>
          ) : (
            <>
              <button
                onClick={() => setEditingName(true)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-bonsai-text hover:bg-bonsai-cream"
              >
                <Pencil className="h-4 w-4 text-bonsai-text-muted" />
                Update username
              </button>
              <div className="my-1 border-t border-bonsai-border" />
              <button
                onClick={() => {
                  setExportStep('confirm');
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-bonsai-text hover:bg-bonsai-cream"
              >
                <Download className="h-4 w-4 text-bonsai-text-muted" />
                Export My Data
              </button>
              <button
                onClick={() => {
                  setImportStep('confirm');
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-bonsai-text hover:bg-bonsai-cream"
              >
                <Upload className="h-4 w-4 text-bonsai-text-muted" />
                Import User Data
              </button>
              {INFO_LINKS.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={closeMenu}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-bonsai-text hover:bg-bonsai-cream"
                >
                  <Icon className="h-4 w-4 text-bonsai-text-muted" />
                  {label}
                </Link>
              ))}
              <div className="my-1 border-t border-bonsai-border" />
              <button
                onClick={() => {
                  setResetStep('confirm');
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
                Reset Bonsai
              </button>
            </>
          )}
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-bonsai-cream',
          open && 'bg-bonsai-cream',
        )}
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-bonsai-cream text-xs font-semibold text-bonsai-green">
          {initials}
        </span>
        <span className="flex-1 text-sm font-medium text-bonsai-text">{user.name}</span>
        <ChevronDown className={cn('h-4 w-4 text-bonsai-text-muted transition-transform', open && 'rotate-180')} />
      </button>

      {exportStep === 'confirm' && (
        <ConfirmDialog
          title="Export Your Data"
          description="This will package your course outlines, module content, progress, and settings into a downloadable archive. API keys and other credentials are never included."
          confirmLabel="Export"
          onCancel={() => setExportStep('idle')}
          onConfirm={handleExport}
        />
      )}
      {exportStep === 'notice' && (
        <NoticeDialog title="Export Your Data" message={exportMessage} onClose={() => setExportStep('idle')} />
      )}

      {importStep === 'confirm' && (
        <ConfirmDialog
          title="Import Your Data"
          description="Select a Bonsai export archive (.zip) to restore. This replaces everything currently in this installation — all existing courses and progress — with what's in the archive. API keys aren't included in exports and won't be affected."
          confirmLabel="Choose File"
          onCancel={() => setImportStep('idle')}
          onConfirm={() => {
            setImportStep('idle');
            importInputRef.current?.click();
          }}
        />
      )}
      {importStep === 'notice' && (
        <NoticeDialog title="Import Your Data" message={importMessage} onClose={() => setImportStep('idle')} />
      )}

      {resetStep === 'confirm' && (
        <ConfirmDialog
          title="Reset Bonsai"
          description="This permanently deletes every course, all progress, and all Settings — including your username, model provider configuration, and API keys — and can't be undone. Bonsai will reload afterward as if freshly installed."
          confirmLabel={resetting ? 'Deleting...' : 'Delete everything'}
          confirmWord="delete"
          onCancel={() => setResetStep('idle')}
          onConfirm={handleReset}
        />
      )}
      {resetStep === 'notice' && (
        <NoticeDialog title="Reset Bonsai" message={resetMessage} onClose={() => setResetStep('idle')} />
      )}
    </div>
  );
}
