import React from 'react';
import { TopNavigation } from '@/components/navigation/TopNavigation';
import { CitizenFooter } from '@/components/layout/CitizenFooter';
import { MobileNavigation } from '@/components/navigation/MobileNavigation';

interface AppShellProps {
  children: React.ReactNode;
  showFooter?: boolean;
}

export function AppShell({ children, showFooter = true }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-on-surface">
      <TopNavigation />
      <main className="flex-1 w-full pt-16 pb-16 md:pb-0">
        {children}
      </main>
      {showFooter && <CitizenFooter />}
      <MobileNavigation />
    </div>
  );
}
