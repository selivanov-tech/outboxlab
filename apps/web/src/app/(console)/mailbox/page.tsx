import type { Metadata } from 'next';

import { MailboxCard, type Mailbox } from '@/entities/mailbox';
import { getMailboxes } from '@/entities/mailbox/server';
import { LiveRefresh } from '@/features/live-refresh';
import { rethrowForPage } from '@/shared/api/outboxlab-api';

export const metadata: Metadata = { title: 'Mailbox' };
export const dynamic = 'force-dynamic';

export default async function MailboxPage() {
  let mailboxes: Mailbox[];
  try {
    mailboxes = await getMailboxes();
  } catch (error) {
    rethrowForPage(error);
  }

  return (
    <>
      <h1>Mailbox</h1>
      <p className="page-lede">
        Campaigns send from this Gmail mailbox. Each mailbox has a daily cap, counted per UTC day,
        so one busy campaign cannot burn its reputation.
      </p>
      {mailboxes.length === 0 ? (
        <div className="empty-state">
          <h2>No mailbox connected</h2>
          <p>
            Set <code>GMAIL_USER_EMAIL</code> and the Google OAuth values in the API environment,
            then run <code>make seed</code>. Campaigns cannot be created without a mailbox.
          </p>
        </div>
      ) : (
        <>
          <LiveRefresh intervalSeconds={15} />
          <div className="mailbox-grid">
            {mailboxes.map((mailbox) => (
              <MailboxCard key={mailbox.id} mailbox={mailbox} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
