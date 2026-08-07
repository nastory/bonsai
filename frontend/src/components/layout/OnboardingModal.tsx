import { useState } from 'react';
import { useAppData } from '../../context/AppDataContext';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Toggle } from '../ui/Toggle';
import { SegmentedControl } from '../ui/SegmentedControl';
import { cn } from '../ui/cn';
import logo from '../../assets/logo.svg';

type Step = 'name' | 'model' | 'tavily' | 'done';
const PROGRESS_STEPS: Step[] = ['name', 'model', 'tavily', 'done'];

/**
 * Shown once, on first load (gated in AppShell.tsx on !user.onboardingCompleted).
 * Non-dismissible by design (no backdrop-click-close, no X) - the only way
 * through is to finish it, same "forced choice" precedent as
 * ModuleCompletionModal. Each step batches its fields into one
 * updateUserSettings() call on Continue, rather than Settings.tsx's
 * per-field autosave-on-blur - there's nothing to individually confirm mid-form here.
 */
export function OnboardingModal() {
  const { user, updateUserSettings } = useAppData();
  const [step, setStep] = useState<Step>('name');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  const [nameDraft, setNameDraft] = useState(user.name);

  const [tier, setTier] = useState<'hosted' | 'byom'>(user.modelProvider.tier);
  const [hostedProvider, setHostedProvider] = useState<'anthropic' | 'openai'>(
    user.modelProvider.hostedProvider ?? 'anthropic',
  );
  const [hostedModel, setHostedModel] = useState(user.modelProvider.hostedModel ?? '');
  const [apiKey, setApiKey] = useState('');
  const [byomEndpoint, setByomEndpoint] = useState(user.modelProvider.byomEndpoint ?? '');
  const [byomModel, setByomModel] = useState(user.modelProvider.byomModel ?? '');
  const [embeddingModel, setEmbeddingModel] = useState(user.embeddingModel ?? '');
  const [embeddingUseCompletionCredentials, setEmbeddingUseCompletionCredentials] = useState(
    user.embeddingUseCompletionCredentials,
  );
  const [embeddingApiKey, setEmbeddingApiKey] = useState('');

  const [tavilyKey, setTavilyKey] = useState('');

  const handleNameContinue = () => {
    const trimmed = nameDraft.trim();
    if (!trimmed) return;
    setSaving(true);
    setError(false);
    updateUserSettings({ name: trimmed })
      .then(() => setStep('model'))
      .catch(() => setError(true))
      .finally(() => setSaving(false));
  };

  const handleModelContinue = () => {
    setSaving(true);
    setError(false);
    updateUserSettings({
      modelProvider: {
        tier,
        ...(tier === 'hosted'
          ? {
              hostedProvider,
              ...(hostedModel.trim() && { hostedModel: hostedModel.trim() }),
              ...(apiKey.trim() && { apiKey: apiKey.trim() }),
            }
          : {
              ...(byomEndpoint.trim() && { byomEndpoint: byomEndpoint.trim() }),
              ...(byomModel.trim() && { byomModel: byomModel.trim() }),
            }),
      },
      ...(embeddingModel.trim() && { embeddingModel: embeddingModel.trim() }),
      embeddingUseCompletionCredentials,
      ...(tier === 'hosted' &&
        !embeddingUseCompletionCredentials &&
        embeddingApiKey.trim() && { embeddingApiKey: embeddingApiKey.trim() }),
    })
      .then(() => setStep('tavily'))
      .catch(() => setError(true))
      .finally(() => setSaving(false));
  };

  const handleModelSkip = () => {
    setError(false);
    setStep('tavily');
  };

  const handleTavilyContinue = () => {
    const trimmed = tavilyKey.trim();
    if (!trimmed) {
      setStep('done');
      return;
    }
    setSaving(true);
    setError(false);
    updateUserSettings({ tavilyApiKey: trimmed })
      .then(() => setStep('done'))
      .catch(() => setError(true))
      .finally(() => setSaving(false));
  };

  const handleTavilySkip = () => {
    setError(false);
    setStep('done');
  };

  const handleFinish = () => {
    setSaving(true);
    setError(false);
    updateUserSettings({ onboardingCompleted: true })
      .catch(() => setError(true))
      .finally(() => setSaving(false));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <Card className="w-full max-w-md">
        {step === 'name' && (
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bonsai-cream">
                <img src={logo} alt="Bonsai" className="h-4 w-4" />
              </span>
              <div>
                <p className="font-semibold text-bonsai-text">Welcome to Bonsai!</p>
                <p className="text-sm text-bonsai-text-muted">What should we call you?</p>
              </div>
            </div>
            <Input
              className="mt-4"
              autoFocus
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNameContinue()}
              placeholder="Your name"
            />
            <Button className="mt-4 w-full" onClick={handleNameContinue} disabled={!nameDraft.trim() || saving}>
              Continue
            </Button>
          </div>
        )}

        {step === 'model' && (
          <div>
            <p className="font-semibold text-bonsai-text">Set up a model</p>
            <p className="mt-1 text-sm text-bonsai-text-muted">
              Bonsai routes model calls through LiteLLM — use a hosted provider or your own local model. You can
              change this anytime.
            </p>

            <div className="mt-4">
              <SegmentedControl
                value={tier}
                options={[
                  { value: 'hosted', label: 'Hosted' },
                  { value: 'byom', label: 'Bring Your Own Model' },
                ]}
                onChange={setTier}
              />
            </div>

            {tier === 'hosted' ? (
              <div className="mt-3 space-y-3">
                <SegmentedControl
                  value={hostedProvider}
                  options={[
                    { value: 'anthropic', label: 'Anthropic' },
                    { value: 'openai', label: 'OpenAI' },
                  ]}
                  onChange={setHostedProvider}
                />
                <Input
                  placeholder={
                    hostedProvider === 'openai'
                      ? 'Model (e.g. gpt-4o). Leave blank for a sensible default'
                      : 'Model (e.g. claude-3-5-sonnet-20241022). Leave blank for a sensible default'
                  }
                  value={hostedModel}
                  onChange={(e) => setHostedModel(e.target.value)}
                />
                <Input
                  type="password"
                  placeholder="API key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>
            ) : (
              <div className="mt-3 space-y-3">
                <Input
                  placeholder="Local model endpoint (e.g. http://localhost:11434)"
                  value={byomEndpoint}
                  onChange={(e) => setByomEndpoint(e.target.value)}
                />
                <Input
                  placeholder="Model name at that endpoint (e.g. llama3)"
                  value={byomModel}
                  onChange={(e) => setByomModel(e.target.value)}
                />
              </div>
            )}

            <div className="mt-4 border-t border-bonsai-border pt-3">
              <p className="text-sm font-medium text-bonsai-text">Embedding model</p>
              <p className="mt-0.5 text-xs text-bonsai-text-muted">
                Powers retrieval for document- and web-grounded course generation.
              </p>
              <Input
                className="mt-2"
                placeholder={
                  tier === 'hosted' ? 'Embedding model (e.g. text-embedding-3-small)' : 'Embedding model name (e.g. nomic-embed-text)'
                }
                value={embeddingModel}
                onChange={(e) => setEmbeddingModel(e.target.value)}
              />
              {tier === 'hosted' && (
                <>
                  <div className="mt-3 flex items-center justify-between">
                    <p className="text-sm text-bonsai-text">Use the same API key for the embedding model</p>
                    <Toggle checked={embeddingUseCompletionCredentials} onChange={setEmbeddingUseCompletionCredentials} />
                  </div>
                  {!embeddingUseCompletionCredentials && (
                    <Input
                      className="mt-3"
                      type="password"
                      placeholder="Embedding API key"
                      value={embeddingApiKey}
                      onChange={(e) => setEmbeddingApiKey(e.target.value)}
                    />
                  )}
                </>
              )}
            </div>

            <div className="mt-5 flex gap-2">
              <Button className="flex-1" onClick={handleModelContinue} disabled={saving}>
                Continue
              </Button>
              <Button className="flex-1" variant="secondary" onClick={handleModelSkip} disabled={saving}>
                Skip for now
              </Button>
            </div>
            <p className="mt-2 text-xs text-bonsai-text-muted">You can set this later in Settings.</p>
          </div>
        )}

        {step === 'tavily' && (
          <div>
            <p className="font-semibold text-bonsai-text">Add a Tavily key</p>
            <p className="mt-1 text-sm text-bonsai-text-muted">
              Powers the web search Bonsai uses to ground and cite course content. Separate from whichever model
              provider you just set up.
            </p>
            <Input
              className="mt-4"
              type="password"
              placeholder="Tavily API key"
              value={tavilyKey}
              onChange={(e) => setTavilyKey(e.target.value)}
            />
            <div className="mt-5 flex gap-2">
              <Button className="flex-1" onClick={handleTavilyContinue} disabled={saving}>
                Continue
              </Button>
              <Button className="flex-1" variant="secondary" onClick={handleTavilySkip} disabled={saving}>
                Skip for now
              </Button>
            </div>
            <p className="mt-2 text-xs text-bonsai-text-muted">You can set this later in Settings.</p>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-bonsai-cream">
              <img src={logo} alt="Bonsai" className="h-6 w-6" />
            </span>
            <p className="mt-3 text-lg font-semibold text-bonsai-text">You're ready to start learning!</p>
            <Button className="mt-5 w-full" onClick={handleFinish} disabled={saving}>
              Start learning
            </Button>
          </div>
        )}

        {error && <p className="mt-3 text-xs text-red-600">Something went wrong saving that — try again.</p>}

        {step !== 'done' && (
          <div className="mt-4 flex justify-center gap-2">
            {PROGRESS_STEPS.slice(0, 3).map((s) => (
              <span
                key={s}
                className={cn(
                  'h-2 w-2 rounded-full',
                  PROGRESS_STEPS.indexOf(s) <= PROGRESS_STEPS.indexOf(step) ? 'bg-bonsai-green' : 'bg-bonsai-border',
                )}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
