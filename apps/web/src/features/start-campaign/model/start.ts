'use server';

import { revalidatePath } from 'next/cache';

import { startCampaign } from '@/entities/campaign/server';
import { messageForAction } from '@/shared/api/action-error';

export interface StartCampaignState {
  tone: 'idle' | 'done' | 'error';
  message: string | null;
}

export async function start(campaignId: string): Promise<StartCampaignState> {
  try {
    const result = await startCampaign(campaignId);
    revalidatePath(`/campaigns/${campaignId}`);
    return {
      tone: 'done',
      message:
        result.scheduled > 0
          ? `Started. ${result.scheduled} ${result.scheduled === 1 ? 'lead is' : 'leads are'} scheduled for the first step.`
          : 'Already started. Nothing new to schedule.',
    };
  } catch (error) {
    return {
      tone: 'error',
      message: messageForAction(error, {
        404: 'This campaign no longer exists.',
        422: 'Add at least one lead before starting.',
      }),
    };
  }
}
