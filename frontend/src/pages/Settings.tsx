import { useEffect, useState } from 'react';
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

  // The backend never sends the real API key back, so this draft always
  // starts empty; it exists only to capture a *new* key to save.
  const [apiKeyDraft, setApiKeyDraft] = useState('');
  const [tavilyKeyDraft, setTavilyKeyDraft] = useState('');

  // byomEndpoint/byomModel aren't secret, so it's fine to prefill and re-sync
  // when the fetched settings change, but still save on blur rather than per keystroke.
  const [byomEndpointDraft, setByomEndpointDraft] = useState(modelProvider.byomEndpoint ?? '');
  useEffect(() => {
    setByomEndpointDraft(modelProvider.byomEndpoint ?? '');
  }, [modelProvider.byomEndpoint]);

  const [byomModelDraft, setByomModelDraft] = useState(modelProvider.byomModel ?? '');
  useEffect(() => {
    setByomModelDraft(modelProvider.byomModel ?? '');
  }, [modelProvider.byomModel]);

  const [hostedModelDraft, setHostedModelDraft] = useState(modelProvider.hostedModel ?? '');
  useEffect(() => {
    setHostedModelDraft(modelProvider.hostedModel ?? '');
  }, [modelProvider.hostedModel]);

  const [embeddingModelDraft, setEmbeddingModelDraft] = useState(user.embeddingModel ?? '');
  useEffect(() => {
    setEmbeddingModelDraft(user.embeddingModel ?? '');
  }, [user.embeddingModel]);

  const saveApiKeyIfChanged = () => {
    if (apiKeyDraft.trim()) {
      updateUserSettings({ modelProvider: { apiKey: apiKeyDraft.trim() } });
      setApiKeyDraft('');
    }
  };

  const saveTavilyKeyIfChanged = () => {
    if (tavilyKeyDraft.trim()) {
      updateUserSettings({ tavilyApiKey: tavilyKeyDraft.trim() });
      setTavilyKeyDraft('');
    }
  };

  const saveByomEndpointIfChanged = () => {
    if (byomEndpointDraft !== (modelProvider.byomEndpoint ?? '')) {
      updateUserSettings({ modelProvider: { byomEndpoint: byomEndpointDraft } });
    }
  };

  const saveByomModelIfChanged = () => {
    if (byomModelDraft !== (modelProvider.byomModel ?? '')) {
      updateUserSettings({ modelProvider: { byomModel: byomModelDraft } });
    }
  };

  const saveHostedModelIfChanged = () => {
    if (hostedModelDraft !== (modelProvider.hostedModel ?? '')) {
      updateUserSettings({ modelProvider: { hostedModel: hostedModelDraft } });
    }
  };

  const saveEmbeddingModelIfChanged = () => {
    if (embeddingModelDraft !== (user.embeddingModel ?? '')) {
      updateUserSettings({ embeddingModel: embeddingModelDraft });
    }
  };

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
            onChange={(tier) => updateUserSettings({ modelProvider: { tier } })}
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
              onChange={(hostedProvider) => updateUserSettings({ modelProvider: { hostedProvider } })}
            />
            <Input
              placeholder={
                modelProvider.hostedProvider === 'openai'
                  ? 'Model (e.g. gpt-4o). Leave blank for a sensible default'
                  : 'Model (e.g. claude-3-5-sonnet-20241022). Leave blank for a sensible default'
              }
              value={hostedModelDraft}
              onChange={(e) => setHostedModelDraft(e.target.value)}
              onBlur={saveHostedModelIfChanged}
            />
            <Input
              type="password"
              placeholder={modelProvider.hasApiKey ? 'Enter a new key to replace the current one' : 'API key'}
              value={apiKeyDraft}
              onChange={(e) => setApiKeyDraft(e.target.value)}
              onBlur={saveApiKeyIfChanged}
            />
            <p className="text-xs text-bonsai-text-muted">
              {modelProvider.hasApiKey ? 'A key is configured. ' : 'No key set yet. '}
              Reliable tool-use support on this path means citations and retrieval work as designed.
            </p>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <Input
              placeholder="Local model endpoint (e.g. http://localhost:11434)"
              value={byomEndpointDraft}
              onChange={(e) => setByomEndpointDraft(e.target.value)}
              onBlur={saveByomEndpointIfChanged}
            />
            <Input
              placeholder="Model name at that endpoint (e.g. llama3)"
              value={byomModelDraft}
              onChange={(e) => setByomModelDraft(e.target.value)}
              onBlur={saveByomModelIfChanged}
            />
            <p className="text-xs text-bonsai-text-muted">
              Best-effort: local models vary in tool-use support, so retrieval and citation quality may be
              reduced compared to the hosted path.
            </p>
          </div>
        )}
      </Card>

      <Card className="mt-4">
        <p className="font-semibold text-bonsai-text">Embedding Model</p>
        <p className="mt-1 text-sm text-bonsai-text-muted">
          Used for retrieval ranking and, later, semantic search over your course index. Configurable
          separately from the completion model above, since it doesn't have to come from the same provider.
          Doesn't do anything yet: nothing in Bonsai reads this setting until retrieval is built.
        </p>
        <Input
          className="mt-3"
          placeholder="Embedding model (e.g. text-embedding-3-small, nomic-embed-text)"
          value={embeddingModelDraft}
          onChange={(e) => setEmbeddingModelDraft(e.target.value)}
          onBlur={saveEmbeddingModelIfChanged}
        />
      </Card>

      <Card className="mt-4">
        <p className="font-semibold text-bonsai-text">Retrieval (Tavily)</p>
        <p className="mt-1 text-sm text-bonsai-text-muted">
          Powers the web search used to ground and cite course content. This is a separate key from whichever
          LLM provider you use above, needed regardless of hosted vs. Bring Your Own Model. Doesn't do
          anything yet: the retrieval agent isn't built.
        </p>
        <Input
          className="mt-3"
          type="password"
          placeholder={user.hasTavilyApiKey ? 'Enter a new key to replace the current one' : 'Tavily API key'}
          value={tavilyKeyDraft}
          onChange={(e) => setTavilyKeyDraft(e.target.value)}
          onBlur={saveTavilyKeyIfChanged}
        />
        <p className="mt-2 text-xs text-bonsai-text-muted">
          {user.hasTavilyApiKey ? 'A key is configured.' : 'No key set yet.'}
        </p>
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
