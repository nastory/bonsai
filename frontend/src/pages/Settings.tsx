import { useEffect, useState } from 'react';
import { useAppData } from '../context/AppDataContext';
import type { UserSettingsPatch } from '../types/course';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { KeyInput, type SaveStatus } from '../components/ui/KeyInput';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Toggle } from '../components/ui/Toggle';
import { cn } from '../components/ui/cn';

export function Settings() {
  const { user, updateUserSettings } = useAppData();
  const { modelProvider } = user;

  // Fire-and-forget updates (toggles, segmented controls, model name
  // fields): AppDataContext already logs failures, and these fields show
  // their own current value, so there's nothing further to confirm.
  const save = (patch: UserSettingsPatch) => {
    updateUserSettings(patch).catch(() => {});
  };

  // The backend never sends the real API key back, so this draft always
  // starts empty; it exists only to capture a *new* key to save. Since
  // there's no persisted value to show afterward, these two fields need
  // their own save-status feedback so it's clear whether it actually saved.
  const [apiKeyDraft, setApiKeyDraft] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState<SaveStatus>('idle');
  const [tavilyKeyDraft, setTavilyKeyDraft] = useState('');
  const [tavilyKeyStatus, setTavilyKeyStatus] = useState<SaveStatus>('idle');
  const [embeddingApiKeyDraft, setEmbeddingApiKeyDraft] = useState('');
  const [embeddingApiKeyStatus, setEmbeddingApiKeyStatus] = useState<SaveStatus>('idle');
  const [imageGenerationApiKeyDraft, setImageGenerationApiKeyDraft] = useState('');
  const [imageGenerationApiKeyStatus, setImageGenerationApiKeyStatus] = useState<SaveStatus>('idle');

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

  const [imageGenerationModelDraft, setImageGenerationModelDraft] = useState(user.imageGenerationModel ?? '');
  useEffect(() => {
    setImageGenerationModelDraft(user.imageGenerationModel ?? '');
  }, [user.imageGenerationModel]);

  const [weeklyGoalDraft, setWeeklyGoalDraft] = useState(
    user.weeklyGoalActivities != null ? String(user.weeklyGoalActivities) : '',
  );
  useEffect(() => {
    setWeeklyGoalDraft(user.weeklyGoalActivities != null ? String(user.weeklyGoalActivities) : '');
  }, [user.weeklyGoalActivities]);

  const saveApiKeyIfChanged = () => {
    if (!apiKeyDraft.trim()) return;
    updateUserSettings({ modelProvider: { apiKey: apiKeyDraft.trim() } })
      .then(() => {
        setApiKeyDraft('');
        setApiKeyStatus('saved');
      })
      .catch(() => setApiKeyStatus('error'));
  };

  const saveTavilyKeyIfChanged = () => {
    if (!tavilyKeyDraft.trim()) return;
    updateUserSettings({ tavilyApiKey: tavilyKeyDraft.trim() })
      .then(() => {
        setTavilyKeyDraft('');
        setTavilyKeyStatus('saved');
      })
      .catch(() => setTavilyKeyStatus('error'));
  };

  const saveEmbeddingApiKeyIfChanged = () => {
    if (!embeddingApiKeyDraft.trim()) return;
    updateUserSettings({ embeddingApiKey: embeddingApiKeyDraft.trim() })
      .then(() => {
        setEmbeddingApiKeyDraft('');
        setEmbeddingApiKeyStatus('saved');
      })
      .catch(() => setEmbeddingApiKeyStatus('error'));
  };

  const saveImageGenerationApiKeyIfChanged = () => {
    if (!imageGenerationApiKeyDraft.trim()) return;
    updateUserSettings({ imageGenerationApiKey: imageGenerationApiKeyDraft.trim() })
      .then(() => {
        setImageGenerationApiKeyDraft('');
        setImageGenerationApiKeyStatus('saved');
      })
      .catch(() => setImageGenerationApiKeyStatus('error'));
  };

  const saveByomEndpointIfChanged = () => {
    if (byomEndpointDraft !== (modelProvider.byomEndpoint ?? '')) {
      save({ modelProvider: { byomEndpoint: byomEndpointDraft } });
    }
  };

  const saveByomModelIfChanged = () => {
    if (byomModelDraft !== (modelProvider.byomModel ?? '')) {
      save({ modelProvider: { byomModel: byomModelDraft } });
    }
  };

  const saveHostedModelIfChanged = () => {
    if (hostedModelDraft !== (modelProvider.hostedModel ?? '')) {
      save({ modelProvider: { hostedModel: hostedModelDraft } });
    }
  };

  const saveEmbeddingModelIfChanged = () => {
    if (embeddingModelDraft !== (user.embeddingModel ?? '')) {
      save({ embeddingModel: embeddingModelDraft });
    }
  };

  const saveImageGenerationModelIfChanged = () => {
    if (imageGenerationModelDraft !== (user.imageGenerationModel ?? '')) {
      save({ imageGenerationModel: imageGenerationModelDraft });
    }
  };

  const saveWeeklyGoalIfChanged = () => {
    const parsed = parseInt(weeklyGoalDraft, 10);
    const next = Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    if (next !== user.weeklyGoalActivities) {
      save({ weeklyGoalActivities: next });
      setWeeklyGoalDraft(next != null ? String(next) : '');
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
            onChange={(tier) => save({ modelProvider: { tier } })}
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
              onChange={(hostedProvider) => save({ modelProvider: { hostedProvider } })}
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
            <KeyInput
              status={apiKeyStatus}
              type="password"
              placeholder={modelProvider.hasApiKey ? 'Enter a new key to replace the current one' : 'API key'}
              value={apiKeyDraft}
              onChange={(e) => {
                setApiKeyDraft(e.target.value);
                setApiKeyStatus('idle');
              }}
              onBlur={saveApiKeyIfChanged}
            />
            <p
              className={cn(
                'text-xs',
                apiKeyStatus === 'saved'
                  ? 'text-green-600'
                  : apiKeyStatus === 'error'
                    ? 'text-red-600'
                    : 'text-bonsai-text-muted',
              )}
            >
              {apiKeyStatus === 'saved'
                ? 'Saved. '
                : apiKeyStatus === 'error'
                  ? 'Failed to save — try again. '
                  : modelProvider.hasApiKey
                    ? 'A key is configured. '
                    : 'No key set yet. '}
              The most reliable path for generation quality and well-formed output.
            </p>

            <div className="mt-2 border-t border-bonsai-border pt-3">
              <p className="text-sm font-medium text-bonsai-text">Embedding model</p>
              <p className="mt-0.5 text-xs text-bonsai-text-muted">
                Powers retrieval for both document- and web-grounded course generation. Without one set,
                grounding falls back to raw source text instead of targeted retrieval, which may produce
                lower-quality material.
              </p>
              <Input
                className="mt-2"
                placeholder="Embedding model (e.g. text-embedding-3-small)"
                value={embeddingModelDraft}
                onChange={(e) => setEmbeddingModelDraft(e.target.value)}
                onBlur={saveEmbeddingModelIfChanged}
              />
              <div className="mt-3 flex items-center justify-between">
                <p className="text-sm text-bonsai-text">Use the same API key for the embedding model</p>
                <Toggle
                  checked={user.embeddingUseCompletionCredentials}
                  onChange={(embeddingUseCompletionCredentials) => save({ embeddingUseCompletionCredentials })}
                />
              </div>
              {!user.embeddingUseCompletionCredentials && (
                <>
                  <KeyInput
                    status={embeddingApiKeyStatus}
                    className="mt-3"
                    type="password"
                    placeholder={
                      user.hasEmbeddingApiKey ? 'Enter a new key to replace the current one' : 'Embedding API key'
                    }
                    value={embeddingApiKeyDraft}
                    onChange={(e) => {
                      setEmbeddingApiKeyDraft(e.target.value);
                      setEmbeddingApiKeyStatus('idle');
                    }}
                    onBlur={saveEmbeddingApiKeyIfChanged}
                  />
                  <p
                    className={cn(
                      'mt-2 text-xs',
                      embeddingApiKeyStatus === 'saved'
                        ? 'text-green-600'
                        : embeddingApiKeyStatus === 'error'
                          ? 'text-red-600'
                          : 'text-bonsai-text-muted',
                    )}
                  >
                    {embeddingApiKeyStatus === 'saved'
                      ? 'Saved.'
                      : embeddingApiKeyStatus === 'error'
                        ? 'Failed to save — try again.'
                        : user.hasEmbeddingApiKey
                          ? 'A key is configured.'
                          : 'No key set yet.'}
                  </p>
                </>
              )}
            </div>

            <div className="mt-2 border-t border-bonsai-border pt-3">
              <p className="text-sm font-medium text-bonsai-text">Image generation model</p>
              <p className="mt-0.5 text-xs text-bonsai-text-muted">
                Powers real course thumbnail images (see the "Course thumbnails" toggle below). Only
                OpenAI and Azure are supported for image generation today.
              </p>
              <Input
                className="mt-2"
                placeholder="Image generation model (e.g. dall-e-3)"
                value={imageGenerationModelDraft}
                onChange={(e) => setImageGenerationModelDraft(e.target.value)}
                onBlur={saveImageGenerationModelIfChanged}
              />
              <div className="mt-3 flex items-center justify-between">
                <p className="text-sm text-bonsai-text">Use the same API key for the image generation model</p>
                <Toggle
                  checked={user.imageGenerationUseCompletionCredentials}
                  onChange={(imageGenerationUseCompletionCredentials) =>
                    save({ imageGenerationUseCompletionCredentials })
                  }
                />
              </div>
              {!user.imageGenerationUseCompletionCredentials && (
                <>
                  <KeyInput
                    status={imageGenerationApiKeyStatus}
                    className="mt-3"
                    type="password"
                    placeholder={
                      user.hasImageGenerationApiKey
                        ? 'Enter a new key to replace the current one'
                        : 'Image generation API key'
                    }
                    value={imageGenerationApiKeyDraft}
                    onChange={(e) => {
                      setImageGenerationApiKeyDraft(e.target.value);
                      setImageGenerationApiKeyStatus('idle');
                    }}
                    onBlur={saveImageGenerationApiKeyIfChanged}
                  />
                  <p
                    className={cn(
                      'mt-2 text-xs',
                      imageGenerationApiKeyStatus === 'saved'
                        ? 'text-green-600'
                        : imageGenerationApiKeyStatus === 'error'
                          ? 'text-red-600'
                          : 'text-bonsai-text-muted',
                    )}
                  >
                    {imageGenerationApiKeyStatus === 'saved'
                      ? 'Saved.'
                      : imageGenerationApiKeyStatus === 'error'
                        ? 'Failed to save — try again.'
                        : user.hasImageGenerationApiKey
                          ? 'A key is configured.'
                          : 'No key set yet.'}
                  </p>
                </>
              )}
            </div>
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
              Best-effort: local models vary in instruction-following and output reliability compared to the
              hosted path. Citations are attached automatically from retrieved material either way, so
              citation accuracy doesn't depend on the model.
            </p>

            <div className="mt-2 border-t border-bonsai-border pt-3">
              <p className="text-sm font-medium text-bonsai-text">Embedding model</p>
              <p className="mt-0.5 text-xs text-bonsai-text-muted">
                Powers retrieval for both document- and web-grounded course generation. Served from the same
                local endpoint above. Without one set, grounding falls back to raw source text instead of
                targeted retrieval, which may produce lower-quality material.
              </p>
              <Input
                className="mt-2"
                placeholder="Embedding model name (e.g. nomic-embed-text)"
                value={embeddingModelDraft}
                onChange={(e) => setEmbeddingModelDraft(e.target.value)}
                onBlur={saveEmbeddingModelIfChanged}
              />
            </div>
          </div>
        )}
      </Card>

      <Card className="mt-4">
        <p className="font-semibold text-bonsai-text">Retrieval (Tavily)</p>
        <p className="mt-1 text-sm text-bonsai-text-muted">
          Powers the web search used to ground and cite course content. This is a separate key from whichever
          LLM provider you use above, needed regardless of hosted vs. Bring Your Own Model.
        </p>
        <KeyInput
          status={tavilyKeyStatus}
          className="mt-3"
          type="password"
          placeholder={user.hasTavilyApiKey ? 'Enter a new key to replace the current one' : 'Tavily API key'}
          value={tavilyKeyDraft}
          onChange={(e) => {
            setTavilyKeyDraft(e.target.value);
            setTavilyKeyStatus('idle');
          }}
          onBlur={saveTavilyKeyIfChanged}
        />
        <p
          className={cn(
            'mt-2 text-xs',
            tavilyKeyStatus === 'saved'
              ? 'text-green-600'
              : tavilyKeyStatus === 'error'
                ? 'text-red-600'
                : 'text-bonsai-text-muted',
          )}
        >
          {tavilyKeyStatus === 'saved'
            ? 'Saved.'
            : tavilyKeyStatus === 'error'
              ? 'Failed to save — try again.'
              : user.hasTavilyApiKey
                ? 'A key is configured.'
                : 'No key set yet.'}
        </p>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-bonsai-text">Deep search</p>
            <p className="mt-0.5 text-xs text-bonsai-text-muted">
              Slower, more thorough searches when generating module content.
            </p>
          </div>
          <Toggle
            checked={user.deepSearchEnabled}
            onChange={(deepSearchEnabled) => save({ deepSearchEnabled })}
          />
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-bonsai-text">In-course visual aids</p>
            <p className="mt-0.5 text-xs text-bonsai-text-muted">
              Illustrate reading activities with a relevant image, when one is available. Needs a
              Tavily key above to do anything.
            </p>
          </div>
          <Toggle
            checked={user.visualAidsEnabled}
            onChange={(visualAidsEnabled) => save({ visualAidsEnabled })}
          />
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-bonsai-text">Video embedding</p>
            <p className="mt-0.5 text-xs text-bonsai-text-muted">
              Try to include one relevant YouTube video per module, when a good match is found. Needs
              a Tavily key above to do anything.
            </p>
          </div>
          <Toggle
            checked={user.videoEmbeddingEnabled}
            onChange={(videoEmbeddingEnabled) => save({ videoEmbeddingEnabled })}
          />
        </div>
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-bonsai-text">Course thumbnails</p>
            <p className="mt-1 text-sm text-bonsai-text-muted">
              Generate a real image for each course. Needs an image generation model configured above to
              do anything — otherwise courses keep their default gradient thumbnail.
            </p>
          </div>
          <Toggle
            checked={user.thumbnailGenerationEnabled}
            onChange={(thumbnailGenerationEnabled) => save({ thumbnailGenerationEnabled })}
          />
        </div>
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-bonsai-text">Learning Objectives</p>
            <p className="mt-1 text-sm text-bonsai-text-muted">
              Set a personal goal for how many activities to complete each week. Missing it carries no
              penalty — it's just shown as progress on your Today dashboard.
            </p>
          </div>
          <Toggle
            checked={user.weeklyGoalActivities != null}
            onChange={(enabled) => save({ weeklyGoalActivities: enabled ? 5 : null })}
          />
        </div>
        {user.weeklyGoalActivities != null && (
          <div className="mt-3 flex items-center gap-2">
            <Input
              type="number"
              min={1}
              className="w-24"
              value={weeklyGoalDraft}
              onChange={(e) => setWeeklyGoalDraft(e.target.value)}
              onBlur={saveWeeklyGoalIfChanged}
            />
            <span className="text-sm text-bonsai-text-muted">activities per week</span>
          </div>
        )}
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
            onChange={(feedbackTone) => save({ feedbackTone })}
          />
        </div>
      </Card>
    </div>
  );
}
