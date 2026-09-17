const DATE_TIME = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
});

const CLOCK = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  timeZone: 'UTC',
});

/** Every time in the console is UTC: the daily send cap resets at 00:00 UTC, so one clock keeps it honest. */
export function formatDateTime(iso: string): string {
  return `${DATE_TIME.format(new Date(iso))} UTC`;
}

export function formatClock(date: Date): string {
  return `${CLOCK.format(date)} UTC`;
}

const UNITS: Array<[number, string]> = [
  [86_400, 'day'],
  [3_600, 'hour'],
  [60, 'minute'],
  [1, 'second'],
];

/** 90 → "1 minute 30 seconds", 172800 → "2 days": the two largest units. */
export function formatDuration(seconds: number): string {
  const parts: string[] = [];
  let rest = Math.max(0, seconds);
  for (const [size, name] of UNITS) {
    const count = Math.floor(rest / size);
    if (count > 0) {
      parts.push(`${count} ${name}${count === 1 ? '' : 's'}`);
      rest -= count * size;
    }
    if (parts.length === 2) {
      break;
    }
  }
  return parts.join(' ') || '0 seconds';
}

/** When a step goes out, counted from the campaign start for the first step and from the previous step after that. */
export function formatStepTiming(stepIndex: number, delaySeconds: number): string {
  const anchor = stepIndex === 0 ? 'the campaign starts' : 'the previous step';
  if (delaySeconds <= 0) {
    return stepIndex === 0 ? `Goes out as soon as ${anchor}` : `Goes out right after ${anchor}`;
  }
  return `Goes out ${formatDuration(delaySeconds)} after ${anchor}`;
}

export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

export function sentenceCase(value: string): string {
  const words = value.replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
