import { describe, expect, it } from 'vitest';

import { parseCampaignForm } from './parse-campaign';

function form(entries: Array<[string, string]>): FormData {
  const data = new FormData();
  entries.forEach(([key, value]) => data.append(key, value));
  return data;
}

describe('parseCampaignForm', () => {
  it('turns delay amounts and units into seconds', () => {
    const parsed = parseCampaignForm(
      form([
        ['name', ' Q3 outreach '],
        ['subject', 'Quick question'],
        ['body', 'Hello'],
        ['delayAmount', '0'],
        ['delayUnit', 'minutes'],
        ['subject', 'Following up'],
        ['body', 'Hello again'],
        ['delayAmount', '2'],
        ['delayUnit', 'days'],
      ]),
    );
    expect(parsed).toEqual({
      ok: true,
      campaign: {
        name: 'Q3 outreach',
        steps: [
          { subject: 'Quick question', body: 'Hello', delay_seconds: 0 },
          { subject: 'Following up', body: 'Hello again', delay_seconds: 172_800 },
        ],
      },
    });
  });

  it('says which field of which step is wrong', () => {
    const parsed = parseCampaignForm(
      form([
        ['name', ''],
        ['subject', 'Quick question'],
        ['body', ''],
        ['delayAmount', '-1'],
        ['delayUnit', 'hours'],
      ]),
    );
    expect(parsed).toEqual({
      ok: false,
      errors: {
        name: 'Give the campaign a name.',
        steps: [{ body: 'Write the email.', delay: 'Use a whole number, zero or more.' }],
      },
    });
  });

  it('refuses a campaign without steps', () => {
    expect(parseCampaignForm(form([['name', 'Empty']])).ok).toBe(false);
  });
});
