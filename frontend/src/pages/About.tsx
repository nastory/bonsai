import { Card } from '../components/ui/Card';
import logo from '../assets/logo.svg';

export function About() {
  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-center px-8 py-10">
      <div className="flex flex-col items-center text-center">
        <div className="relative">
          <div className="absolute right-full top-1/2 mr-3 flex h-16 w-16 -translate-y-1/2 items-center justify-center rounded-xl bg-bonsai-cream">
            <img src={logo} alt="" className="h-9 w-9" />
          </div>
          <h1 className="text-4xl font-semibold text-bonsai-text">Bonsai Learning</h1>
        </div>
        <p className="mt-2 text-sm text-bonsai-text-muted">Self-directed learning, grown at your own pace.</p>
      </div>

      <Card className="mt-8 space-y-4 text-sm leading-relaxed text-bonsai-text">
        <p>
          Bonsai Learning is an open-source, standalone, locally-hosted application for
          self-directed learning on any subject. Instead of picking from a catalog of pre-built courses, you
          tell Bonsai what you want to learn, and it builds a course outline with you, generating each module
          as you reach it.
        </p>
        <p>
          The project is named for the meditative, self-shaped practice of bonsai cultivation. You build and
          reshape your own curriculum as you go, rather than following a fixed one someone else designed.
        </p>
        <div className="border-t border-bonsai-border pt-4 text-xs text-bonsai-text-muted">
          <p>Version: Phase 2 (development build) · License: Apache 2.0</p>
        </div>
      </Card>
    </div>
  );
}
