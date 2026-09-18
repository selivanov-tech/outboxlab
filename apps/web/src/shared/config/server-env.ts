import 'server-only';

const DEFAULT_API_URL = 'http://localhost:8000';

/** The OutboxLab API as the Next.js server reaches it. */
export function apiBaseUrl(): string {
  return (process.env.OUTBOXLAB_API_URL ?? DEFAULT_API_URL).replace(/\/+$/, '');
}

/** Session cookies are marked Secure everywhere except a plain-http local run. */
export function secureCookies(): boolean {
  return process.env.NODE_ENV === 'production';
}
