import 'server-only';

import { redirect } from 'next/navigation';

import { DISCONNECT_PATH } from '@/shared/session/session';

import { ApiError } from './outboxlab-api';

/**
 * For a Server Action: a rejected credential ends the session; any other API answer becomes a
 * message the form shows. Errors that are not API answers are rethrown.
 */
export function messageForAction(error: unknown, messages: Record<number, string> = {}): string {
  if (!(error instanceof ApiError)) {
    throw error;
  }
  if (error.status === 401) {
    redirect(`${DISCONNECT_PATH}?reason=rejected`);
  }
  return messages[error.status] ?? `The API refused this (${error.status}): ${error.detail}`;
}
