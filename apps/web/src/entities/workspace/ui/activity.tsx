import { formatDateTime, sentenceCase } from '@/shared/lib/format';

import type { WorkspaceState } from '../model/types';

interface ActivityProps {
  state: WorkspaceState;
}

function countsLine(counts: Record<string, number>): string {
  const entries = Object.entries(counts);
  return entries.length > 0
    ? entries.map(([name, count]) => `${sentenceCase(name)} ${count}`).join(' · ')
    : 'None yet';
}

const EVENT_NAMES: Record<string, string> = {
  InboundReceived: 'Email received',
  ReplyMatched: 'Reply matched to a sent email',
  ReplyClassified: 'Reply classified',
};

export function Activity({ state }: ActivityProps) {
  return (
    <>
      <dl className="facts">
        <div>
          <dt>Inbox sync</dt>
          <dd>
            {state.mailbox_last_sync_cursor
              ? `Following the inbox (cursor ${state.mailbox_last_sync_cursor})`
              : 'Not started. The worker sets a starting point on its first poll; replies sent before that are not seen.'}
          </dd>
        </div>
        <div>
          <dt>Emails</dt>
          <dd>
            {state.outbound_count} sent · {state.inbound_count} received
          </dd>
        </div>
        <div>
          <dt>Leads</dt>
          <dd>{countsLine(state.leads)}</dd>
        </div>
        <div>
          <dt>Send jobs</dt>
          <dd>{countsLine(state.send_jobs)}</dd>
        </div>
        <div>
          <dt>Reply intents</dt>
          <dd>{countsLine(state.intents)}</dd>
        </div>
      </dl>
      <h2>Latest events</h2>
      {state.recent_events.length === 0 ? (
        <p className="empty-note">
          Nothing yet. Events appear when the worker receives mail for this workspace.
        </p>
      ) : (
        <div className="table-scroll">
          <table className="event-table">
            <thead>
              <tr>
                <th scope="col">Event</th>
                <th scope="col">Message</th>
                <th scope="col">When</th>
              </tr>
            </thead>
            <tbody>
              {state.recent_events.map((event) => (
                <tr key={`${event.event_type}-${event.aggregate_id}-${event.created_at}`}>
                  <td>{EVENT_NAMES[event.event_type] ?? event.event_type}</td>
                  <td className="mono">{event.aggregate_id.slice(0, 8)}</td>
                  <td>{formatDateTime(event.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
