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
  DollarSign,
  Calendar,
  Layers,
  MapPin,
  Tag,
  Star,
  CheckCircle2,
  Phone,
  Flame,
  ShieldCheck,
} from 'lucide-react';
import { fetchOrderById, injectOrderEvent } from '@/lib/api';
import { OrderDetail } from '@/lib/types';
import { OrderStatusBadge } from '@/components/OrderStatusBadge';
import { EventTimeline } from '@/components/EventTimeline';

function OrderDetailInner() {
  const params = useParams();
  const orderId = params?.id as string;

  const [order, setOrder] = useState<OrderDetail | null>(null);
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
      setInjectSuccess(`Event '${injectEventType}' injected into timeline!`);
      await loadOrderDetail();
    } catch (err: any) {
      alert(`Failed to inject event: ${err.message}`);
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
        <p className="text-sm font-semibold text-[#282C3F]">Loading order telemetry...</p>
        <p className="text-xs text-[#686B78] mt-1">Retrieving merchant, courier and chronological events</p>
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
          <span>Back to Orders List</span>
        </Link>
      </div>
    );
  }

  const promised = formatTimestamp(order.promised_delivery_at);
  const created = formatTimestamp(order.created_at);

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
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-[#282C3F] font-mono tracking-tight">
                {order.external_order_id}
              </h1>
              <OrderStatusBadge
                status={order.order_status}
                isDelayed={order.is_delayed}
              />
            </div>
            <p className="text-xs text-[#686B78] mt-0.5">
              Placed {created.date} at {created.time} • Source:{' '}
              <span className="font-bold text-[#282C3F]">{order.data_source}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadOrderDetail}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white text-[#282C3F] border border-[#E9ECEE] hover:bg-[#F8F9FA] transition-colors shadow-sm"
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
              <span className="font-bold">Delivery Delay Alert:</span> This order has encountered operational delay exceeding the promised customer SLA ({promised.time}).
            </div>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#FEF3C7] border border-[#FDE68A]">
            SLA Risk
          </span>
        </div>
      )}

      {/* 4 Information Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Restaurant Partner */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5 text-[#FC8019]" />
              Restaurant
            </span>
            {order.restaurant?.rating ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#60B246] text-white text-[11px] font-bold">
                <Star className="w-3 h-3 fill-current" />
                {order.restaurant.rating}
              </span>
            ) : (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#F4F5F7] text-[#686B78]">
                {order.data_source === 'PUBLIC_HISTORICAL' ? 'Dataset Source' : 'Partner'}
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.restaurant?.name || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Restaurant unavailable in source dataset' : 'Restaurant Partner')}
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5">
              {order.restaurant?.cuisine || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Historical Courier Telemetry' : 'Food & Dining')}
            </p>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78] flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-[#93959F] flex-shrink-0" />
            <span className="truncate">
              {order.restaurant?.area && order.restaurant?.city
                ? `${order.restaurant.area}, ${order.restaurant.city}`
                : order.data_source === 'PUBLIC_HISTORICAL'
                ? 'Location not captured in dataset'
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
              {order.data_source === 'PUBLIC_HISTORICAL' ? 'Historical Record' : 'Verified'}
            </span>
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.customer?.name || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Customer unassigned in historical dataset' : 'Customer Name')}
            </h3>
            <div className="text-xs text-[#686B78] mt-1 flex items-center gap-1.5">
              <Phone className="w-3 h-3 text-[#93959F]" />
              <span>
                {order.customer?.phone && order.customer?.phone !== 'N/A'
                  ? order.customer.phone
                  : order.data_source === 'PUBLIC_HISTORICAL'
                  ? 'Not recorded in dataset'
                  : '+91 98765 43210'}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78] flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-[#93959F] flex-shrink-0" />
            <span className="truncate">
              {order.data_source === 'PUBLIC_HISTORICAL' ? 'Address unlinked in historical records' : 'Delivery Doorstep Address'}
            </span>
          </div>
        </div>

        {/* Card 3: Delivery Partner / Courier */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Truck className="w-3.5 h-3.5 text-[#FC8019]" />
              Delivery Fleet
            </span>
            {order.delivery_partner ? (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#EDF7EC] text-[#60B246] border border-[#C8E6C9]">
                Assigned
              </span>
            ) : (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#FFF8E6] text-[#D97706] border border-[#FDE68A]">
                Pending
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base font-bold text-[#282C3F]">
              {order.delivery_partner?.name || (order.data_source === 'PUBLIC_HISTORICAL' ? 'Courier ID in telemetry' : 'Pending Assignment')}
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5 font-mono">
              {order.delivery_partner?.external_rider_id
                ? `ID: ${order.delivery_partner.external_rider_id}`
                : 'Searching nearest courier...'}
            </p>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-xs text-[#686B78]">
            Status:{' '}
            <span className="font-semibold text-[#282C3F]">
              {order.delivery_partner?.availability_status || 'DISPATCH_IN_PROGRESS'}
            </span>
          </div>
        </div>

        {/* Card 4: Financials & Promised SLA */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#FC8019]" />
              SLA & Value
            </span>
            <span className="text-xs font-bold text-[#FC8019] bg-[#FFF5ED] px-2 py-0.5 rounded-full border border-[#FED7AA]">
              ₹{order.order_value}
            </span>
          </div>

          <div>
            <div className="text-xs text-[#686B78] font-medium">Promised Delivery ETA:</div>
            <div className="text-lg font-black text-[#282C3F] mt-0.5">
              {promised.time}
            </div>
            <div className="text-[11px] text-[#93959F]">{promised.date}</div>
          </div>

          <div className="pt-2 border-t border-[#F4F5F7] text-[11px] text-[#686B78]">
            Events count: <strong className="text-[#282C3F]">{order.events?.length ?? 0} milestones</strong>
          </div>
        </div>
      </div>

      {/* Main Order Timeline Component */}
      <EventTimeline events={order.events || []} />

      {/* Runtime Event Injection Console (Operator Override) */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#F4F5F7]">
          <div>
            <h3 className="text-base font-bold text-[#282C3F] flex items-center gap-2">
              <PlusCircle className="w-4 h-4 text-[#FC8019]" />
              Runtime Operator Event Console
            </h3>
            <p className="text-xs text-[#686B78] mt-0.5">
              Simulate live operational anomalies, customer inquiries, or emergency dispatches into this order
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#F4F5F7] text-[#686B78]">
            Operator Override
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
                Event Type
              </label>
              <select
                value={injectEventType}
                onChange={(e) => setInjectEventType(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#F8F9FA] focus:bg-white text-xs font-semibold text-[#282C3F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
              >
                <option value="CUSTOMER_SUPPORT_INQUIRY">CUSTOMER_SUPPORT_INQUIRY (Customer inquiry)</option>
                <option value="TRAFFIC_CONGESTION_DETECTED">TRAFFIC_CONGESTION_DETECTED (Route delay)</option>
                <option value="KITCHEN_DELAY_DETECTED">KITCHEN_DELAY_DETECTED (Preparation backlog)</option>
                <option value="RIDER_VEHICLE_BREAKDOWN">RIDER_VEHICLE_BREAKDOWN (Operational anomaly)</option>
                <option value="RECOVERY_TRIGGERED">RECOVERY_TRIGGERED (Emergency autonomous recovery)</option>
                <option value="RIDER_REASSIGNED">RIDER_REASSIGNED (Alternate dispatch)</option>
                <option value="WALLET_CREDIT_ISSUED">WALLET_CREDIT_ISSUED (Customer appeasement)</option>
                <option value="ORDER_DELIVERED">ORDER_DELIVERED (Final handover)</option>
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
                  <span>Injecting...</span>
                </>
              ) : (
                <>
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Inject Operational Event</span>
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
