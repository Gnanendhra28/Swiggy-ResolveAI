'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ShoppingBag,
  Sparkles,
  PlayCircle,
  Activity,
  History,
  X,
  ChevronRight,
} from 'lucide-react';
import { SwiggyLogo } from './SwiggyLogo';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  systemStatus: 'healthy' | 'degraded' | 'offline';
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  systemStatus,
}) => {
  const pathname = usePathname();

  const navItems = [
    {
      label: 'Overview',
      href: '/',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      label: 'All Orders',
      href: '/orders',
      icon: ShoppingBag,
      badge: null,
    },
    {
      label: 'AI Insights',
      href: '/intelligence',
      icon: Sparkles,
      badge: null,
    },
    {
      label: 'Try Scenarios',
      href: '/simulation',
      icon: PlayCircle,
      badge: null,
    },
    {
      label: 'Performance',
      href: '/health',
      icon: Activity,
      badge: null,
    },
    {
      label: 'Activity History',
      href: '/intelligence#activity-history',
      icon: History,
      badge: null,
    },
  ];

  const getStatusColor = () => {
    switch (systemStatus) {
      case 'healthy':
        return 'bg-[#60B246]';
      case 'degraded':
        return 'bg-[#D97706]';
      case 'offline':
      default:
        return 'bg-[#E23744]';
    }
  };

  const getStatusLabel = () => {
    switch (systemStatus) {
      case 'healthy':
        return 'System Online';
      case 'degraded':
        return 'System Degraded';
      case 'offline':
      default:
        return 'System Offline';
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-[#282C3F]/40 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-white border-r border-[#E9ECEE] flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Header & Branding */}
        <div>
          <div className="h-16 px-5 border-b border-[#F4F5F7] flex items-center justify-between">
            <Link href="/" onClick={onClose}>
              <SwiggyLogo size="md" />
            </Link>
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-[#686B78] hover:bg-[#F4F5F7]"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Subtitle tag */}
          <div className="px-5 py-3 bg-[#FBFBFC] border-b border-[#F4F5F7]">
            <p className="text-[11px] font-semibold text-[#686B78] uppercase tracking-wider">
              Automated Delivery Support
            </p>
            <p className="text-[10px] text-[#93959F] mt-0.5">
              Smart order monitoring and proactive issue resolution
            </p>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isHashMatch = item.href.includes('#');
              const isActive = isHashMatch
                ? false
                : item.href === '/'
                ? pathname === '/'
                : pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-[#FFF5ED] text-[#FC8019] shadow-sm'
                      : 'text-[#686B78] hover:text-[#282C3F] hover:bg-[#F8F9FA]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`w-4 h-4 ${
                        isActive ? 'text-[#FC8019]' : 'text-[#686B78]'
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer: System Status & Provenance Notice */}
        <div className="p-4 border-t border-[#F4F5F7] bg-[#FBFBFC] space-y-3">
          {/* Real-time Health Pill */}
          <Link
            href="/health"
            onClick={onClose}
            className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-[#E9ECEE] hover:border-[#FC8019]/40 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${getStatusColor()}`}
                />
                <span
                  className={`relative inline-flex rounded-full h-2.5 w-2.5 ${getStatusColor()}`}
                />
              </span>
              <span className="text-[11px] font-semibold text-[#282C3F]">
                {getStatusLabel()}
              </span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-[#93959F]" />
          </Link>

          {/* Provenance Notice */}
          <div className="text-[10px] text-[#93959F] leading-tight">
            Prototype demonstration with simulated and public order data. Not connected to live Swiggy production systems.
          </div>
        </div>
      </aside>
    </>
  );
};
