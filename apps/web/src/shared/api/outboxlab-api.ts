import 'server-only';

import createClient from 'openapi-fetch';
import { notFound, redirect } from 'next/navigation';

import { apiBaseUrl } from '@/shared/config/server-env';
import { authHeaders, type Credentials } from '@/shared/session/credentials';
import { DISCONNECT_PATH, requireCredentials } from '@/shared/session/session';

import type { paths } from './generated/api-v1';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`OutboxLab API answered ${status}: ${detail}`);
    this.name = 'ApiError';
  }
}

export function apiFor(credentials: Credentials) {
  return createClient<paths>({
    baseUrl: apiBaseUrl(),
    headers: authHeaders(credentials),
    fetch: (request) => fetch(request, { cache: 'no-store' }),
  });
}

/** The API client of the connected workspace; sends a visitor without a session to the connect page. */
export async function api() {
  return apiFor(await requireCredentials());
}

interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

export function unwrap<T>(result: ApiResult<T>): T {
  if (result.data !== undefined) {
    return result.data;
  }
  throw new ApiError(result.response.status, detailOf(result.error));
}

function detailOf(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : ''))
        .filter(Boolean)
        .join('; ');
    }
  }
  return 'no detail';
}

/**
 * For a page render: a rejected credential ends the session, a missing record is a 404 page,
 * anything else reaches the error boundary.
 */
export function rethrowForPage(error: unknown): never {
  if (error instanceof ApiError && error.status === 401) {
    redirect(`${DISCONNECT_PATH}?reason=rejected`);
  }
  if (error instanceof ApiError && error.status === 404) {
    notFound();
  }
  throw error;
}
