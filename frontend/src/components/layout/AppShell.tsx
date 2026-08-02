import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-bonsai-cream">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <p className="pointer-events-none fixed bottom-2 right-3 text-xs text-gray-400">
        Nigel Story &copy; {new Date().getFullYear()}
      </p>
    </div>
  );
}
