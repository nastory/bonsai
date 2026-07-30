import { useAppData } from '../context/AppDataContext';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Toggle } from '../components/ui/Toggle';
import { cn } from '../components/ui/cn';

function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-bonsai-border bg-white p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            value === option.value
              ? 'bg-bonsai-green text-white'
              : 'text-bonsai-text-muted hover:text-bonsai-text',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Settings() {
  const { user, updateUserSettings } = useAppData();
  const { modelProvider } = user;

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Settings</h1>

      <Card className="mt-6">
        <p className="font-semibold text-bonsai-text">Model Provider</p>
        <p className="mt-1 text-sm text-bonsai-text-muted">
          Bonsai routes model calls through LiteLLM, so you can use a hosted provider or your own local model.
        </p>

        <div className="mt-4">
          <SegmentedControl
            value={modelProvider.tier}
            options={[
              { value: 'hosted', label: 'Hosted' },
              { value: 'byom', label: 'Bring Your Own Model' },
            ]}
            onChange={(tier) => updateUserSettings({ modelProvider: { ...modelProvider, tier } })}
          />
        </div>

        {modelProvider.tier === 'hosted' ? (
          <div className="mt-4 space-y-3">
            <SegmentedControl
              value={modelProvider.hostedProvider ?? 'anthropic'}
              options={[
                { value: 'anthropic', label: 'Anthropic' },
                { value: 'openai', label: 'OpenAI' },
              ]}
              onChange={(hostedProvider) =>
                updateUserSettings({ modelProvider: { ...modelProvider, hostedProvider } })
              }
            />
            <Input
              type="password"
              placeholder="API key"
              value={modelProvider.apiKey ?? ''}
              onChange={(e) =>
                updateUserSettings({ modelProvider: { ...modelProvider, apiKey: e.target.value } })
              }
            />
            <p className="text-xs text-bonsai-text-muted">
              Reliable tool-use support on this path means citations and retrieval work as designed.
            </p>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <Input
              placeholder="Local model endpoint (e.g. http://localhost:11434)"
              value={modelProvider.byomEndpoint ?? ''}
              onChange={(e) =>
                updateUserSettings({ modelProvider: { ...modelProvider, byomEndpoint: e.target.value } })
              }
            />
            <p className="text-xs text-bonsai-text-muted">
              Best-effort: local models vary in tool-use support, so retrieval and citation quality may be
              reduced compared to the hosted path.
            </p>
          </div>
        )}
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-bonsai-text">Course thumbnails</p>
            <p className="mt-1 text-sm text-bonsai-text-muted">
              Generate an image for each course. Turn off to save tokens.
            </p>
          </div>
          <Toggle
            checked={user.thumbnailGenerationEnabled}
            onChange={(thumbnailGenerationEnabled) => updateUserSettings({ thumbnailGenerationEnabled })}
          />
        </div>
      </Card>

      <Card className="mt-4">
        <p className="font-semibold text-bonsai-text">Feedback style</p>
        <p className="mt-1 text-sm text-bonsai-text-muted">
          How Bonsai responds to your exercises and check-ins.
        </p>
        <div className="mt-3">
          <SegmentedControl
            value={user.feedbackTone}
            options={[
              { value: 'encouraging', label: 'Encouraging' },
              { value: 'straightforward', label: 'Straightforward' },
            ]}
            onChange={(feedbackTone) => updateUserSettings({ feedbackTone })}
          />
        </div>
      </Card>
    </div>
  );
}
