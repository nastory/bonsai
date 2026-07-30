import { InfoPage } from '../components/layout/InfoPage';

export function Terms() {
  return (
    <InfoPage title="Terms of Service">
      <p className="italic text-bonsai-text-muted">
        Draft. Bonsai is an early, self-hosted hobby project, not a reviewed legal document.
      </p>
      <p>
        Bonsai is provided as-is, under the Apache 2.0 license, with no warranty of any kind. You run it on
        your own machine and are responsible for any model provider accounts, API keys, and costs you
        configure it to use, and for complying with those providers' own terms of service.
      </p>
      <p>
        Bonsai carries no accreditation of any kind. Completing a course does not constitute a degree,
        certification, or professional qualification. It's self-directed learning, nothing more.
      </p>
      <p>
        Bonsai makes no guarantee of the correctness of generated or synthesized material. Where available,
        refer to the original cited sources for the most accurate information.
      </p>
      <p>
        If you configure Bonsai to use your own local ("Bring Your Own Model") model instead of a hosted
        provider, you are responsible for that model's behavior and outputs. Bonsai cannot guarantee it
        will follow the content restrictions described in the User Policy.
      </p>
    </InfoPage>
  );
}
