import type { Metadata } from 'next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'SatyaSetu — Civic Truth: Before You Forward It, Verify It.',
  description:
    'AI-powered claim verification platform for multilingual India. Verify suspicious messages, screenshots, voice notes, and circulars with statutory proof.',
  keywords: [
    'SatyaSetu',
    'fact check',
    'misinformation',
    'WhatsApp forward check',
    'civic truth',
    'PIB fact check',
    'India news verification',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-font-scale="standard">
      <body className="bg-background font-sans text-on-surface antialiased min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
