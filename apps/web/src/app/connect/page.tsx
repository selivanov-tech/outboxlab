import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import { ConnectForm } from '@/features/connect-workspace';
import { readCredentials } from '@/shared/session/session';
import { Wordmark } from '@/shared/ui/wordmark';

export const metadata: Metadata = { title: 'Connect a workspace' };

interface ConnectPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ConnectPage({ searchParams }: ConnectPageProps) {
  if (await readCredentials()) {
    redirect('/campaigns');
  }
  const rejected = (await searchParams).reason === 'rejected';
  return (
    <main className="connect-page">
      <section className="envelope" aria-labelledby="connect-title">
        <div className="envelope-inner">
          <Wordmark />
          <h1 id="connect-title">Connect a workspace</h1>
          <p className="envelope-lede">
            Paste the workspace API key. It stays in a cookie only this server can read, and every
            request to the API is made from here, not from your browser.
          </p>
          {rejected && (
            <p className="notice" role="status">
              The API stopped accepting the saved key, so the workspace was disconnected.
            </p>
          )}
          <ConnectForm />
        </div>
      </section>
    </main>
  );
}
