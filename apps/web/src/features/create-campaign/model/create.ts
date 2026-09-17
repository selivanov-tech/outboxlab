'use server';

import { redirect } from 'next/navigation';

import { createCampaign } from '@/entities/campaign/server';
import { messageForAction } from '@/shared/api/action-error';

import {
  campaignFormValues,
  parseCampaignForm,
  type CampaignFormErrors,
  type CampaignFormValues,
} from './parse-campaign';

export interface CreateCampaignState {
  errors: CampaignFormErrors | null;
  message: string | null;
  values: CampaignFormValues | null;
}

export async function create(_: CreateCampaignState, form: FormData): Promise<CreateCampaignState> {
  const values = campaignFormValues(form);
  const parsed = parseCampaignForm(form);
  if (!parsed.ok) {
    return {
      errors: parsed.errors,
      message: 'Some fields need fixing before the campaign is saved.',
      values,
    };
  }
  let id: string;
  try {
    ({ id } = await createCampaign(parsed.campaign));
  } catch (error) {
    return {
      values,
      errors: null,
      message: messageForAction(error, {
        409: 'This workspace has no mailbox connected, so a campaign has nothing to send from. Set GMAIL_USER_EMAIL and run "make seed".',
      }),
    };
  }
  redirect(`/campaigns/${id}`);
}
