import { formatDateTime } from '@/shared/lib/format';

import type { LeadTrack as LeadTrackModel, TrackStop } from '../lib/lead-track';

interface LeadTrackProps {
  track: LeadTrackModel;
}

const STOP_LABEL: Record<TrackStop['status'], string> = {
  sent: 'sent',
  next: 'next',
  waiting: 'waiting',
  cancelled: 'cancelled',
};

/** A lead's route through the sequence, one stop per step, with a stamp when the route ended. */
export function LeadTrack({ track }: LeadTrackProps) {
  return (
    <div className="track-cell">
      <ol className="track">
        {track.stops.map((stop, index) => (
          <li
            key={stop.position}
            className={`stop stop--${stop.status}`}
            title={`Step ${index + 1}: ${stop.subject}`}
          >
            <span className="stop-dot" aria-hidden="true">
              {index + 1}
            </span>
            <span className="stop-text">
              <span className="visually-hidden">
                Step {index + 1}, {stop.subject}:{' '}
              </span>
              {stop.status === 'next' && stop.sendAt
                ? formatDateTime(stop.sendAt)
                : STOP_LABEL[stop.status]}
            </span>
          </li>
        ))}
      </ol>
      {track.stamp && (
        <span key={track.stamp.label} className={`stamp stamp--${track.stamp.tone}`}>
          {track.stamp.label}
        </span>
      )}
    </div>
  );
}
