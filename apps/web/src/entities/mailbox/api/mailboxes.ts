import 'server-only';

import { api, unwrap } from '@/shared/api/outboxlab-api';

import type { Mailbox } from '../model/types';

export async function getMailboxes(): Promise<Mailbox[]> {
  return unwrap(await (await api()).GET('/mailboxes'));
}
