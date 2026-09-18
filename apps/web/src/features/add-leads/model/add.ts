'use server';

import { revalidatePath } from 'next/cache';

import { addLeads } from '@/entities/campaign/server';
import { messageForAction } from '@/shared/api/action-error';

import { MAX_LEADS_PER_REQUEST, parseEmails } from './parse-emails';

export interface AddLeadsState {
  tone: 'idle' | 'done' | 'error';
  message: string | null;
  /** What the person pasted, given back so a refused form keeps it. */
  text: string;
}

export async function add(
  campaignId: string,
  _: AddLeadsState,
  form: FormData,
): Promise<AddLeadsState> {
  const text = String(form.get('emails') ?? '');
  const { emails, invalid } = parseEmails(text);
  if (invalid.length > 0) {
    return {
      tone: 'error',
      message: `These are not email addresses: ${invalid.join(', ')}`,
      text,
    };
  }
  if (emails.length === 0) {
    return { tone: 'error', message: 'Paste at least one email address.', text };
  }
  if (emails.length > MAX_LEADS_PER_REQUEST) {
    return { tone: 'error', message: `Add up to ${MAX_LEADS_PER_REQUEST} leads at a time.`, text };
  }
  try {
    const result = await addLeads(campaignId, emails);
    revalidatePath(`/campaigns/${campaignId}`);
    const parts = [`Added ${result.added}`];
    if (result.skipped > 0) {
      parts.push(`${result.skipped} already in this campaign`);
    }
    if (result.scheduled > 0) {
      parts.push(`${result.scheduled} scheduled for the first step`);
    }
    return { tone: 'done', message: `${parts.join(' · ')}.`, text: '' };
  } catch (error) {
    return {
      tone: 'error',
      message: messageForAction(error, { 404: 'This campaign no longer exists.' }),
      text,
    };
  }
}
