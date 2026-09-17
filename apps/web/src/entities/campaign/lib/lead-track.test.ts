import { describe, expect, it } from 'vitest';

import type { CampaignStep, Lead } from '../model/types';
import { buildLeadTrack } from './lead-track';

const STEPS: CampaignStep[] = [
  { id: 's2', position: 2, subject: 'Following up', body: '…', delay_seconds: 86_400 },
  { id: 's1', position: 1, subject: 'Quick question', body: '…', delay_seconds: 0 },
];

function lead(overrides: Partial<Lead>): Lead {
  return {
    id: 'l1',
    email: 'ada@example.com',
    state: 'pending',
    steps_sent: 0,
    stop_reason: null,
    reply_intent: null,
    next_send_at: null,
    updated_at: '2026-09-13T10:00:00Z',
    ...overrides,
  };
}

describe('buildLeadTrack', () => {
  it('orders stops by step position', () => {
    const track = buildLeadTrack(STEPS, lead({}));
    expect(track.stops.map((stop) => stop.subject)).toEqual(['Quick question', 'Following up']);
  });

  it('marks the first step as next for a scheduled lead, with its send time', () => {
    const track = buildLeadTrack(
      STEPS,
      lead({ state: 'scheduled', next_send_at: '2026-09-13T10:05:00Z' }),
    );
    expect(track.stops.map((stop) => stop.status)).toEqual(['next', 'waiting']);
    expect(track.stops[0]?.sendAt).toBe('2026-09-13T10:05:00Z');
    expect(track.stamp).toBeNull();
  });

  it('cancels the follow-up when a reply paused the lead', () => {
    const track = buildLeadTrack(
      STEPS,
      lead({ state: 'paused', steps_sent: 1, stop_reason: 'replied', reply_intent: 'positive' }),
    );
    expect(track.stops.map((stop) => stop.status)).toEqual(['sent', 'cancelled']);
    expect(track.stamp).toEqual({ tone: 'replied', label: 'Replied · positive' });
  });

  it('stamps an unsubscribe differently from a reply', () => {
    const track = buildLeadTrack(
      STEPS,
      lead({
        state: 'paused',
        steps_sent: 1,
        stop_reason: 'unsubscribed',
        reply_intent: 'unsubscribe',
      }),
    );
    expect(track.stamp).toEqual({ tone: 'stopped', label: 'Unsubscribed' });
  });

  it('names why a lead failed', () => {
    const track = buildLeadTrack(
      STEPS,
      lead({ state: 'failed', steps_sent: 1, stop_reason: 'bounced', reply_intent: 'bounce' }),
    );
    expect(track.stops.map((stop) => stop.status)).toEqual(['sent', 'cancelled']);
    expect(track.stamp).toEqual({ tone: 'failed', label: 'Bounced' });
  });

  it('marks a finished sequence', () => {
    const track = buildLeadTrack(STEPS, lead({ state: 'done', steps_sent: 2 }));
    expect(track.stops.map((stop) => stop.status)).toEqual(['sent', 'sent']);
    expect(track.stamp).toEqual({ tone: 'complete', label: 'Complete' });
  });
});
