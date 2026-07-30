import { NavLink } from 'react-router-dom';
import { Home, BookOpen, PlusCircle, Library, Settings, Sprout } from 'lucide-react';
import { cn } from '../ui/cn';
import { UserMenu } from './UserMenu';

const navItems: { to: string; label: string; icon: typeof Home; end: boolean }[] = [
  { to: '/', label: 'Today', icon: Home, end: true },
  { to: '/courses', label: 'My Courses', icon: BookOpen, end: false },
  { to: '/create', label: 'Create Course', icon: PlusCircle, end: false },
  { to: '/library', label: 'Library', icon: Library, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col justify-between border-r border-bonsai-border bg-white px-4 py-6">
      <div>
        <div className="mb-8 flex items-center gap-2 px-2">
          <Sprout className="h-5 w-5 text-bonsai-green" />
          <span className="text-lg font-semibold text-bonsai-text">Bonsai</span>
        </div>

        <nav className="flex flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-bonsai-cream text-bonsai-green'
                    : 'text-bonsai-text-muted hover:bg-bonsai-cream hover:text-bonsai-text',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <UserMenu />
    </aside>
  );
}
