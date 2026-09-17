import Link from 'next/link';
import type { ReactNode } from 'react';

import { describeCredentials } from '@/shared/session';
import { DISCONNECT_PATH, requireCredentials } from '@/shared/session/session';
import { NavLink } from '@/shared/ui/nav-link';
import { Wordmark } from '@/shared/ui/wordmark';

export default async function ConsoleLayout({ children }: { children: ReactNode }) {
  const credentials = await requireCredentials();
  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <Link href="/campaigns" className="site-brand">
            <Wordmark />
          </Link>
          <nav className="site-nav" aria-label="Main">
            <NavLink href="/campaigns">Campaigns</NavLink>
            <NavLink href="/mailbox">Mailbox</NavLink>
            <NavLink href="/activity">Activity</NavLink>
          </nav>
          <form action={DISCONNECT_PATH} method="post" className="session">
            <span className="session-credential">{describeCredentials(credentials)}</span>
            <button type="submit" className="button button--on-ink">
              Disconnect
            </button>
          </form>
        </div>
      </header>
      <main className="console-main">{children}</main>
    </>
  );
}
