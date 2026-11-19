'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Menu,
  Search,
  PlayCircle,
  Activity,
  CheckCircle2,
  Clock,
  Sparkles,
} from 'lucide-react';
import { SwiggyLogo } from './SwiggyLogo';

interface TopHeaderProps {
  onOpenSidebar: () => void;
  systemStatus: 'healthy' | 'degraded' | 'offline';
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  onOpenSidebar,
  systemStatus,
}) => {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/orders?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const getStatusBadge = () => {
    switch (systemStatus) {
      case 'healthy':
        return {
          bg: 'bg-[#EDF7EC]',
          text: 'text-[#60B246]',
          border: 'border-[#C8E6C9]',
          dot: 'bg-[#60B246]',
          label: 'System Active',
        };
      case 'degraded':
        return {
          bg: 'bg-[#FFF8E6]',
          text: 'text-[#D97706]',
          border: 'border-[#FDE68A]',
          dot: 'bg-[#D97706]',
          label: 'Service Slow',
        };
      case 'offline':
      default:
        return {
          bg: 'bg-[#FDF0F1]',
          text: 'text-[#E23744]',
          border: 'border-[#FECDD3]',
          dot: 'bg-[#E23744]',
          label: 'Offline',
        };
    }
  };

  const statusStyle = getStatusBadge();

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-[#E9ECEE] px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
      {/* Mobile Menu Trigger & Logo */}
      <div className="flex items-center gap-3 lg:hidden">
        <button
          onClick={onOpenSidebar}
          className="p-2 -ml-2 rounded-xl text-[#282C3F] hover:bg-[#F4F5F7] transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <Link href="/">
          <SwiggyLogo size="sm" showSubtitle={false} />
        </Link>
      </div>

      {/* Global Quick Search Bar */}
      <form
        onSubmit={handleSearch}
        className="hidden md:flex items-center relative flex-1 max-w-md"
      >
        <Search className="w-4 h-4 text-[#93959F] absolute left-3.5" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search orders by ID, restaurant, or customer name..."
          className="w-full pl-9 pr-4 py-2 bg-[#F8F9FA] hover:bg-[#F4F5F7] focus:bg-white text-xs text-[#282C3F] placeholder-[#93959F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019] focus:ring-1 focus:ring-[#FC8019] transition-all"
        />
      </form>

      {/* Header Actions */}
      <div className="flex items-center gap-2.5 sm:gap-3 ml-auto">
        {/* Status Indicator */}
        <Link
          href="/health"
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border} transition-colors`}
        >
          <span className={`w-2 h-2 rounded-full ${statusStyle.dot}`} />
          <span className="hidden sm:inline">{statusStyle.label}</span>
        </Link>

        {/* Quick Simulation CTA */}
        <Link
          href="/simulation"
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-[#FC8019] hover:bg-[#E27315] text-white shadow-sm shadow-orange-500/20 hover:shadow transition-all"
        >
          <PlayCircle className="w-3.5 h-3.5" />
          <span>Try Scenarios</span>
        </Link>
      </div>
    </header>
  );
};
