import Link from 'next/link';

import { formatDateTime } from '@/shared/lib/format';
import { StateBadge } from '@/shared/ui/state-badge';

import type { CampaignSummary } from '../model/types';
import { LeadBar } from './lead-bar';

interface CampaignListProps {
  campaigns: CampaignSummary[];
}

export function CampaignList({ campaigns }: CampaignListProps) {
  return (
    <ul className="campaign-list">
      {campaigns.map((campaign) => (
        <li key={campaign.id} className="campaign-card">
          <div className="campaign-card-head">
            <h2>
              <Link href={`/campaigns/${campaign.id}`}>{campaign.name}</Link>
            </h2>
            <StateBadge state={campaign.status} />
          </div>
          <p className="campaign-card-meta">
            {campaign.steps.length} {campaign.steps.length === 1 ? 'step' : 'steps'} · created{' '}
            {formatDateTime(campaign.created_at)}
          </p>
          <LeadBar counts={campaign.lead_counts} />
        </li>
      ))}
    </ul>
  );
}
