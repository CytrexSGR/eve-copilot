import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EC Trade - Interactive EVE Online Map',
  description: 'We Like The Data',
  openGraph: {
    title: 'EC Trade - Interactive EVE Online Map',
    description: 'We Like The Data',
    type: 'website',
    images: [
      {
        url: '/ectrade.png',
        width: 256,
        height: 256,
        alt: 'EC Trade',
      },
    ],
  },
  twitter: {
    card: 'summary',
    title: 'EC Trade - Interactive EVE Online Map',
    description: 'We Like The Data',
    images: ['/ectrade.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="h-screen w-screen overflow-hidden fixed inset-0">{children}</body>
    </html>
  );
}
