import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Info, FileText, Shield, ScrollText, Pencil, Download } from 'lucide-react';
import { useAppData } from '../../context/AppDataContext';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { cn } from '../ui/cn';

const INFO_LINKS = [
  { to: '/about', label: 'About Bonsai', icon: Info },
  { to: '/terms', label: 'Terms of Service', icon: FileText },
  { to: '/privacy', label: 'Privacy Policy', icon: Shield },
  { to: '/policy', label: 'User Policy', icon: ScrollText },
];

export function UserMenu() {
  const { user, updateUserSettings } = useAppData();
  const [open, setOpen] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(user.name);
  const [showExportNote, setShowExportNote] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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
        setShowExportNote(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const closeMenu = () => {
    setOpen(false);
    setEditingName(false);
    setShowExportNote(false);
  };

  const saveName = () => {
    const trimmed = nameDraft.trim();
    if (trimmed) updateUserSettings({ name: trimmed });
    setEditingName(false);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
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
                onClick={() => setShowExportNote(true)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-bonsai-text hover:bg-bonsai-cream"
              >
                <Download className="h-4 w-4 text-bonsai-text-muted" />
                Export My Data
              </button>
              {showExportNote && (
                <p className="px-3 pb-1 text-xs text-bonsai-text-muted">
                  Not wired up yet. Phase 1 will let you download your data as an archive.
                </p>
              )}
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
    </div>
  );
}
