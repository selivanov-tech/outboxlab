import { sentenceCase } from '@/shared/lib/format';

import type { CampaignStep, Lead } from '../model/types';

export type StopStatus = 'sent' | 'next' | 'waiting' | 'cancelled';
export type StampTone = 'replied' | 'stopped' | 'failed' | 'complete';

export interface TrackStop {
  position: number;
  subject: string;
  status: StopStatus;
  /** When the next step goes out; only the `next` stop has it. */
  sendAt: string | null;
}

export interface TrackStamp {
  tone: StampTone;
  label: string;
}

export interface LeadTrack {
  stops: TrackStop[];
  stamp: TrackStamp | null;
}

const HALTED = new Set(['paused', 'failed']);

/**
 * A lead's way through the sequence: which steps went out, which one is next and when, and which
 * will never go out because the lead replied, unsubscribed, bounced or failed.
 */
export function buildLeadTrack(steps: CampaignStep[], lead: Lead): LeadTrack {
  const ordered = [...steps].sort((a, b) => a.position - b.position);
  const halted = HALTED.has(lead.state);
  const stops = ordered.map((step, index): TrackStop => {
    const ordinal = index + 1;
    let status: StopStatus = 'waiting';
    if (ordinal <= lead.steps_sent) {
      status = 'sent';
    } else if (halted) {
      status = 'cancelled';
    } else if (ordinal === lead.steps_sent + 1) {
      status = 'next';
    }
    return {
      position: step.position,
      subject: step.subject,
      status,
      sendAt: status === 'next' ? (lead.next_send_at ?? null) : null,
    };
  });
  return { stops, stamp: stampFor(lead) };
}

function stampFor(lead: Lead): TrackStamp | null {
  if (lead.state === 'done') {
    return { tone: 'complete', label: 'Complete' };
  }
  if (lead.state === 'paused') {
    if (lead.stop_reason === 'unsubscribed') {
      return { tone: 'stopped', label: 'Unsubscribed' };
    }
    return {
      tone: 'replied',
      label: lead.reply_intent ? `Replied · ${lead.reply_intent}` : 'Replied',
    };
  }
  if (lead.state === 'failed') {
    return { tone: 'failed', label: sentenceCase(lead.stop_reason ?? 'failed') };
  }
  return null;
}
