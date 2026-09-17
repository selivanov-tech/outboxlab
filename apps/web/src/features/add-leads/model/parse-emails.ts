const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const MAX_LEADS_PER_REQUEST = 1000;

export interface ParsedEmails {
  emails: string[];
  invalid: string[];
}

/** Splits pasted text on whitespace, commas and semicolons; lowercases, removes repeats, sets aside what is not an address. */
export function parseEmails(text: string): ParsedEmails {
  const seen = new Set<string>();
  const emails: string[] = [];
  const invalid: string[] = [];
  for (const piece of text.split(/[\s,;]+/)) {
    const candidate = piece.trim().toLowerCase();
    if (!candidate || seen.has(candidate)) {
      continue;
    }
    seen.add(candidate);
    (EMAIL.test(candidate) ? emails : invalid).push(candidate);
  }
  return { emails, invalid };
}
