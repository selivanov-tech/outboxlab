'use client';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ reset }: ErrorPageProps) {
  return (
    <main className="lone-page">
      <h1>The API did not answer</h1>
      <p>
        The page could not load its data. Check that the OutboxLab API is running, then try again.
      </p>
      <button type="button" className="button" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
