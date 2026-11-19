'use client';

import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Truck,
  Store,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  Flame,
  Check,
  PackageCheck,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { OrderEvent } from '@/lib/types';

interface EventTimelineProps {
  events: OrderEvent[];
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ events }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const getEventFriendlyTitle = (type: string) => {
    const t = type.toUpperCase();
    switch (t) {
      case 'ORDER_PLACED':
        return 'Order Received from Customer';
      case 'RESTAURANT_ACCEPTED':
        return 'Restaurant Confirmed Order';
      case 'PREPARATION_STARTED':
        return 'Kitchen Began Preparation';
      case 'FOOD_READY':
        return 'Food Packed & Ready for Pickup';
      case 'RIDER_ASSIGNED':
        return 'Delivery Partner Assigned';
      case 'RIDER_ARRIVED_AT_STORE':
        return 'Delivery Partner Reached Merchant';
      case 'ORDER_PICKED_UP':
        return 'Order Picked Up & On the Way';
      case 'KITCHEN_DELAY_DETECTED':
        return 'Kitchen Preparation Delay Identified';
      case 'COURIER_ALLOTMENT_TIMEOUT':
        return 'Extended Delivery Partner Search';
      case 'TRAFFIC_CONGESTION_DETECTED':
        return 'Transit Delay / Heavy Road Traffic';
      case 'RECOVERY_TRIGGERED':
        return 'Automated Support Action Suggested';
      case 'RIDER_REASSIGNED':
        return 'Delivery Partner Reassigned';
      case 'WALLET_CREDIT_ISSUED':
        return 'Apology Credit Issued to Customer';
      case 'CUSTOMER_SUPPORT_INQUIRY':
        return 'Customer Contacted Support';
      case 'ORDER_DELIVERED':
        return 'Order Delivered Successfully';
      default:
        return t.replace(/_/g, ' ');
    }
  };

  const getEventConfig = (type: string, isLast: boolean) => {
    const t = type.toUpperCase();

    if (t === 'ORDER_PLACED') {
      return {
        icon: <Clock className="w-4 h-4 text-white" />,
        nodeBg: 'bg-[#FC8019]',
        badgeBg: 'bg-[#FFF5ED]',
        badgeText: 'text-[#FC8019]',
        badgeBorder: 'border-[#FED7AA]',
      };
    }
    if (t === 'RESTAURANT_ACCEPTED' || t === 'FOOD_READY' || t === 'PREPARATION_STARTED') {
      return {
        icon: <Store className="w-4 h-4 text-white" />,
        nodeBg: 'bg-[#FC8019]',
        badgeBg: 'bg-[#FFF5ED]',
        badgeText: 'text-[#FC8019]',
        badgeBorder: 'border-[#FED7AA]',
      };
    }
    if (t.includes('RIDER') || t === 'ORDER_PICKED_UP') {
      if (t.includes('TIMEOUT')) {
        return {
          icon: <ShieldAlert className="w-4 h-4 text-[#D97706]" />,
          nodeBg: 'bg-[#FEF3C7] border-2 border-[#D97706]',
          badgeBg: 'bg-[#FFF8E6]',
          badgeText: 'text-[#D97706]',
          badgeBorder: 'border-[#FDE68A]',
        };
      }
      return {
        icon: <Truck className="w-4 h-4 text-white" />,
        nodeBg: 'bg-[#FC8019]',
        badgeBg: 'bg-[#FFF5ED]',
        badgeText: 'text-[#FC8019]',
        badgeBorder: 'border-[#FED7AA]',
      };
    }
    if (t.includes('DELAY') || t.includes('CONGESTION') || t.includes('STOCKOUT') || t.includes('ANOMALY')) {
      return {
        icon: <AlertTriangle className="w-4 h-4 text-[#D97706]" />,
        nodeBg: 'bg-[#FFF8E6] border-2 border-[#D97706]',
        badgeBg: 'bg-[#FFF8E6]',
        badgeText: 'text-[#D97706]',
        badgeBorder: 'border-[#FDE68A]',
      };
    }
    if (t.includes('RECOVERY_SUCCESSFUL') || t === 'ORDER_DELIVERED') {
      return {
        icon: <PackageCheck className="w-4 h-4 text-white" />,
        nodeBg: 'bg-[#60B246]',
        badgeBg: 'bg-[#EDF7EC]',
        badgeText: 'text-[#60B246]',
        badgeBorder: 'border-[#C8E6C9]',
      };
    }
    if (t.includes('RECOVERY') || t.includes('REASSIGNED') || t.includes('WALLET_CREDIT')) {
      return {
        icon: <RefreshCw className="w-4 h-4 text-white" />,
        nodeBg: 'bg-[#FC8019]',
        badgeBg: 'bg-[#FFF5ED]',
        badgeText: 'text-[#FC8019]',
        badgeBorder: 'border-[#FED7AA]',
      };
    }
    if (t.includes('FAIL') || t.includes('ESCALATED')) {
      return {
        icon: <AlertCircle className="w-4 h-4 text-[#E23744]" />,
        nodeBg: 'bg-[#FDF0F1] border-2 border-[#E23744]',
        badgeBg: 'bg-[#FDF0F1]',
        badgeText: 'text-[#E23744]',
        badgeBorder: 'border-[#FECDD3]',
      };
    }

    return {
      icon: <Check className="w-4 h-4 text-[#686B78]" />,
      nodeBg: 'bg-[#F4F5F7] border-2 border-[#D1D5DB]',
      badgeBg: 'bg-[#F4F5F7]',
      badgeText: 'text-[#686B78]',
      badgeBorder: 'border-[#E5E7EB]',
    };
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return {
        time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        date: d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }),
      };
    } catch {
      return { time: iso, date: '' };
    }
  };

  if (!events || events.length === 0) {
    return (
      <div className="py-12 text-center bg-white rounded-2xl border border-[#E9ECEE] p-6">
        <HelpCircle className="w-8 h-8 text-[#93959F] mx-auto mb-2" />
        <p className="text-sm font-medium text-[#686B78]">
          No operational events recorded for this order yet.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)]">
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#F4F5F7]">
        <div>
          <h3 className="text-base font-bold text-[#282C3F]">Order Progress & Activity Timeline</h3>
          <p className="text-xs text-[#686B78] mt-0.5">
            Chronological log of restaurant preparation, courier transit, and support actions
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
          {events.length} Milestones Recorded
        </span>
      </div>

      <div className="relative pl-4 space-y-6 before:absolute before:left-[19px] before:top-3 before:bottom-3 before:w-0.5 before:bg-[#E9ECEE]">
        {events.map((ev, idx) => {
          const isExpanded = expandedIndex === idx;
          const isLast = idx === events.length - 1;
          const config = getEventConfig(ev.event_type, isLast);
          const ts = formatTimestamp(ev.event_timestamp);
          const meta = (ev.metadata || (ev as any).event_metadata || {}) as Record<string, any>;
          const hasMeta = meta && Object.keys(meta).length > 0;
          const isObserved = ev.data_source === 'PUBLIC_HISTORICAL';
          const isDemo = ev.data_source === 'SYNTHETIC';

          return (
            <div key={ev.id || idx} className="relative flex items-start gap-4">
              {/* Timeline Node Icon */}
              <div
                className={`relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm ${config.nodeBg}`}
              >
                {config.icon}
              </div>

              {/* Event Content Card */}
              <div className="flex-1 bg-[#FBFBFC] hover:bg-[#F8F9FA] transition-colors rounded-xl border border-[#E9ECEE] p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-[#282C3F]">
                      {getEventFriendlyTitle(ev.event_type)}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${config.badgeBg} ${config.badgeText} ${config.badgeBorder}`}
                    >
                      {isDemo ? 'Demo Event' : isObserved ? 'Historical Record' : 'Live Event'}
                    </span>
                  </div>

                  <div className="text-xs text-[#686B78] flex items-center gap-1.5 font-medium">
                    <Clock className="w-3.5 h-3.5 text-[#93959F]" />
                    <span>{ts.time}</span>
                    <span className="text-[#D1D5DB]">•</span>
                    <span>{ts.date}</span>
                  </div>
                </div>

                {/* Event Highlights from Metadata */}
                {hasMeta && (
                  <div className="mt-2.5 pt-2.5 border-t border-[#ECEEEF]">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                      {meta.delay_minutes !== undefined && (
                        <div className="text-[#D97706] font-medium bg-[#FFF8E6] px-2 py-1 rounded border border-[#FDE68A]">
                          Extra Delay: +{meta.delay_minutes} mins
                        </div>
                      )}
                      {meta.reason && (
                        <div className="text-[#686B78] bg-white px-2 py-1 rounded border border-[#E9ECEE]">
                          Observation: <span className="text-[#282C3F] font-semibold">{meta.reason}</span>
                        </div>
                      )}
                      {meta.rider_name && (
                        <div className="text-[#686B78] bg-white px-2 py-1 rounded border border-[#E9ECEE]">
                          Delivery Partner: <span className="text-[#282C3F] font-semibold">{meta.rider_name}</span>
                        </div>
                      )}
                      {meta.resolution && (
                        <div className="text-[#60B246] font-medium bg-[#EDF7EC] px-2 py-1 rounded border border-[#C8E6C9]">
                          Outcome: {meta.resolution}
                        </div>
                      )}
                      {meta.note && (
                        <div className="text-[#686B78] col-span-full italic bg-white px-2.5 py-1.5 rounded border border-[#E9ECEE]">
                          &ldquo;{meta.note}&rdquo;
                        </div>
                      )}
                      {meta.cuisine && (
                        <div className="text-[#686B78] bg-white px-2 py-1 rounded border border-[#E9ECEE]">
                          Cuisine: <span className="text-[#282C3F] font-semibold">{meta.cuisine}</span>
                        </div>
                      )}
                      {meta.payment_mode && (
                        <div className="text-[#686B78] bg-white px-2 py-1 rounded border border-[#E9ECEE]">
                          Payment: <span className="text-[#282C3F] font-semibold">{meta.payment_mode}</span>
                        </div>
                      )}
                    </div>

                    {/* Expandable Technical Metadata */}
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                      className="mt-2 text-[11px] font-semibold text-[#FC8019] hover:text-[#E27315] flex items-center gap-1"
                    >
                      <span>{isExpanded ? 'Hide Raw Details' : 'View Raw Details'}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>

                    {isExpanded && (
                      <pre className="mt-2 p-3 bg-white border border-[#E9ECEE] rounded-lg text-[11px] font-mono text-[#282C3F] overflow-x-auto">
                        {JSON.stringify(meta, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
