import { InfoPage } from '../components/layout/InfoPage';

export function UserPolicy() {
  return (
    <InfoPage title="User Policy">
      <p>
        By using Bonsai, you agree not to use it, through your course topics, interview answers, uploaded
        documents, or any other input, to generate or extract content that teaches, references,
        recommends, or encourages anything illegal: drug manufacturing, weapons, self-harm, hate content,
        or similar. You also agree not to attempt to circumvent Bonsai's built-in content restrictions.
      </p>
      <p>
        You're responsible for everything you submit to Bonsai: the topics you request, the answers you
        give during course creation, and any documents you upload. Only upload material you have the right
        to use.
      </p>
      <p>
        You're responsible for everything Bonsai generates in response, readings, quizzes, feedback, and
        anything else, and for how you use it. Review generated content critically, especially anything you
        plan to rely on, share, or act on outside the app.
      </p>
      <p>
        Bonsai makes no guarantee that generated or synthesized material is accurate, complete, or current.
        A citation shown alongside generated content means a source was retrieved and referenced, not that
        the content has been verified as correct. Where it matters, check the original source or another
        authoritative reference yourself.
      </p>
      <p>
        Bonsai carries no accreditation of any kind. Completing a course, module, activity, or capstone
        project through Bonsai doesn't certify, license, or qualify you to practice, perform, or claim
        expertise in anything. It's self-directed learning, not a substitute for formal education,
        professional training, licensure, or certification, and medical or legal topics in particular
        should never be treated as professional advice.
      </p>
      <p>
        Enforcement of the content restrictions above relies on your configured model provider's own safety
        behavior, plus a lightweight automated check at course-creation time, neither of which is
        foolproof. If you configure Bonsai to use your own local model ("Bring Your Own Model") instead of
        a hosted provider, responsibility for that model's behavior and outputs is yours; Bonsai can't
        guarantee it will follow this policy.
      </p>
    </InfoPage>
  );
}
