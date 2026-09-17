import { sentenceCase } from '@/shared/lib/format';

interface StateBadgeProps {
  state: string;
}

/** A lead state, campaign status or send-job status as a small tag; the colour comes from the value. */
export function StateBadge({ state }: StateBadgeProps) {
  return <span className={`badge badge--${state}`}>{sentenceCase(state)}</span>;
}
