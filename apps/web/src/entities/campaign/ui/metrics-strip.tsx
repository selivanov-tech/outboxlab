import { formatPercent } from '@/shared/lib/format';

import type { CampaignMetrics } from '../model/types';

interface MetricsStripProps {
  metrics: CampaignMetrics;
}

export function MetricsStrip({ metrics }: MetricsStripProps) {
  const figures: Array<[string, string, string]> = [
    ['Leads', String(metrics.leads), `${metrics.in_progress} still in the sequence`],
    ['Contacted', String(metrics.contacted), `${metrics.emails_sent} emails sent`],
    ['Replied', String(metrics.replied), `${formatPercent(metrics.reply_rate)} of contacted`],
    ['Bounced', String(metrics.bounced), `${formatPercent(metrics.bounce_rate)} of contacted`],
    ['Finished', String(metrics.completed), 'got every step'],
  ];
  return (
    <dl className="metrics-strip">
      {figures.map(([label, value, note]) => (
        <div key={label} className="metric">
          <dt>{label}</dt>
          <dd>
            <span className="metric-value">{value}</span>
            <span className="metric-note">{note}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}
