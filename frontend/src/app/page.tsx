'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Package,
  Clock,
  CheckCircle2,
  AlertTriangle,
  PlayCircle,
  ArrowRight,
  RefreshCw,
  TrendingUp,
  MapPin,
  Flame,
  Store,
  Truck,
  Layers,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { fetchMetrics, fetchOrders } from '@/lib/api';
import { DashboardMetrics, OrderSummary } from '@/lib/types';
import { StatCard } from '@/components/StatCard';
import { OrderStatusBadge } from '@/components/OrderStatusBadge';

export default function OperationsDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, ords] = await Promise.all([
        fetchMetrics(),
        fetchOrders({ limit: 6 }),
      ]);
      setMetrics(m);
      setRecentOrders(ords.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to ResolveAI backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 12000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Operations Dashboard Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FC8019]" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              Operations Intelligence Dashboard
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            Real-time proactive monitoring, delivery anomaly detection, and autonomous recovery telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadData}
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

          <Link
            href="/simulation"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#FC8019] hover:bg-[#E27315] text-white transition-all shadow-sm shadow-orange-500/20 hover:shadow"
          >
            <PlayCircle className="w-4 h-4" />
            <span>Launch Simulation</span>
          </Link>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-2xl border border-[#FECDD3] bg-[#FDF0F1] p-4 text-[#E23744] text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadData}
            className="underline font-bold text-[#E23744] hover:text-[#991B1B]"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Orders"
          value={loading && !metrics ? '...' : metrics?.total_orders ?? 0}
          subtitle="All runtime and historical orders"
          icon={Package}
          variant="primary"
        />
        <StatCard
          title="Active Orders"
          value={loading && !metrics ? '...' : metrics?.active_orders ?? 0}
          subtitle="In preparation or out for delivery"
          icon={Clock}
          variant="default"
        />
        <StatCard
          title="Delivered Successfully"
          value={loading && !metrics ? '...' : metrics?.delivered_orders ?? 0}
          subtitle="Fulfilled within operational SLA"
          icon={CheckCircle2}
          variant="success"
        />
        <StatCard
          title="Delayed / Escalated"
          value={loading && !metrics ? '...' : metrics?.delayed_orders ?? 0}
          subtitle="Breached SLA or escalated to support"
          icon={AlertTriangle}
          variant="danger"
        />
      </div>

      {/* Main Grid: Orders & Status Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Recent Orders Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-[#E9ECEE] shadow-[0_2px_8px_rgba(40,44,63,0.04)] overflow-hidden">
            <div className="p-5 border-b border-[#F4F5F7] flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-[#282C3F]">Recent Orders</h2>
                <p className="text-xs text-[#686B78] mt-0.5">
                  Latest active and completed orders requiring intelligence oversight
                </p>
              </div>
              <Link
                href="/orders"
                className="text-xs font-bold text-[#FC8019] hover:text-[#E27315] flex items-center gap-1 transition-colors"
              >
                <span>View All Orders</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* Orders Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-[#FBFBFC] text-[#686B78] font-bold border-b border-[#E9ECEE] uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Order ID</th>
                    <th className="py-3 px-4">Restaurant</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Promised Delivery</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F4F5F7]">
                  {recentOrders.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-[#93959F]">
                        {loading ? 'Loading orders...' : 'No orders found. Launch a simulation to create test orders.'}
                      </td>
                    </tr>
                  ) : (
                    recentOrders.map((ord) => (
                      <tr
                        key={ord.id}
                        className="hover:bg-[#FFFDFB] transition-colors"
                      >
                        <td className="py-3.5 px-4 font-mono font-bold text-[#FC8019]">
                          <Link
                            href={`/orders/${ord.id}`}
                            className="hover:underline"
                          >
                            {ord.external_order_id}
                          </Link>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-[#282C3F]">
                            {ord.restaurant_name || (ord.data_source === 'PUBLIC_HISTORICAL' ? 'Restaurant unavailable in source dataset' : 'Restaurant Partner')}
                          </div>
                          <div className="text-[11px] text-[#93959F]">
                            {ord.restaurant_city || (ord.data_source === 'PUBLIC_HISTORICAL' ? 'Location not captured in dataset' : 'Bengaluru')}
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <OrderStatusBadge
                            status={ord.order_status}
                            isDelayed={ord.is_delayed}
                          />
                        </td>
                        <td className="py-3.5 px-4 text-[#686B78] font-medium">
                          {formatTime(ord.promised_delivery_at)}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <Link
                            href={`/orders/${ord.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold text-[#FC8019] bg-[#FFF5ED] hover:bg-[#FFEADA] border border-[#FED7AA] transition-colors"
                          >
                            <span>Inspect</span>
                            <ChevronRight className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Operational Events Stream */}
          <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)]">
            <div className="flex items-center justify-between pb-4 border-b border-[#F4F5F7]">
              <div>
                <h2 className="text-base font-bold text-[#282C3F]">
                  Recent Operational Events
                </h2>
                <p className="text-xs text-[#686B78] mt-0.5">
                  Live anomaly alerts, dispatch updates, and autonomous recovery events
                </p>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
                {metrics?.recent_activity?.length ?? 0} events
              </span>
            </div>

            <div className="divide-y divide-[#F4F5F7] mt-2">
              {!metrics?.recent_activity || metrics.recent_activity.length === 0 ? (
                <div className="py-8 text-center text-xs text-[#93959F]">
                  No operational events recorded yet. Run a scenario from the Simulation Center.
                </div>
              ) : (
                metrics.recent_activity.slice(0, 5).map((act) => {
                  const isDelay = act.event_type.includes('DELAY') || act.event_type.includes('TIMEOUT');
                  const isSuccess = act.event_type.includes('DELIVERED') || act.event_type.includes('SUCCESSFUL');
                  const isRecovery = act.event_type.includes('RECOVERY') || act.event_type.includes('REASSIGNED');

                  return (
                    <div
                      key={act.id}
                      className="py-3.5 flex items-start justify-between gap-3 hover:bg-[#FFFDFB] px-2 rounded-xl transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                            isDelay
                              ? 'bg-[#FFF8E6] text-[#D97706]'
                              : isSuccess
                              ? 'bg-[#EDF7EC] text-[#60B246]'
                              : isRecovery
                              ? 'bg-[#FFF5ED] text-[#FC8019]'
                              : 'bg-[#F4F5F7] text-[#686B78]'
                          }`}
                        >
                          {isDelay ? (
                            <ShieldAlert className="w-4 h-4" />
                          ) : isSuccess ? (
                            <CheckCircle2 className="w-4 h-4" />
                          ) : (
                            <Store className="w-4 h-4" />
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[#282C3F]">
                              {act.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-[#F4F5F7] text-[#686B78]">
                              {act.data_source}
                            </span>
                          </div>

                          <div className="text-[11px] text-[#686B78] mt-0.5 flex items-center gap-1.5">
                            <Link
                              href={`/orders/${act.order_id}`}
                              className="font-mono text-[#FC8019] hover:underline font-bold"
                            >
                              {act.external_order_id}
                            </Link>
                            <span>•</span>
                            <span>{act.restaurant_name}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-[11px] font-medium text-[#93959F] flex-shrink-0">
                        {formatTime(act.event_timestamp)}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Order Status Distribution & Scenario Shortcuts */}
        <div className="space-y-6">
          {/* Status Distribution Breakdown */}
          <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)]">
            <h2 className="text-base font-bold text-[#282C3F]">Status Distribution</h2>
            <p className="text-xs text-[#686B78] mt-0.5">
              Breakdown across fulfillment stages
            </p>

            <div className="mt-5 space-y-4">
              {metrics && metrics.status_distribution && Object.keys(metrics.status_distribution).length > 0 ? (
                Object.entries(metrics.status_distribution).map(([status, count]) => {
                  const total = metrics.total_orders || 1;
                  const pct = Math.round((count / total) * 100);

                  const getBarColor = (st: string) => {
                    const s = st.toUpperCase();
                    if (s === 'DELIVERED') return 'bg-[#60B246]';
                    if (s === 'RECOVERED') return 'bg-[#2E7D32]';
                    if (s === 'OUT_FOR_DELIVERY') return 'bg-[#FC8019]';
                    if (s === 'ESCALATED' || s === 'CANCELLED') return 'bg-[#E23744]';
                    return 'bg-[#FC8019]/70';
                  };

                  return (
                    <div key={status} className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-[#282C3F]">
                          {status.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[#686B78] font-bold">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-[#F4F5F7] overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${getBarColor(status)}`}
                          style={{ width: `${Math.max(pct, 3)}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="py-8 text-center text-xs text-[#93959F]">
                  No status data available yet.
                </div>
              )}
            </div>
          </div>

          {/* Swiggy Proactive Recovery Intelligence Spotlight */}
          <div className="bg-gradient-to-br from-[#FFF5ED] to-white rounded-2xl border border-[#FED7AA] p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-[#FC8019] flex items-center justify-center text-white shadow-sm">
                <Flame className="w-4 h-4 fill-current" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#282C3F]">
                  Autonomous Recovery
                </h3>
                <span className="text-[10px] font-bold text-[#FC8019] uppercase tracking-wider">
                  Swiggy Operational Intelligence
                </span>
              </div>
            </div>

            <p className="text-xs text-[#686B78] leading-relaxed">
              ResolveAI predicts delay risks before customers notice, coordinating express dispatch, rider reassignment, and proactive customer updates.
            </p>

            <div className="pt-2">
              <Link
                href="/simulation"
                className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl bg-[#FC8019] hover:bg-[#E27315] text-white text-xs font-bold transition-all shadow-sm shadow-orange-500/20"
              >
                <span>Simulate Delay & Recovery</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
