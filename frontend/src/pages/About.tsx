import { InfoPage } from '../components/layout/InfoPage';

export function About() {
  return (
    <InfoPage title="About Bonsai">
      <p>
        Bonsai is an open-source, standalone, locally-hosted application for self-directed learning on any
        subject. Instead of picking from a catalog of pre-built courses, you tell Bonsai what you want to
        learn, and it builds a course outline with you, generating each module as you reach it.
      </p>
      <p>
        The project is named for the meditative, self-shaped practice of bonsai cultivation. You build and
        reshape your own curriculum as you go, rather than following a fixed one someone else designed.
      </p>
      <p className="text-bonsai-text-muted">
        Version: Phase 0 (development build) · License: Apache 2.0 · Created by Nigel Story
      </p>
    </InfoPage>
  );
}
