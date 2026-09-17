import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="lone-page">
      <h1>Nothing at this address</h1>
      <p>The campaign may belong to another workspace, or the link is wrong.</p>
      <p>
        <Link href="/campaigns">Back to campaigns</Link>
      </p>
    </main>
  );
}
