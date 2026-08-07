import { Outlet } from 'react-router-dom';
import { useAppData } from '../../context/AppDataContext';
import { Sidebar } from './Sidebar';
import { OnboardingModal } from './OnboardingModal';

export function AppShell() {
  const { user, loading } = useAppData();

  return (
    <div className="flex h-screen overflow-hidden bg-bonsai-cream">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <p className="pointer-events-none fixed bottom-2 right-3 text-xs text-gray-400">
        Nigel Story &copy; {new Date().getFullYear()}
      </p>
      {!loading && !user.onboardingCompleted && <OnboardingModal />}
    </div>
  );
}
