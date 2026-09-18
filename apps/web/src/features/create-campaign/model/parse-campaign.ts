import type { NewCampaign } from '@/entities/campaign';

export const DELAY_UNITS = { minutes: 60, hours: 3_600, days: 86_400 } as const;
export type DelayUnit = keyof typeof DELAY_UNITS;

export interface CampaignFormErrors {
  name?: string;
  steps: Array<{ subject?: string; body?: string; delay?: string }>;
}

export interface CampaignFormValues {
  name: string;
  steps: Array<{ subject: string; body: string; delayAmount: string; delayUnit: string }>;
}

/** What the person typed, as typed, so a refused form can show it again. */
export function campaignFormValues(form: FormData): CampaignFormValues {
  const bodies = form.getAll('body').map(String);
  const amounts = form.getAll('delayAmount').map(String);
  const units = form.getAll('delayUnit').map(String);
  return {
    name: String(form.get('name') ?? ''),
    steps: form.getAll('subject').map((subject, index) => ({
      subject: String(subject),
      body: bodies[index] ?? '',
      delayAmount: amounts[index] ?? '0',
      delayUnit: units[index] ?? 'minutes',
    })),
  };
}

export type ParsedCampaign =
  { ok: true; campaign: NewCampaign } | { ok: false; errors: CampaignFormErrors };

function isDelayUnit(value: string): value is DelayUnit {
  return value in DELAY_UNITS;
}

/** Reads the campaign form: one name, and per step a subject, a body, a delay amount and its unit. */
export function parseCampaignForm(form: FormData): ParsedCampaign {
  const name = String(form.get('name') ?? '').trim();
  const subjects = form.getAll('subject').map(String);
  const bodies = form.getAll('body').map(String);
  const amounts = form.getAll('delayAmount').map(String);
  const units = form.getAll('delayUnit').map(String);

  const errors: CampaignFormErrors = { steps: [] };
  if (!name) {
    errors.name = 'Give the campaign a name.';
  } else if (name.length > 200) {
    errors.name = 'Keep the name under 200 characters.';
  }

  const steps: NewCampaign['steps'] = [];
  subjects.forEach((rawSubject, index) => {
    const subject = rawSubject.trim();
    const body = (bodies[index] ?? '').trim();
    const amount = Number((amounts[index] ?? '').trim() || '0');
    const unit = units[index] ?? 'minutes';
    const stepErrors: CampaignFormErrors['steps'][number] = {};
    if (!subject) {
      stepErrors.subject = 'Write a subject line.';
    }
    if (!body) {
      stepErrors.body = 'Write the email.';
    }
    if (!Number.isInteger(amount) || amount < 0 || !isDelayUnit(unit)) {
      stepErrors.delay = 'Use a whole number, zero or more.';
    }
    errors.steps[index] = stepErrors;
    if (Object.keys(stepErrors).length === 0 && isDelayUnit(unit)) {
      steps.push({ subject, body, delay_seconds: amount * DELAY_UNITS[unit] });
    }
  });

  const valid = !errors.name && subjects.length > 0 && steps.length === subjects.length;
  return valid ? { ok: true, campaign: { name, steps } } : { ok: false, errors };
}
