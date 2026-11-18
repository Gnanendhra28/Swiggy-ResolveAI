import type { Metadata } from 'next';
import { Suspense } from 'react';
import './globals.css';
import { AppShell } from '@/components/AppShell';

export const metadata: Metadata = {
  title: 'Swiggy ResolveAI — Proactive Order Intelligence & Autonomous Recovery',
  description:
    'Proactive food delivery order anomaly detection, operational intelligence, and autonomous recovery platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F4F5F7] text-[#282C3F] antialiased selection:bg-[#FC8019] selection:text-white">
        <AppShell>
          <Suspense
            fallback={
              <div className="py-24 text-center text-[#686B78] text-sm font-medium">
                Loading Swiggy ResolveAI...
              </div>
            }
          >
            {children}
          </Suspense>
        </AppShell>
      </body>
    </html>
  );
}
