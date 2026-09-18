import { LEAD_STATES, type LeadState } from '../model/types';

export interface LeadSegment {
  state: LeadState;
  count: number;
  /** Share of all leads, 0–100. */
  share: number;
}

export function totalLeads(counts: Record<string, number>): number {
  return LEAD_STATES.reduce((sum, state) => sum + (counts[state] ?? 0), 0);
}

/** The non-empty lead states in their lifecycle order, each with its share of the whole. */
export function leadSegments(counts: Record<string, number>): LeadSegment[] {
  const total = totalLeads(counts);
  if (total === 0) {
    return [];
  }
  return LEAD_STATES.filter((state) => (counts[state] ?? 0) > 0).map((state) => {
    const count = counts[state] ?? 0;
    return { state, count, share: (count / total) * 100 };
  });
}
