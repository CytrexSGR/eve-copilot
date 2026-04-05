import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Capital Operations Map',
  description: 'EVE Online Capital Operations Galaxy Map',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
