import type { Metadata } from 'next';
import { Big_Shoulders, IBM_Plex_Mono, Public_Sans } from 'next/font/google';
import type { ReactNode } from 'react';

import './globals.css';

const display = Big_Shoulders({
  adjustFontFallback: false,
  subsets: ['latin'],
  weight: ['700', '800'],
  variable: '--font-display',
});
const body = Public_Sans({ subsets: ['latin'], variable: '--font-body' });
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: { default: 'OutboxLab', template: '%s — OutboxLab' },
  description: 'Run short email sequences and watch every lead move through them.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
