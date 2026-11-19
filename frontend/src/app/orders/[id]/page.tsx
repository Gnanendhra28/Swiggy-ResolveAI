'use client';

import React, { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Clock,
  Store,
  Truck,
  User,
  AlertCircle,
  RefreshCw,
  PlusCircle,
  CheckCircle2,
  Phone,
  MapPin,
  Sparkles,
  HelpCircle,
  ShieldCheck,
  ChevronRight,
  Info,
} from 'lucide-react';
import {
  fetchOrderById,
  injectOrderEvent,
  fetchLatestOrderInvestigation,
  fetchRecommendations,
} from '@/lib/api';
import { OrderDetail, InvestigationResponse, RecommendationResponse } from '@/lib/types';
import { OrderStatusBadge } from '@/components/OrderStatusBadge';
import { EventTimeline } from '@/components/EventTimeline';
import { formatDataSource, getOrderOperationalStory } from '@/lib/presentation';

function OrderDetailInner() {
  const params = useParams();
  const orderId = params?.id as string;

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Dynamic Event Injection Form state
  const [injectEventType, setInjectEventType] = useState<string>('CUSTOMER_SUPPORT_INQUIRY');
  const [injectNote, setInjectNote] = useState<string>('Customer contacted care regarding delivery ETA.');
  const [injecting, setInjecting] = useState<boolean>(false);
  const [injectSuccess, setInjectSuccess] = useState<string | null>(null);

  const loadOrderDetail = async () => {
    if (!orderId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOrderById(orderId);
      setOrder(data);

      // Attempt to load associated investigation and recommendations
      try {
        const [inv, recs] = await Promise.all([
          fetchLatestOrderInvestigation(orderId).catch(() => null),
          fetchRecommendations({ order_id: orderId }).catch(() => []),
        ]);
        setInvestigation(inv);
        setRecommendations(recs);
      } catch {
        // Non-fatal if no investigation exists yet
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load order details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrderDetail();
  }, [orderId]);

  const handleInjectEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setInjecting(true);
    setInjectSuccess(null);
    try {
      await injectOrderEvent({
        order_id: order.id,
        event_type: injectEventType,
        metadata: {
          note: injectNote,
          injected_by: 'OPERATOR_CONSOLE',
          timestamp: new Date().toISOString(),
        },
        data_source: 'SYNTHETIC',
      });
      setInjectSuccess(`Event '${injectEventType.replace(/_/g, ' ')}' added to timeline!`);
      await loadOrderDetail();
    } catch (err: any) {
      alert(`Failed to add event: ${err.message}`);
    } finally {
      setInjecting(false);
    }
  };

  const formatTimestamp = (isoString?: string): { time: string; date: string } => {
    if (!isoString) return { time: '—', date: '' };
    try {
      const d = new Date(isoString);
      return {
        time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        date: d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }),
      };
    } catch {
      return { time: isoString, date: '' };
    }
  };

  if (loading && !order) {
    return (
      <div className="py-24 text-center">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#FC8019] mb-3" />
        <p className="text-sm font-semibold text-[#282C3F]">Loading order details...</p>
        <p className="text-xs text-[#686B78] mt-1">Retrieving restaurant preparation, courier assignment, and timeline</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="py-16 text-center space-y-4 max-w-md mx-auto">
        <div className="w-12 h-12 rounded-2xl bg-[#FDF0F1] border border-[#FECDD3] flex items-center justify-center mx-auto text-[#E23744]">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-[#282C3F]">Order Not Found</h2>
        <p className="text-xs text-[#686B78]">{error || 'Unable to retrieve order details from the database.'}</p>
        <Link
          href="/orders"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#FC8019] text-white hover:bg-[#E27315] shadow-sm transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to All Orders</span>
        </Link>
      </div>
    );
  }

  const promised = formatTimestamp(order.promised_delivery_at);
  const created = formatTimestamp(order.created_at);
  const sourceMeta = formatDataSource(order.data_source);
  const story = getOrderOperationalStory(order, investigation, recommendations);

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div className="flex items-center gap-3">
          <Link
            href="/orders"
            className="p-2 rounded-xl bg-white border border-[#E9ECEE] text-[#686B78] hover:text-[#282C3F] hover:bg-[#F8F9FA] transition-colors shadow-sm"
            aria-label="Back to orders"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-black text-[#282C3F] font-mono tracking-tight">
                {order.external_order_id}
              </h1>
              <OrderStatusBadge
                status={order.order_status}
                isDelayed={order.is_delayed}
              />
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sourceMeta.badgeClass}`}
                title={sourceMeta.description}
              >
                {sourceMeta.label}
              </span>
            </div>
            <p className="text-xs text-[#686B78] mt-0.5">
              Placed on {created.date} at {created.time}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href={`/intelligence?order=${order.id}`}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-[#FC8019] text-white hover:bg-[#E27315] shadow-sm shadow-orange-500/20 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Open AI Insights</span>
          </Link>

          <button
            onClick={loadOrderDetail}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white text-[#282C3F] border border-[#E9ECEE] hover:bg-[#F8F9FA] transition-colors shadow-sm"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-[#686B78] ${
                loading ? 'animate-spin text-[#FC8019]' : ''
              }`}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Delay Alert Banner (if delayed or escalated) */}
      {order.is_delayed && (
        <div className="rounded-2xl border border-[#FDE68A] bg-[#FFF8E6] p-4 text-[#D97706] text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-[#D97706]" />
            <div>
              <span className="font-bold">Delivery Delay Notice:</span> This order is taking longer than expected and has exceeded its promised delivery target ({promised.time}).
            </div>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#FEF3C7] border border-[#FDE68A]">
            Delay Action Needed
          </span>
        </div>
      )}

      {/* 5 Core Questions Operational Story Card */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F4F5F7] pb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#FFF5ED] text-[#FC8019] flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#282C3F]">Order Understanding & Quick Summary</h2>
              <p className="text-xs text-[#686B78]">Clear answers for operations leads and restaurant partners</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              5-Point Summary
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {/* Question 1: What happened? */}
          <div className="p-4 rounded-xl bg-[#FBFBFC] border border-[#E9ECEE] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#FC8019] tracking-wider flex items-center gap-1">
              <span>1. Current Situation</span>
            </div>
            <div className="font-bold text-sm text-[#282C3F]">What happened?</div>
            <p className="text-[#686B78] leading-relaxed pt-1">{story.whatHappened}</p>
          </div>

          {/* Question 2: Why might it have happened? */}
          <div className="p-4 rounded-xl bg-[#FBFBFC] border border-[#E9ECEE] space-y-1">
            <div className="text-[10px] uppercase font-bold text-blue-600 tracking-wider flex items-center gap-1">
              <span>2. Underlying Cause</span>
            </div>
            <div className="font-bold text-sm text-[#282C3F]">Why might it have happened?</div>
            <p className="text-[#686B78] leading-relaxed pt-1">{story.whyItHappened}</p>
          </div>

          {/* Question 3: What could happen next? */}
          <div className="p-4 rounded-xl bg-[#FBFBFC] border border-[#E9ECEE] space-y-1">
            <div className="text-[10px] uppercase font-bold text-purple-600 tracking-wider flex items-center gap-1">
              <span>3. AI Forecast</span>
            </div>
            <div className="font-bold text-sm text-[#282C3F]">What could happen next?</div>
            <p className="text-[#686B78] leading-relaxed pt-1">{story.whatCouldHappen}</p>
            <p className="text-[10px] text-[#93959F] italic pt-1 leading-tight">{story.confidenceNote}</p>
          </div>

          {/* Question 4: What action is recommended? */}
          <div className="p-4 rounded-xl bg-[#FBFBFC] border border-[#E9ECEE] space-y-1 md:col-span-2">
            <div className="text-[10px] uppercase font-bold text-[#60B246] tracking-wider flex items-center gap-1">
              <span>4. Suggested Action</span>
            </div>
            <div className="font-bold text-sm text-[#282C3F]">What action is recommended?</div>
            <p className="text-[#282C3F] font-semibold leading-relaxed pt-1">{story.recommendedAction}</p>
          </div>

          {/* Question 5: Does it require manager approval? */}
          <div className="p-4 rounded-xl bg-[#FBFBFC] border border-[#E9ECEE] space-y-1">
            <div className="text-[10px] uppercase font-bold text-amber-600 tracking-wider flex items-center gap-1">
              <span>5. Manager Review</span>
            </div>
            <div className="font-bold text-sm text-[#282C3F]">Requires approval?</div>
            <div className="pt-1">
              <span
                className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                  story.requiresManagerApproval
                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                    : 'bg-[#EDF7EC] text-[#2E7D32] border border-[#C8E6C9]'
                }`}
              >
                {story.requiresManagerApproval ? 'Yes — Requires Manager Approval' : 'No — Pre-Approved'}
              </span>
              <p className="text-[11px] text-[#686B78] mt-1">{story.approvalDetail}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Information Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Restaurant Partner */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5 text-[#FC8019]" />
              Restaurant Partner
            </span>
            {order.restaurant?.rating ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#60B246] text-white text-[11px] font-bold">
                ★ {order.restaurant.rating}
              </span>
            ) : (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#F4F5F7] text-[#686B78]">
                {sourceMeta.shortLabel}
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.restaurant?.name || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Historical Partner' : 'Restaurant Partner')}
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5">
              {order.restaurant?.cuisine || 'Food & Dining'}
            </p>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78] flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-[#93959F] flex-shrink-0" />
            <span className="truncate">
              {order.restaurant?.area && order.restaurant?.city
                ? `${order.restaurant.area}, ${order.restaurant.city}`
                : 'Bengaluru'}
            </span>
          </div>
        </div>

        {/* Card 2: Customer Profile */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-[#FC8019]" />
              Customer
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#F4F5F7] text-[#686B78]">
              {order.data_source === 'PUBLIC_HISTORICAL' ? 'Archived Customer' : 'Verified'}
            </span>
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.customer?.name || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Customer Name' : 'Customer Name')}
            </h3>
            <div className="text-xs text-[#686B78] mt-1 flex items-center gap-1.5">
              <Phone className="w-3 h-3 text-[#93959F]" />
              <span>
                {order.customer?.phone && order.customer?.phone !== 'N/A'
                  ? order.customer.phone
                  : '+91 98765 43210'}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78] flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-[#93959F] flex-shrink-0" />
            <span className="truncate">Delivery Doorstep Address</span>
          </div>
        </div>

        {/* Card 3: Delivery Partner / Courier */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Truck className="w-3.5 h-3.5 text-[#FC8019]" />
              Delivery Partner
            </span>
            {order.delivery_partner ? (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#EDF7EC] text-[#60B246] border border-[#C8E6C9]">
                Assigned
              </span>
            ) : (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#FFF8E6] text-[#D97706] border border-[#FDE68A]">
                Searching
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.delivery_partner?.name || 'Searching for partner...'}
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5 font-mono">
              {order.delivery_partner?.external_rider_id
                ? `Rider ID: ${order.delivery_partner.external_rider_id}`
                : 'Nearest courier will be assigned'}
            </p>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78]">
            Status:{' '}
            <span className="font-semibold text-[#282C3F]">
              {order.delivery_partner?.availability_status === 'AVAILABLE'
                ? 'On the move'
                : (order.delivery_partner?.availability_status || 'Dispatching')}
            </span>
          </div>
        </div>

        {/* Card 4: Financials & Promised SLA */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#FC8019]" />
              Delivery Promise
            </span>
            <span className="text-xs font-bold text-[#FC8019] bg-[#FFF5ED] px-2 py-0.5 rounded-full border border-[#FED7AA]">
              ₹{order.order_value}
            </span>
          </div>

          <div>
            <div className="text-xs text-[#686B78] font-medium">Promised Delivery Time:</div>
            <div className="text-lg font-black text-[#282C3F] mt-0.5">
              {promised.time}
            </div>
            <div className="text-[11px] text-[#93959F]">{promised.date}</div>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-[11px] text-[#686B78]">
            Recorded milestones: <strong className="text-[#282C3F]">{order.events?.length ?? 0} updates</strong>
          </div>
        </div>
      </div>

      {/* Main Order Timeline Component */}
      <EventTimeline events={order.events || []} />

      {/* Runtime Event Injection Console (Testing Console) */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#F4F5F7]">
          <div>
            <h3 className="text-base font-bold text-[#282C3F] flex items-center gap-2">
              <PlusCircle className="w-4 h-4 text-[#FC8019]" />
              Simulate Order Event (Testing Console)
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5">
              Test how ResolveAI responds to real-world disruptions (like heavy rain, road traffic, or kitchen delays)
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#F4F5F7] text-[#686B78]">
            Interactive Test
          </span>
        </div>

        {injectSuccess && (
          <div className="rounded-xl border border-[#C8E6C9] bg-[#EDF7EC] p-3 text-[#2E7D32] text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{injectSuccess}</span>
          </div>
        )}

        <form onSubmit={handleInjectEvent} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#282C3F] mb-1.5 uppercase tracking-wider">
                Event to Simulate
              </label>
              <select
                value={injectEventType}
                onChange={(e) => setInjectEventType(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#F8F9FA] focus:bg-white text-xs font-semibold text-[#282C3F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
              >
                <option value="CUSTOMER_SUPPORT_INQUIRY">Customer Inquired with Support</option>
                <option value="TRAFFIC_CONGESTION_DETECTED">Heavy Road Traffic Encountered</option>
                <option value="KITCHEN_DELAY_DETECTED">Kitchen Order Backlog / Extra Prep Time</option>
                <option value="RIDER_VEHICLE_BREAKDOWN">Delivery Partner Vehicle Issue</option>
                <option value="RIDER_REASSIGNED">Delivery Partner Reassigned</option>
                <option value="WALLET_CREDIT_ISSUED">Apology Credit Voucher Issued</option>
                <option value="ORDER_DELIVERED">Order Delivered Successfully</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#282C3F] mb-1.5 uppercase tracking-wider">
                Event Note & Context
              </label>
              <input
                type="text"
                value={injectNote}
                onChange={(e) => setInjectNote(e.target.value)}
                placeholder="Describe operational detail..."
                className="w-full px-3.5 py-2.5 bg-[#F8F9FA] focus:bg-white text-xs text-[#282C3F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={injecting}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-[#FC8019] hover:bg-[#E27315] text-white shadow-sm shadow-orange-500/20 hover:shadow transition-all disabled:opacity-50"
            >
              {injecting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Adding Event...</span>
                </>
              ) : (
                <>
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Add Test Event</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function OrderDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="py-24 text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#FC8019] mb-3" />
          <p className="text-sm font-semibold text-[#282C3F]">Loading order...</p>
        </div>
      }
    >
      <OrderDetailInner />
    </Suspense>
  );
}
