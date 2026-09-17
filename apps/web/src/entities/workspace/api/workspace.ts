import 'server-only';

import { api, apiFor, unwrap } from '@/shared/api/outboxlab-api';
import type { Credentials } from '@/shared/session';

import type { Workspace, WorkspaceState } from '../model/types';

export async function getWorkspace(): Promise<Workspace> {
  return unwrap(await (await api()).GET('/workspaces/me'));
}

/** Checks a credential before it becomes the session: the API answers with the workspace it opens. */
export async function getWorkspaceWith(credentials: Credentials): Promise<Workspace> {
  return unwrap(await apiFor(credentials).GET('/workspaces/me'));
}

export async function getWorkspaceState(): Promise<WorkspaceState> {
  return unwrap(await (await api()).GET('/debug/state'));
}
