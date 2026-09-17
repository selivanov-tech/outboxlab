import type { Metadata } from 'next';
import Link from 'next/link';

import {
  LeadTable,
  MetricsStrip,
  StepList,
  type CampaignDetail,
  type CampaignMetrics,
} from '@/entities/campaign';
import { getCampaign, getCampaignMetrics } from '@/entities/campaign/server';
import { AddLeadsForm } from '@/features/add-leads';
import { LiveRefresh } from '@/features/live-refresh';
import { StartCampaignButton } from '@/features/start-campaign';
import { rethrowForPage } from '@/shared/api/outboxlab-api';
import { StateBadge } from '@/shared/ui/state-badge';

export const metadata: Metadata = { title: 'Campaign' };
export const dynamic = 'force-dynamic';

interface CampaignPageProps {
  params: Promise<{ id: string }>;
}

export default async function CampaignPage({ params }: CampaignPageProps) {
  const { id } = await params;
  let campaign: CampaignDetail;
  let metrics: CampaignMetrics;
  try {
    [campaign, metrics] = await Promise.all([getCampaign(id), getCampaignMetrics(id)]);
  } catch (error) {
    rethrowForPage(error);
  }
  const draft = campaign.status === 'draft';

  return (
    <>
      <p className="breadcrumb">
        <Link href="/campaigns">Campaigns</Link>
      </p>
      <div className="page-head">
        <h1>
          {campaign.name} <StateBadge state={campaign.status} />
        </h1>
        {draft && (
          <StartCampaignButton campaignId={campaign.id} hasLeads={campaign.leads.length > 0} />
        )}
      </div>
      <LiveRefresh intervalSeconds={5} />

      <MetricsStrip metrics={metrics} />

      <div className="campaign-columns">
        <section aria-labelledby="leads-title" className="campaign-leads">
          <h2 id="leads-title">Leads</h2>
          {campaign.leads.length === 0 ? (
            <p className="empty-note">
              No leads yet. Add the addresses this sequence should go to.
            </p>
          ) : (
            <LeadTable steps={campaign.steps} leads={campaign.leads} />
          )}
        </section>
        <aside className="campaign-side">
          <section aria-labelledby="sequence-title">
            <h2 id="sequence-title">Sequence</h2>
            <StepList steps={campaign.steps} />
          </section>
          <section aria-labelledby="add-leads-title">
            <h2 id="add-leads-title">Add leads</h2>
            <AddLeadsForm campaignId={campaign.id} campaignActive={!draft} />
          </section>
        </aside>
      </div>
    </>
  );
}
