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
        You may not use Bonsai for any illegal purpose, or to violate any law or regulation that applies to
        you. This covers any use of the app, not just the content it generates: planning, facilitating, or
        carrying out illegal activity through Bonsai is prohibited, whether or not the content involved is
        itself restricted (see the User Policy for the rules governing generated content specifically).
      </p>
      <p>
        Bonsai, and the individuals who create and contribute to it, are not liable for any damages,
        losses, or other consequences, direct, indirect, incidental, or otherwise, arising from your use of
        the app. This includes the accuracy of anything it generates or synthesizes, any decision or action
        you take based on it, costs incurred through a model provider you configure, and the behavior of
        any local model you bring yourself. To the fullest extent the law allows, you use Bonsai entirely
        at your own risk.
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
