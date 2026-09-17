import { formatStepTiming } from '@/shared/lib/format';

import type { CampaignStep } from '../model/types';

interface StepListProps {
  steps: CampaignStep[];
}

/** The sequence in sending order; the number is the step's place in it. */
export function StepList({ steps }: StepListProps) {
  const ordered = [...steps].sort((a, b) => a.position - b.position);
  return (
    <ol className="step-list">
      {ordered.map((step, index) => (
        <li key={step.id} className="step-item">
          <span className="step-number">{index + 1}</span>
          <div>
            <p className="step-subject">{step.subject}</p>
            <p className="step-delay">{formatStepTiming(index, step.delay_seconds)}</p>
            <details>
              <summary>Read the email</summary>
              <pre className="step-body">{step.body}</pre>
            </details>
          </div>
        </li>
      ))}
    </ol>
  );
}
