import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, BookOpen, PlusCircle, Layers, ChevronDown, Settings } from 'lucide-react';
import { cn } from '../ui/cn';
import { UserMenu } from './UserMenu';
import logo from '../../assets/logo.svg';

const navItems: { to: string; label: string; icon: typeof Home; end: boolean }[] = [
  { to: '/', label: 'Today', icon: Home, end: true },
  { to: '/courses', label: 'My Courses', icon: BookOpen, end: false },
  { to: '/create', label: 'Create Course', icon: PlusCircle, end: false },
];

const resourceItems = [
  { to: '/resources/flash-cards', label: 'Flash Cards' },
  { to: '/resources/ask-me-anything', label: 'Ask Me Anything' },
  { to: '/resources/quiz-me', label: 'Quiz Me' },
];

const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-bonsai-cream text-bonsai-green'
      : 'text-bonsai-text-muted hover:bg-bonsai-cream hover:text-bonsai-text',
  );

export function Sidebar() {
  const location = useLocation();
  // Starts expanded if a direct link/refresh lands on a Resources sub-page,
  // same "seed from the current route" idea as CourseHome's expandedModules.
  const [expanded, setExpanded] = useState(location.pathname.startsWith('/resources'));

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col justify-between border-r border-bonsai-border bg-white px-4 py-6">
      <div>
        <div className="mb-8 flex items-center gap-2 px-2">
          <img src={logo} alt="Bonsai" className="h-5 w-5" />
          <span className="text-lg font-semibold text-bonsai-text">Bonsai</span>
        </div>

        <nav className="flex flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClasses}>
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}

          <button
            onClick={() => setExpanded((e) => !e)}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors',
              location.pathname.startsWith('/resources')
                ? 'text-bonsai-green'
                : 'text-bonsai-text-muted hover:bg-bonsai-cream hover:text-bonsai-text',
            )}
          >
            <Layers className="h-4 w-4" />
            <span className="flex-1">Resources</span>
            <ChevronDown className={cn('h-4 w-4 transition-transform', expanded && 'rotate-180')} />
          </button>
          {expanded && (
            <div className="ml-4 flex flex-col gap-1 border-l border-bonsai-border pl-3">
              {resourceItems.map(({ to, label }) => (
                <NavLink key={to} to={to} end={false} className={navLinkClasses}>
                  {label}
                </NavLink>
              ))}
            </div>
          )}

          <NavLink to="/settings" end={false} className={navLinkClasses}>
            <Settings className="h-4 w-4" />
            Settings
          </NavLink>
        </nav>
      </div>

      <UserMenu />
    </aside>
  );
}
