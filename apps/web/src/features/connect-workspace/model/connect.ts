'use server';

import { redirect } from 'next/navigation';

import { getWorkspaceWith } from '@/entities/workspace/server';
import { ApiError } from '@/shared/api/outboxlab-api';
import { parseCredentials } from '@/shared/session';
import { storeCredentials } from '@/shared/session/session';

export interface ConnectState {
  error: string | null;
}

export async function connect(_: ConnectState, form: FormData): Promise<ConnectState> {
  const credentials = parseCredentials(String(form.get('credential') ?? ''));
  if (!credentials) {
    return {
      error:
        'That is neither an API key nor a workspace id. A key starts with "olab_"; a workspace id is a UUID.',
    };
  }
  try {
    await getWorkspaceWith(credentials);
  } catch (error) {
    if (error instanceof ApiError) {
      return { error: rejection(error, credentials.kind) };
    }
    return { error: 'The API did not answer. Check that it is running and try again.' };
  }
  await storeCredentials(credentials);
  redirect('/campaigns');
}

function rejection(error: ApiError, kind: 'apiKey' | 'workspaceId'): string {
  if (error.status === 401 && kind === 'workspaceId') {
    return 'This API accepts only API keys. Create one with "make api-key" and paste it here.';
  }
  if (error.status === 401) {
    return 'The API does not know this key, or the key was revoked.';
  }
  if (error.status === 404) {
    return 'No workspace has this id. Run "make seed" to create the default workspace.';
  }
  return `The API refused the connection (${error.status}): ${error.detail}`;
}
