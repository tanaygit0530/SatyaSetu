import type { Metadata } from 'next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: "SachCheck — Forward it. Know if it's true.",
  description:
    'AI-powered claim verification platform for multilingual India. Forward any WhatsApp text, screenshot, voice memo, or circular to verify with proof.',
  keywords: [
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
