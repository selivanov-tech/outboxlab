import { describe, expect, it } from 'vitest';

import { parseEmails } from './parse-emails';

describe('parseEmails', () => {
  it('splits on whitespace, commas and semicolons', () => {
    expect(parseEmails('ada@example.com, grace@example.com;\nlinus@example.com').emails).toEqual([
      'ada@example.com',
      'grace@example.com',
      'linus@example.com',
    ]);
  });

  it('lowercases and removes repeats', () => {
    expect(parseEmails('Ada@Example.com ada@example.com').emails).toEqual(['ada@example.com']);
  });

  it('sets aside what is not an address', () => {
    expect(parseEmails('ada@example.com not-an-email @nobody')).toEqual({
      emails: ['ada@example.com'],
      invalid: ['not-an-email', '@nobody'],
    });
  });

  it('finds nothing in blank text', () => {
    expect(parseEmails('  \n ')).toEqual({ emails: [], invalid: [] });
  });
});
