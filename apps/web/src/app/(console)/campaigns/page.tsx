import type { Metadata } from 'next';
import Link from 'next/link';

import { CampaignList, type CampaignSummary } from '@/entities/campaign';
import { getCampaigns } from '@/entities/campaign/server';
import { LiveRefresh } from '@/features/live-refresh';
import { rethrowForPage } from '@/shared/api/outboxlab-api';

export const metadata: Metadata = { title: 'Campaigns' };
export const dynamic = 'force-dynamic';

export default async function CampaignsPage() {
  let campaigns: CampaignSummary[];
  try {
    campaigns = await getCampaigns();
  } catch (error) {
    rethrowForPage(error);
  }

  return (
    <>
      <div className="page-head">
        <h1>Campaigns</h1>
        <Link href="/campaigns/new" className="button">
          New campaign
        </Link>
      </div>
      {campaigns.length === 0 ? (
        <div className="empty-state">
          <h2>No campaigns yet</h2>
          <p>
            A campaign is a short sequence of emails sent to a list of leads. A lead who replies,
            unsubscribes or bounces stops getting the rest.
          </p>
          <Link href="/campaigns/new" className="button">
            Write the first campaign
          </Link>
        </div>
      ) : (
        <>
          <LiveRefresh intervalSeconds={5} />
          <CampaignList campaigns={campaigns} />
        </>
      )}
    </>
  );
}
