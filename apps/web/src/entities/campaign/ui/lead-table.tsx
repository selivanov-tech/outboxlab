import { formatDateTime } from '@/shared/lib/format';
import { StateBadge } from '@/shared/ui/state-badge';

import { buildLeadTrack } from '../lib/lead-track';
import type { CampaignStep, Lead } from '../model/types';
import { LeadTrack } from './lead-track';

interface LeadTableProps {
  steps: CampaignStep[];
  leads: Lead[];
}

export function LeadTable({ steps, leads }: LeadTableProps) {
  return (
    <div className="table-scroll">
      <table className="lead-table">
        <thead>
          <tr>
            <th scope="col">Lead</th>
            <th scope="col">State</th>
            <th scope="col">Route through the sequence</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.id}>
              <th scope="row">
                <span className="lead-email">{lead.email}</span>
                <span className="lead-updated">Changed {formatDateTime(lead.updated_at)}</span>
              </th>
              <td>
                <StateBadge state={lead.state} />
              </td>
              <td>
                <LeadTrack track={buildLeadTrack(steps, lead)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
