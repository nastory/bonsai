import { Outlet, useLocation } from 'react-router-dom';
import { useAppData } from '../../context/AppDataContext';
import { Sidebar } from './Sidebar';
import { OnboardingModal } from './OnboardingModal';

// Onboarding's final step links out to these two pages so a learner can
// actually read them before agreeing (see OnboardingModal.tsx) - the modal
// itself is a fixed full-screen overlay on every other route, so without
// this exemption a link opened in a new tab would just show the same
// modal on top of the page it's trying to link to.
const ONBOARDING_LINK_ROUTES = ['/terms', '/policy'];

export function AppShell() {
  const { user, loading } = useAppData();
  const location = useLocation();
  const showOnboarding = !loading && !user.onboardingCompleted && !ONBOARDING_LINK_ROUTES.includes(location.pathname);

  return (
    <div className="flex h-screen overflow-hidden bg-bonsai-cream">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <p className="pointer-events-none fixed bottom-2 right-3 text-xs text-gray-400">
        Nigel Story &copy; {new Date().getFullYear()}
      </p>
      {showOnboarding && <OnboardingModal />}
    </div>
  );
}
