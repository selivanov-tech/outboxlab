'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { formatClock } from '@/shared/lib/format';

interface LiveRefreshProps {
  intervalSeconds: number;
}

/**
 * Re-renders the server components of the page on a timer, so a lead that pauses shows up without
 * a reload. It rests while the tab is hidden.
 */
export function LiveRefresh({ intervalSeconds }: LiveRefreshProps) {
  const router = useRouter();
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') {
        router.refresh();
        setRefreshedAt(new Date());
      }
    };
    const timer = window.setInterval(tick, intervalSeconds * 1000);
    document.addEventListener('visibilitychange', tick);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [intervalSeconds, router]);

  return (
    <p className="live-refresh" role="status">
      <span className="live-dot" aria-hidden="true" />
      Live · refreshes every {intervalSeconds} seconds
      {refreshedAt ? ` · last at ${formatClock(refreshedAt)}` : ''}
    </p>
  );
}
