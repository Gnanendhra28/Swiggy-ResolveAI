'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
  AlertCircle,
  Clock,
  Layers,
  MapPin,
  ShoppingBag,
  User,
  Truck,
  Store,
} from 'lucide-react';
import { fetchOrders } from '@/lib/api';
import { OrderSummary, PaginatedOrders } from '@/lib/types';
import { OrderStatusBadge } from '@/components/OrderStatusBadge';

export default function OrdersManagementPage() {
  const [data, setData] = useState<PaginatedOrders | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(12);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [dataSourceFilter, setDataSourceFilter] = useState<string>('');

  const loadOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchOrders({
        page,
        limit,
        status: statusFilter || undefined,
        data_source: dataSourceFilter || undefined,
        search: search || undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch orders.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, [page, statusFilter, dataSourceFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadOrders();
  };

  const resetFilters = () => {
    setSearch('');
    setStatusFilter('');
    setDataSourceFilter('');
    setPage(1);
  };

  const formatDateTime = (isoString?: string): { time: string; date: string } => {
    if (!isoString) return { time: '—', date: '' };
    try {
      const d = new Date(isoString);
      return {
        time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        date: d.toLocaleDateString([], { month: 'short', day: 'numeric' }),
      };
    } catch {
      return { time: isoString, date: '' };
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FC8019]" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              Orders Management
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            Active order telemetry, restaurant fulfillment, rider assignment, and delivery SLA status.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadOrders}
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

      {/* Filter and Search Bar Card */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] p-4 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-3 sm:space-y-0 sm:flex sm:items-center sm:justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md relative">
          <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-[#93959F]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by order ID, restaurant, customer, city..."
            className="w-full pl-9 pr-4 py-2 bg-[#F8F9FA] hover:bg-[#F4F5F7] focus:bg-white text-xs text-[#282C3F] placeholder-[#93959F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019] focus:ring-1 focus:ring-[#FC8019] transition-all"
          />
        </form>

        {/* Dropdown Filters */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-[#F8F9FA] text-xs font-semibold text-[#282C3F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
          >
            <option value="">All Statuses</option>
            <option value="PLACED">Placed</option>
            <option value="PREPARING">Preparing</option>
            <option value="OUT_FOR_DELIVERY">Out For Delivery</option>
            <option value="DELIVERED">Delivered</option>
            <option value="RECOVERED">Recovered</option>
            <option value="ESCALATED">Escalated</option>
          </select>

          {/* Data Source Filter */}
          <select
            value={dataSourceFilter}
            onChange={(e) => {
              setDataSourceFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-[#F8F9FA] text-xs font-semibold text-[#282C3F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
          >
            <option value="">All Sources</option>
            <option value="SYNTHETIC">Synthetic Live</option>
            <option value="PUBLIC_HISTORICAL">Public Historical</option>
          </select>

          {(search || statusFilter || dataSourceFilter) && (
            <button
              onClick={resetFilters}
              className="text-xs font-bold text-[#FC8019] hover:underline px-2 py-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-2xl border border-[#FECDD3] bg-[#FDF0F1] p-4 text-[#E23744] text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadOrders}
            className="underline font-bold text-[#E23744]"
          >
            Retry
          </button>
        </div>
      )}

      {/* Orders Data Table Card */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] shadow-[0_2px_8px_rgba(40,44,63,0.04)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#FBFBFC] text-[#686B78] font-bold border-b border-[#E9ECEE] uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Order ID</th>
                <th className="py-3 px-4">Restaurant</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Delivery Partner</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Promised SLA</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F5F7]">
              {loading && !data ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#93959F]">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#FC8019] mb-2" />
                    <span>Loading orders telemetry...</span>
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#93959F]">
                    <ShoppingBag className="w-8 h-8 text-[#D1D5DB] mx-auto mb-2" />
                    <p className="font-semibold text-sm text-[#686B78]">No orders found</p>
                    <p className="text-xs text-[#93959F] mt-1">
                      Try adjusting your search criteria or launch a simulation.
                    </p>
                  </td>
                </tr>
              ) : (
                data.items.map((ord) => {
                  const promised = formatDateTime(ord.promised_delivery_at);

                  return (
                    <tr
                      key={ord.id}
                      className="hover:bg-[#FFFDFB] transition-colors"
                    >
                      {/* Order ID */}
                      <td className="py-3.5 px-4 font-mono font-bold text-[#FC8019]">
                        <Link
                          href={`/orders/${ord.id}`}
                          className="hover:underline flex items-center gap-1.5"
                        >
                          <span>{ord.external_order_id}</span>
                        </Link>
                      </td>

                      {/* Restaurant */}
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-[#282C3F]">
                          {ord.restaurant_name || (ord.data_source === 'PUBLIC_HISTORICAL' ? 'Restaurant unavailable in source dataset' : 'Restaurant Partner')}
                        </div>
                        <div className="text-[11px] text-[#93959F]">
                          {ord.restaurant_city || (ord.data_source === 'PUBLIC_HISTORICAL' ? 'Location not captured in dataset' : 'Bengaluru')}
                        </div>
                      </td>

                      {/* Customer */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-[#282C3F] flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-[#93959F]" />
                          <span>{ord.customer_name || (ord.data_source === 'PUBLIC_HISTORICAL' ? 'Customer unassigned in dataset' : 'Customer')}</span>
                        </div>
                      </td>

                      {/* Delivery Partner */}
                      <td className="py-3.5 px-4">
                        {ord.delivery_partner_name ? (
                          <div className="flex items-center gap-1.5 text-[#282C3F] font-semibold">
                            <Truck className="w-3.5 h-3.5 text-[#FC8019]" />
                            <span>{ord.delivery_partner_name}</span>
                          </div>
                        ) : (
                          <span className="text-[#93959F] italic text-[11px]">
                            {ord.data_source === 'PUBLIC_HISTORICAL' ? 'Courier ID in telemetry' : 'Pending Assignment'}
                          </span>
                        )}
                      </td>

                      {/* Order Status */}
                      <td className="py-3.5 px-4">
                        <OrderStatusBadge
                          status={ord.order_status}
                          isDelayed={ord.is_delayed}
                        />
                      </td>

                      {/* Promised Delivery Time */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-[#282C3F]">
                          {promised.time}
                        </div>
                        <div className="text-[11px] text-[#93959F]">
                          {promised.date}
                        </div>
                      </td>

                      {/* Data Provenance */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            ord.data_source === 'PUBLIC_HISTORICAL'
                              ? 'bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]'
                              : 'bg-[#F4F5F7] text-[#686B78] border border-[#E2E5E8]'
                          }`}
                        >
                          {ord.data_source}
                        </span>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/orders/${ord.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold text-[#FC8019] bg-[#FFF5ED] hover:bg-[#FFEADA] border border-[#FED7AA] transition-colors shadow-sm"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {data && data.total_pages > 1 && (
          <div className="p-4 border-t border-[#F4F5F7] bg-[#FBFBFC] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#686B78]">
            <div>
              Showing <span className="font-bold text-[#282C3F]">{data.items.length}</span> of{' '}
              <span className="font-bold text-[#282C3F]">{data.total}</span> orders
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page <= 1 || loading}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-[#E9ECEE] text-[#282C3F] hover:bg-[#F4F5F7] disabled:opacity-40 font-semibold transition-colors shadow-sm"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous</span>
              </button>

              <span className="px-3 py-1.5 font-bold text-[#282C3F]">
                Page {page} of {data.total_pages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(p + 1, data.total_pages))}
                disabled={page >= data.total_pages || loading}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-[#E9ECEE] text-[#282C3F] hover:bg-[#F4F5F7] disabled:opacity-40 font-semibold transition-colors shadow-sm"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
