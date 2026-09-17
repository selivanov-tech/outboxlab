import type { Metadata } from 'next';

import { Activity, type WorkspaceState } from '@/entities/workspace';
import { getWorkspaceState } from '@/entities/workspace/server';
import { LiveRefresh } from '@/features/live-refresh';
import { rethrowForPage } from '@/shared/api/outboxlab-api';

export const metadata: Metadata = { title: 'Activity' };
export const dynamic = 'force-dynamic';

export default async function ActivityPage() {
  let state: WorkspaceState;
  try {
    state = await getWorkspaceState();
  } catch (error) {
    rethrowForPage(error);
  }

  return (
    <>
      <h1>Activity</h1>
      <p className="page-lede">
        What the worker has done for this workspace: mail in and out, the send queue, and the events
        behind every paused lead.
      </p>
      <LiveRefresh intervalSeconds={5} />
      <Activity state={state} />
    </>
  );
}
