import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Sovereignty Map - EVE Copilot',
  description: 'Alliance sovereignty, ADM tracking, and cyno jammer intel',
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
