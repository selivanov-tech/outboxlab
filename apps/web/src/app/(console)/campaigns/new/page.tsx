import type { Metadata } from 'next';
import Link from 'next/link';

import { CreateCampaignForm } from '@/features/create-campaign';

export const metadata: Metadata = { title: 'New campaign' };

export default function NewCampaignPage() {
  return (
    <>
      <p className="breadcrumb">
        <Link href="/campaigns">Campaigns</Link>
      </p>
      <h1>New campaign</h1>
      <p className="page-lede">
        Write the emails in the order they go out. The campaign is saved as a draft: add leads next,
        then start sending.
      </p>
      <CreateCampaignForm />
    </>
  );
}
