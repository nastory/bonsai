import { InfoPage } from '../components/layout/InfoPage';

export function Privacy() {
  return (
    <InfoPage title="Privacy Policy">
      <p>
        Bonsai runs locally on your own machine. Your course outlines, module content, progress, and
        settings are stored locally, split between a local database for metadata/progress and local files
        for generated content, and are never sent to Bonsai's developers, because there's no server on
        the other end to send them to.
      </p>
      <p>
        Bonsai does not collect analytics or telemetry of any kind.
      </p>
      <p>
        If you configure a hosted model provider (e.g., Anthropic, OpenAI) in Settings, the inputs needed to
        generate your courses, your stated topics, interview answers, and progress context, are sent to
        that provider using your own API key, subject to that provider's own privacy policy. If you use a
        local ("Bring Your Own Model") model instead, nothing leaves your machine.
      </p>
      <p>
        API keys and other credentials are stored locally and are never included when you export your data.
      </p>
    </InfoPage>
  );
}
