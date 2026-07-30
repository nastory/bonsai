import { InfoPage } from '../components/layout/InfoPage';

export function UserPolicy() {
  return (
    <InfoPage title="User Policy">
      <p>
        Bonsai must never teach, reference, recommend, or encourage anything illegal: drug manufacturing,
        weapons, self-harm, hate content, none of it.
      </p>
      <p>
        Medical and legal topics carry disclaimers making clear that Bonsai doesn't license or qualify you
        to practice or advise in those fields.
      </p>
      <p>
        Esoteric topics, conspiracy theories, alternative medicine, and the like, are clearly flagged when
        they contradict scientific consensus or the official record.
      </p>
      <p>Bonsai stays neutral on religion and politics.</p>
      <p>
        Bonsai carries no accreditation of any kind and makes no guarantee that its generated or synthesized
        material is correct.
      </p>
      <p>
        Enforcement relies on the safety behavior built into hosted model providers, plus a lightweight
        automated check at course-creation time. If you configure your own local model ("Bring Your Own
        Model"), Bonsai can't guarantee it will follow this policy. Responsibility for that model's outputs
        shifts to you.
      </p>
    </InfoPage>
  );
}
