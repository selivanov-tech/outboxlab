import { describe, expect, it } from 'vitest';

import {
  formatDateTime,
  formatDuration,
  formatPercent,
  formatStepTiming,
  sentenceCase,
} from './format';

describe('formatDuration', () => {
  it('uses the two largest units', () => {
    expect(formatDuration(90)).toBe('1 minute 30 seconds');
    expect(formatDuration(172_800)).toBe('2 days');
    expect(formatDuration(90_061)).toBe('1 day 1 hour');
  });
});

describe('formatStepTiming', () => {
  it('counts the first step from the campaign start', () => {
    expect(formatStepTiming(0, 0)).toBe('Goes out as soon as the campaign starts');
    expect(formatStepTiming(0, 3_600)).toBe('Goes out 1 hour after the campaign starts');
  });

  it('counts a follow-up from the previous step', () => {
    expect(formatStepTiming(1, 0)).toBe('Goes out right after the previous step');
    expect(formatStepTiming(1, 86_400)).toBe('Goes out 1 day after the previous step');
  });
});

describe('formatDateTime', () => {
  it('shows UTC whatever the server time zone is', () => {
    expect(formatDateTime('2026-09-13T21:05:00+05:00')).toBe('13 Sept, 16:05 UTC');
  });
});

describe('formatPercent', () => {
  it('rounds a ratio', () => {
    expect(formatPercent(0.256)).toBe('26%');
    expect(formatPercent(0)).toBe('0%');
  });
});

describe('sentenceCase', () => {
  it('turns an API value into a label', () => {
    expect(sentenceCase('send_failed')).toBe('Send failed');
  });
});
