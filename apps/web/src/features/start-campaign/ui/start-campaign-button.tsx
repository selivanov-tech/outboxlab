'use client';

import { useActionState } from 'react';

import { start, type StartCampaignState } from '../model/start';

interface StartCampaignButtonProps {
  campaignId: string;
  hasLeads: boolean;
}

const INITIAL: StartCampaignState = { tone: 'idle', message: null };

export function StartCampaignButton({ campaignId, hasLeads }: StartCampaignButtonProps) {
  const [state, action, pending] = useActionState(start.bind(null, campaignId), INITIAL);
  return (
    <form action={action} className="start-campaign">
      <button type="submit" className="button" disabled={pending || !hasLeads}>
        {pending ? 'Starting…' : 'Start sending'}
      </button>
      <p className={`form-message form-message--${state.tone}`} role="status">
        {state.message ?? (hasLeads ? null : 'Add at least one lead first.')}
      </p>
    </form>
  );
}
