import { sentenceCase } from '@/shared/lib/format';

import { leadSegments } from '../lib/lead-counts';

interface LeadBarProps {
  counts: Record<string, number>;
}

/** All leads of a campaign as one bar, split by state in lifecycle order, with the numbers next to it. */
export function LeadBar({ counts }: LeadBarProps) {
  const segments = leadSegments(counts);
  if (segments.length === 0) {
    return <p className="lead-bar-empty">No leads yet</p>;
  }
  return (
    <div className="lead-bar">
      <div className="lead-bar-track" aria-hidden="true">
        {segments.map((segment) => (
          <span
            key={segment.state}
            className={`lead-bar-segment lead-bar-segment--${segment.state}`}
            style={{ width: `${segment.share}%` }}
          />
        ))}
      </div>
      <ul className="lead-bar-legend">
        {segments.map((segment) => (
          <li key={segment.state}>
            <span className={`legend-dot lead-bar-segment--${segment.state}`} aria-hidden="true" />
            {sentenceCase(segment.state)} <b>{segment.count}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}
