import 'server-only';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { secureCookies } from '@/shared/config/server-env';

import { decodeCredentials, encodeCredentials, type Credentials } from './credentials';

const SESSION_COOKIE = 'outboxlab_session';
const THIRTY_DAYS = 60 * 60 * 24 * 30;

export const CONNECT_PATH = '/connect';
export const DISCONNECT_PATH = '/disconnect';

export async function readCredentials(): Promise<Credentials | null> {
  return decodeCredentials((await cookies()).get(SESSION_COOKIE)?.value);
}

export async function requireCredentials(): Promise<Credentials> {
  const credentials = await readCredentials();
  if (!credentials) {
    redirect(CONNECT_PATH);
  }
  return credentials;
}

/** Only a Server Action or a Route Handler may call this: a page render cannot set cookies. */
export async function storeCredentials(credentials: Credentials): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, encodeCredentials(credentials), {
    httpOnly: true,
    sameSite: 'strict',
    secure: secureCookies(),
    path: '/',
    maxAge: THIRTY_DAYS,
  });
}

export async function clearCredentials(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}
