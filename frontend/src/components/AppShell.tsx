'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { Sidebar } from './Sidebar';
import { TopHeader } from './TopHeader';
import { fetchHealth } from '@/lib/api';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState<'healthy' | 'degraded' | 'offline'>('healthy');

  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      try {
        const h = await fetchHealth();
        if (isMounted) {
          setSystemStatus(h.status === 'healthy' ? 'healthy' : 'degraded');
        }
      } catch {
        if (isMounted) {
          setSystemStatus('offline');
        }
      }
    };

    check();
    const interval = setInterval(check, 12000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#F4F5F7] text-[#282C3F] flex">
      {/* Fixed Left Sidebar wrapped in Suspense for usePathname() */}
      <Suspense fallback={<div className="hidden lg:block w-64 bg-white border-r border-[#E9ECEE]" />}>
        <Sidebar
          isOpen={isMobileSidebarOpen}
          onClose={() => setIsMobileSidebarOpen(false)}
          systemStatus={systemStatus}
        />
      </Suspense>

      {/* Main App Container */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen min-w-0">
        <Suspense fallback={<div className="h-16 bg-white border-b border-[#E9ECEE]" />}>
          <TopHeader
            onOpenSidebar={() => setIsMobileSidebarOpen(true)}
            systemStatus={systemStatus}
          />
        </Suspense>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>

        <footer className="border-t border-[#E9ECEE] bg-white py-4 px-6 text-center text-xs text-[#93959F]">
          <p>
            <strong className="text-[#686B78]">Swiggy ResolveAI</strong> — Automated Order Support & Resolution Platform • Operations Console • Demo and historical order simulation
          </p>
        </footer>
      </div>
    </div>
  );
};

