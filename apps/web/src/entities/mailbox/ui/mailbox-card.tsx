import type { Mailbox } from '../model/types';

interface MailboxCardProps {
  mailbox: Mailbox;
}

export function MailboxCard({ mailbox }: MailboxCardProps) {
  const used =
    mailbox.daily_send_cap > 0
      ? Math.min(100, (mailbox.sent_today / mailbox.daily_send_cap) * 100)
      : 100;
  return (
    <article className="mailbox-card">
      <h2 className="mailbox-address">{mailbox.email_address}</h2>
      <div className="cap">
        <div className="cap-head">
          <span>Sent today</span>
          <span className="cap-figures">
            <b>{mailbox.sent_today}</b> of {mailbox.daily_send_cap}
          </span>
        </div>
        <div
          className="cap-meter"
          role="meter"
          aria-label="Emails sent today against the daily cap"
          aria-valuemin={0}
          aria-valuemax={mailbox.daily_send_cap}
          aria-valuenow={mailbox.sent_today}
        >
          <span className="cap-meter-fill" style={{ width: `${used}%` }} />
        </div>
        <p className="cap-note">
          {mailbox.remaining_today > 0
            ? `${mailbox.remaining_today} more can go out before 00:00 UTC. Jobs over the cap wait for the next day.`
            : 'The cap is reached. Waiting jobs go out after 00:00 UTC.'}
        </p>
      </div>
      <p className="mailbox-suppressed">
        <b>{mailbox.suppressed_addresses}</b>{' '}
        {mailbox.suppressed_addresses === 1 ? 'address is' : 'addresses are'} never mailed again
        (unsubscribed or bounced).
      </p>
    </article>
  );
}
