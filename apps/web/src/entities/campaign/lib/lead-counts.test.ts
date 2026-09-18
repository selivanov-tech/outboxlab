import { describe, expect, it } from 'vitest';

import { leadSegments, totalLeads } from './lead-counts';

describe('leadSegments', () => {
  it('is empty for a campaign without leads', () => {
    expect(leadSegments({})).toEqual([]);
  });

  it('keeps lifecycle order and skips empty states', () => {
    const segments = leadSegments({ paused: 1, sent: 3 });
    expect(segments.map((segment) => segment.state)).toEqual(['sent', 'paused']);
    expect(segments.map((segment) => segment.share)).toEqual([75, 25]);
  });
});

describe('totalLeads', () => {
  it('ignores states it does not know', () => {
    expect(totalLeads({ sent: 2, archived: 5 })).toBe(2);
  });
});
