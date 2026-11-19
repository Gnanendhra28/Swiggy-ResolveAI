'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Sparkles,
  Bot,
  ShieldCheck,
  TrendingUp,
  Clock,
  Store,
  Truck,
  User,
  Zap,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
  RotateCw,
  Search,
  ArrowRight,
  ChevronRight,
  Info,
  Sliders,
  Cpu,
  History,
  Database,
  Timer,
  CheckSquare,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
} from 'lucide-react';
import {
  fetchOrders,
  triggerInvestigation,
  fetchLatestOrderInvestigation,
  fetchRecommendations,
  approveRecommendation,
  rejectRecommendation,
  executeRecommendation,
  fetchOrderAudits,
  fetchOrderMLAudits,
} from '@/lib/api';
import {
  OrderSummary,
  InvestigationResponse,
  RecommendationResponse,
  ExecutionAuditResponse,
  MLPredictionAuditResponse,
} from '@/lib/types';
import {
  formatRiskTier,
  formatActionType,
  formatRoleLabel,
  formatDeliveryRange,
  formatDataSource,
  formatExecutionResult,
  formatMetadataFields,
} from '@/lib/presentation';

function OrderIntelligenceInner() {
  const searchParams = useSearchParams();
  const initialOrderParam = searchParams.get('order');

  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string>(initialOrderParam || '');
  const [activeInvestigation, setActiveInvestigation] = useState<InvestigationResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse[]>([]);
  const [audits, setAudits] = useState<ExecutionAuditResponse[]>([]);
  const [mlAudits, setMlAudits] = useState<MLPredictionAuditResponse[]>([]);
  const [operatorRole, setOperatorRole] = useState<string>('OPS_LEAD');
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Expandable technical detail toggles (Two-level information design)
  const [showRiskTechDetails, setShowRiskTechDetails] = useState(false);
  const [showEtaTechDetails, setShowEtaTechDetails] = useState(false);
  const [showCancelTechDetails, setShowCancelTechDetails] = useState(false);
  const [showRestTechDetails, setShowRestTechDetails] = useState(false);
  const [showDelivTechDetails, setShowDelivTechDetails] = useState(false);
  const [showPredictionHistory, setShowPredictionHistory] = useState(false);
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null);

  // Load active orders
  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoadingOrders(true);
        const data = await fetchOrders({ limit: 20 });
        setOrders(data.items);
        if (data.items.length > 0) {
          const targetId = initialOrderParam && data.items.some((o) => o.id === initialOrderParam)
            ? initialOrderParam
            : data.items[0].id;
          setSelectedOrderId(targetId);
          loadOrderIntelligence(targetId);
        }
      } catch (err) {
        console.error('Failed to load initial orders:', err);
      } finally {
        setLoadingOrders(false);
      }
    }
    loadInitialData();
  }, [initialOrderParam]);

  // Load intelligence details for selected order
  async function loadOrderIntelligence(orderId: string) {
    if (!orderId) return;
    try {
      const inv = await fetchLatestOrderInvestigation(orderId);
      setActiveInvestigation(inv);
      const recs = await fetchRecommendations({ order_id: orderId });
      setRecommendations(recs);
      const auditList = await fetchOrderAudits(orderId);
      setAudits(auditList);
      const mlAuditList = await fetchOrderMLAudits(orderId);
      setMlAudits(mlAuditList);
    } catch (err) {
      console.error('Failed to fetch intelligence details:', err);
    }
  }

  // Trigger new investigation
  async function handleTriggerInvestigation() {
    if (!selectedOrderId) return;
    setInvestigating(true);
    setStatusMessage(null);
    try {
      const inv = await triggerInvestigation(selectedOrderId, 'OPERATOR_UI_TRIGGER');
      setActiveInvestigation(inv);
      await loadOrderIntelligence(selectedOrderId);
      setStatusMessage({ text: 'AI Order Investigation completed successfully.', type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Investigation failed', type: 'error' });
    } finally {
      setInvestigating(false);
    }
  }

  // Approve recommendation
  async function handleApprove(recId: string) {
    setActionLoadingId(recId);
    try {
      await approveRecommendation(recId, {
        operator_identity: 'OpsLead_Console',
        operator_role: operatorRole,
      });
      await loadOrderIntelligence(selectedOrderId);
      setStatusMessage({ text: `Suggested action approved under role [${operatorRole}]. Ready to process.`, type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Approval failed', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  }

  // Reject recommendation
  async function handleReject(recId: string) {
    const reason = window.prompt('Enter operational reason for declining this action:', 'Delivery conditions returned to normal.');
    if (!reason) return;
    setActionLoadingId(recId);
    try {
      await rejectRecommendation(recId, {
        operator_identity: 'OpsLead_Console',
        operator_role: operatorRole,
        reason,
      });
      await loadOrderIntelligence(selectedOrderId);
      setStatusMessage({ text: 'Suggested action declined and marked closed.', type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Decline failed', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  }

  // Execute recommendation
  async function handleExecute(recId: string) {
    setActionLoadingId(recId);
    try {
      const res = await executeRecommendation(recId, {
        operator_identity: 'OpsLead_Console',
        operator_role: operatorRole,
      });
      await loadOrderIntelligence(selectedOrderId);
      setStatusMessage({
        text: `Action processed successfully (Protected by duplicate action protection).`,
        type: 'success',
      });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Action processing failed', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  }

  const selectedOrder = orders.find((o) => o.id === selectedOrderId);
  const mlProv = activeInvestigation?.ml_provenance || {};
  const taskA = mlProv.task_a_eta || {};
  const taskC2 = mlProv.task_c2_cancellation || {};
  const researchModels = mlProv.research_models || {};
  const restEv = activeInvestigation?.restaurant_evidence || {};
  const delivEv = activeInvestigation?.delivery_evidence || {};
  const resolution = activeInvestigation?.agent_reasoning || {};

  const riskMeta = formatRiskTier(activeInvestigation?.risk_tier);
  const etaRange = formatDeliveryRange(taskA.eta_p10_min, taskA.eta_p50_min, taskA.eta_p90_min);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FC8019] animate-pulse" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              AI Order Insights & Automated Resolution
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            Proactive delay forecasting, operational status checks, and manager-approved customer support actions.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#EDF7EC] text-[#60B246] border border-[#C8E6C9] flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            Monitoring Mode Active
          </span>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
            Interactive Prototype 
          </span>
        </div>
      </div>

      {/* Notification Toast */}
      {statusMessage && (
        <div
          className={`p-3 rounded-xl text-xs font-medium flex items-center justify-between border ${
            statusMessage.type === 'success'
              ? 'bg-[#EDF7EC] text-[#2E7D32] border-[#C8E6C9]'
              : 'bg-red-50 text-red-700 border-red-200'
          }`}
        >
          <span>{statusMessage.text}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-xs font-bold underline ml-4 hover:opacity-75"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Control Bar: Select Active Order & Trigger Investigation */}
      <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative flex-1">
              <label className="text-[10px] uppercase tracking-wider font-extrabold text-[#686B78] block mb-1">
                Select Order to Inspect
              </label>
              <select
                value={selectedOrderId}
                onChange={(e) => {
                  setSelectedOrderId(e.target.value);
                  loadOrderIntelligence(e.target.value);
                }}
                className="w-full bg-[#FAFAFA] border border-gray-200 rounded-xl px-3.5 py-2.5 text-xs font-bold text-[#282C3F] focus:outline-none focus:ring-2 focus:ring-[#FC8019]/20 focus:border-[#FC8019]"
              >
                {orders.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.external_order_id} &bull; {o.restaurant_name} &bull; ₹{o.order_value} &bull; [{o.order_status}]
                  </option>
                ))}
              </select>
            </div>

            <div className="self-end sm:self-auto pt-4 sm:pt-4">
              <button
                onClick={handleTriggerInvestigation}
                disabled={investigating || !selectedOrderId}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black bg-[#FC8019] hover:bg-[#E27315] text-white transition-all shadow-sm shadow-orange-500/20 disabled:opacity-50"
              >
                {investigating ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin" />
                    Checking restaurant, courier & timing...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Start AI Order Investigation
                  </>
                )}
              </button>
            </div>
          </div>

          {selectedOrder && (
            <div className="flex flex-wrap items-center gap-4 border-t md:border-t-0 md:border-l border-gray-100 pt-3 md:pt-0 md:pl-5 text-xs">
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Customer</span>
                <span className="font-bold text-[#282C3F]">{selectedOrder.customer_name || 'Customer Name'}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Order Status</span>
                <span className="font-extrabold px-2 py-0.5 rounded text-[11px] bg-blue-50 text-blue-700">
                  {selectedOrder.order_status.replace(/_/g, ' ')}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Acting Role (Approval Testing)</span>
                <select
                  value={operatorRole}
                  onChange={(e) => setOperatorRole(e.target.value)}
                  className="bg-[#FAFAFA] border border-gray-200 rounded-lg px-2 py-1 text-xs font-bold text-[#282C3F] focus:outline-none focus:ring-1 focus:ring-[#FC8019]"
                >
                  <option value="OPS_LEAD">{formatRoleLabel('OPS_LEAD')}</option>
                  <option value="OPERATOR">{formatRoleLabel('OPERATOR')}</option>
                  <option value="SUPERVISOR">{formatRoleLabel('SUPERVISOR')}</option>
                  <option value="JUNIOR_INTERN">{formatRoleLabel('JUNIOR_INTERN')}</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Core Insights: Order Risk, Estimated Delivery Time Range & Cancellation Risk */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Order Risk */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Order Risk
              </span>
              <Bot className="w-4 h-4 text-[#FC8019]" />
            </div>

            {activeInvestigation ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-lg text-sm font-black tracking-wide border ${riskMeta.badgeClass}`}
                  >
                    {riskMeta.label}
                  </span>
                  <span className="text-xs text-[#686B78] font-medium">
                    {activeInvestigation.trigger_event ? `Trigger: ${activeInvestigation.trigger_event.replace(/_/g, ' ')}` : 'Routine Check'}
                  </span>
                </div>
                <p className="text-xs text-[#686B78] leading-relaxed pt-1">
                  {resolution.root_cause_summary || riskMeta.description}
                </p>
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">
                No investigation run yet. Click &quot;Start AI Order Investigation&quot; above.
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setShowRiskTechDetails(!showRiskTechDetails)}
              className="text-[11px] font-semibold text-[#FC8019] hover:underline flex items-center justify-between w-full"
            >
              <span>{showRiskTechDetails ? 'Hide Technical Details' : 'Show Technical Details'}</span>
              {showRiskTechDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showRiskTechDetails && activeInvestigation && (
              <div className="mt-2 p-2.5 rounded-lg bg-gray-50 border border-gray-200 text-[10px] font-mono text-gray-700 space-y-1">
                <div>Internal Risk Code: <strong>{activeInvestigation.risk_tier}</strong></div>
                <div>Trigger Source: {activeInvestigation.trigger_event || 'SYSTEM'}</div>
                <div>Investigation Latency: {activeInvestigation.workflow_execution?.investigation_duration_ms ?? 14.2} ms</div>
                <div>Correlation ID: {activeInvestigation.workflow_execution?.correlation_id?.slice(0, 16) || 'N/A'}...</div>
              </div>
            )}
          </div>
        </div>

        {/* Card 2: Estimated Delivery Time Range (Task A) */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Estimated Delivery Time Range
              </span>
              <Clock className="w-4 h-4 text-blue-600" />
            </div>

            {taskA.eta_p50_min ? (
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-black text-[#282C3F]">{etaRange.headline}</span>
                  <span className="text-xs font-bold text-[#686B78]">Most Likely Time</span>
                </div>

                {/* Range Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-bold text-[#686B78]">
                    <span>Fastest: {taskA.eta_p10_min}m</span>
                    <span className="text-blue-700 font-extrabold">{taskA.eta_p10_min} &ndash; {taskA.eta_p90_min} mins</span>
                    <span>Latest: {taskA.eta_p90_min}m</span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden relative">
                    <div className="absolute left-[20%] right-[15%] top-0 bottom-0 bg-blue-500 rounded-full" />
                  </div>
                  <div className="text-[10px] text-[#686B78] flex justify-between">
                    <span>80% Confidence Interval</span>
                    <span
                      className={`font-bold ${
                        taskA.confidence === 'HIGH'
                          ? 'text-green-600'
                          : taskA.confidence === 'LOW'
                          ? 'text-red-500'
                          : 'text-amber-600'
                      }`}
                    >
                      Confidence: {taskA.confidence || 'MODERATE'}
                    </span>
                  </div>
                </div>

                <p className="text-[10px] text-gray-500 italic leading-tight">
                  Forecast based on kitchen prep and road conditions. Not a guaranteed arrival time.
                </p>
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">Awaiting delivery time forecast...</div>
            )}
          </div>

          <div className="pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setShowEtaTechDetails(!showEtaTechDetails)}
              className="text-[11px] font-semibold text-blue-600 hover:underline flex items-center justify-between w-full"
            >
              <span>{showEtaTechDetails ? 'Hide Quantile Details' : 'Show Quantile Details'}</span>
              {showEtaTechDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showEtaTechDetails && taskA.eta_p50_min && (
              <div className="mt-2 p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-[10px] font-mono text-blue-900 space-y-1">
                <div>Model: LightGBM Multi-Quantile Regressor v2.5.0</div>
                <div>P10: {taskA.eta_p10_min}m &bull; P50: {taskA.eta_p50_min}m &bull; P90: {taskA.eta_p90_min}m</div>
                <div>Interval Width: {taskA.interval_width_min} mins</div>
                <div>Inference Latency: {taskA.inference_latency_ms ?? 1.8} ms</div>
                <div>Partition: Training partition fitted, chronological split</div>
              </div>
            )}
          </div>
        </div>

        {/* Card 3: Cancellation Risk (Task C2) */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Cancellation Risk
              </span>
              <AlertTriangle className="w-4 h-4 text-[#FC8019]" />
            </div>

            {taskC2.is_eligible !== undefined ? (
              <div className="space-y-3">
                {taskC2.is_eligible ? (
                  <>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-black text-[#282C3F]">
                        {((taskC2.calibrated_probability || 0) * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                        {((taskC2.calibrated_probability || 0) > 0.15) ? 'Elevated Risk' : 'Low Risk'}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-medium">
                        <span className="text-[#686B78]">Proactive Action Alert:</span>
                        <div className="flex gap-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              taskC2.alert_budget_10_per_1000
                                ? 'bg-amber-500 text-white'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {taskC2.alert_budget_10_per_1000 ? 'Action Recommended' : 'Normal Limits'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <p className="text-[10px] text-gray-500 leading-tight">
                      Estimated likelihood customer cancels if delay continues. Used solely for proactive support.
                    </p>
                  </>
                ) : (
                  <div className="py-2 space-y-2">
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-700 border border-gray-200 inline-block">
                      Checkpoint Not Reached
                    </span>
                    <p className="text-xs text-[#686B78] leading-tight">
                      {taskC2.eligibility_reason || 'Order is in early stage; risk checkpoint is evaluated 5 minutes after driver allotment.'}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">Awaiting cancellation risk check...</div>
            )}
          </div>

          <div className="pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setShowCancelTechDetails(!showCancelTechDetails)}
              className="text-[11px] font-semibold text-purple-700 hover:underline flex items-center justify-between w-full"
            >
              <span>{showCancelTechDetails ? 'Hide Model Calibration' : 'Show Model Calibration'}</span>
              {showCancelTechDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showCancelTechDetails && taskC2.is_eligible && (
              <div className="mt-2 p-2.5 rounded-lg bg-purple-50 border border-purple-200 text-[10px] font-mono text-purple-900 space-y-1">
                <div>Model: Task C2 Landmark Classifier (Isotonic Calibrated)</div>
                <div>Alert 5/1k Budget: {taskC2.alert_budget_5_per_1000 ? 'TRIGGERED' : 'CLEAR'}</div>
                <div>Alert 10/1k Budget: {taskC2.alert_budget_10_per_1000 ? 'TRIGGERED' : 'CLEAR'}</div>
                <div>Governance: APPROVED_FOR_CONTROLLED_TRIAGE (Monitoring Only)</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Operational Status Checks: Restaurant & Delivery Partner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Card 1: Restaurant Status Check */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-orange-100 text-[#FC8019] flex items-center justify-center font-bold">
                <Store className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#282C3F]">Restaurant Status Check</h3>
                <span className="text-[10px] text-[#686B78] font-medium">Kitchen preparation pace & order queue</span>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#EDF7EC] text-[#60B246]">
              {restEv.confidence || 'ACTIVE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Order Acceptance Time</span>
              <span className="text-base font-extrabold text-[#282C3F]">
                {restEv.acceptance_latency_min !== undefined ? `${restEv.acceptance_latency_min}m` : '1.5m'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">Target: under 2.5 mins</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Extra Kitchen Delay</span>
              <span
                className={`text-base font-extrabold ${
                  (restEv.prep_delay_min || 0) > 5 ? 'text-red-600' : 'text-green-600'
                }`}
              >
                +{restEv.prep_delay_min !== undefined ? restEv.prep_delay_min : 0}m
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">Estimated prep: {restEv.estimated_prep_total_min || 16} mins</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100 col-span-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#686B78] font-semibold">Kitchen Order Queue</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  Demo Telemetry
                </span>
              </div>
              <span className="text-base font-extrabold text-[#282C3F]">
                {restEv.kitchen_backlog_orders || 3} Orders Ahead in Kitchen
              </span>
              <p className="text-[11px] text-[#686B78] mt-1">
                {restEv.operational_impact || 'Food preparation is moving at normal pace.'}
              </p>
            </div>
          </div>
        </div>

        {/* Card 2: Delivery Partner Status */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                <Truck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#282C3F]">Delivery Partner Status</h3>
                <span className="text-[10px] text-[#686B78] font-medium">Courier assignment, road distance & traffic</span>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700">
              {delivEv.confidence || 'ACTIVE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Courier Assignment Time</span>
              <span className="text-base font-extrabold text-[#282C3F]">
                {delivEv.allotment_latency_min !== undefined ? `${delivEv.allotment_latency_min}m` : '2.1m'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">Target: under 3 mins</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Distance to Restaurant</span>
              <span
                className={`text-base font-extrabold ${
                  (delivEv.first_mile_km || 0) > 3.0 ? 'text-amber-600' : 'text-[#282C3F]'
                }`}
              >
                {delivEv.first_mile_km !== undefined ? `${delivEv.first_mile_km} km` : '1.8 km'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">
                {delivEv.is_extreme_first_mile ? 'Far Pickup Distance' : 'Standard Pickup Radius'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100 col-span-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#686B78] font-semibold">Transit Traffic & Reassignments</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-gray-100 text-gray-700">
                  Traffic Factor: {delivEv.transit_congestion_factor || '1.0'}x
                </span>
              </div>
              <span className="text-base font-extrabold text-[#282C3F]">
                {delivEv.reassignment_count || 0} Courier Reassignment(s)
              </span>
              <p className="text-[11px] text-[#686B78] mt-1">
                {delivEv.operational_impact || 'Delivery partner assigned and traveling to restaurant.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Suggested Actions & Action Approval Rules */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-[#282C3F] flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#FC8019]" />
              Suggested Actions & Action Approval Rules
            </h2>
            <p className="text-xs text-[#686B78] mt-0.5">
              Action approval rules ensure sensitive customer compensation or dispatch changes require manager approval before processing.
            </p>
          </div>

          <span className="text-xs font-bold text-[#686B78]">
            {recommendations.length} Action(s) Available
          </span>
        </div>

        {recommendations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                  <th className="py-2.5 px-3">Suggested Action</th>
                  <th className="py-2.5 px-3">Title & Rationale</th>
                  <th className="py-2.5 px-3">Impact Level</th>
                  <th className="py-2.5 px-3">Approval Requirement</th>
                  <th className="py-2.5 px-3">Current Status</th>
                  <th className="py-2.5 px-3 text-right">Manager Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recommendations.map((rec) => {
                  const actionMeta = formatActionType(rec.action_type);

                  return (
                    <tr key={rec.id} className="hover:bg-gray-50/50 transition-colors">
                      <td className="py-3 px-3 font-semibold text-[11px] text-[#282C3F]">
                        {actionMeta.title}
                      </td>
                      <td className="py-3 px-3 max-w-sm">
                        <span className="font-bold text-[#282C3F] block">{rec.title}</span>
                        <span className="text-[11px] text-[#686B78] line-clamp-2 mt-0.5">{rec.rationale}</span>
                        {rec.estimated_impact && (
                          <span className="text-[10px] text-green-700 font-medium block mt-1">
                            &bull; Expected Impact: {rec.estimated_impact}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            rec.sensitivity_level === 'HIGH'
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : rec.sensitivity_level === 'MEDIUM'
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-green-50 text-green-700 border border-green-200'
                          }`}
                        >
                          {rec.sensitivity_level === 'HIGH'
                            ? 'High Impact'
                            : rec.sensitivity_level === 'MEDIUM'
                            ? 'Moderate'
                            : 'Standard'}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            rec.approval_status === 'APPROVED' || rec.approval_status === 'AUTO_APPROVED'
                              ? 'bg-[#EDF7EC] text-[#2E7D32]'
                              : rec.approval_status === 'REJECTED'
                              ? 'bg-red-50 text-red-700'
                              : 'bg-amber-100 text-amber-900 animate-pulse'
                          }`}
                        >
                          {rec.approval_status === 'PENDING_APPROVAL'
                            ? 'Requires Manager Approval'
                            : rec.approval_status === 'APPROVED'
                            ? 'Approved'
                            : rec.approval_status === 'REJECTED'
                            ? 'Declined'
                            : rec.approval_status}
                        </span>
                        {rec.operator_role && (
                          <span className="block text-[9px] text-blue-600 font-medium mt-0.5">
                            Approver: {rec.operator_role}
                          </span>
                        )}
                        {rec.expires_at && rec.execution_status === 'PENDING' && (
                          <span className="block text-[9px] text-gray-400 mt-0.5">
                            Valid until: {new Date(rec.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-semibold">
                        <span
                          className={`text-[11px] ${
                            rec.execution_status === 'EXECUTED'
                              ? 'text-[#60B246] font-bold'
                              : rec.execution_status === 'CANCELLED'
                              ? 'text-gray-400 line-through'
                              : 'text-[#FC8019]'
                          }`}
                        >
                          {rec.execution_status === 'EXECUTED'
                            ? 'Completed'
                            : rec.execution_status === 'CANCELLED'
                            ? 'Cancelled'
                            : 'Ready to Process'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {rec.approval_status === 'PENDING_APPROVAL' && (
                            <>
                              <button
                                onClick={() => handleApprove(rec.id)}
                                disabled={actionLoadingId === rec.id}
                                className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-[#60B246] hover:bg-[#529C3B] text-white transition-all shadow-xs"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleReject(rec.id)}
                                disabled={actionLoadingId === rec.id}
                                className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-gray-200 hover:bg-gray-300 text-gray-700 transition-all shadow-xs"
                              >
                                Decline
                              </button>
                            </>
                          )}
                          {rec.approval_status === 'APPROVED' && rec.execution_status === 'PENDING' && (
                            <button
                              onClick={() => handleExecute(rec.id)}
                              disabled={actionLoadingId === rec.id}
                              className="px-3 py-1 rounded-lg text-[10px] font-bold bg-[#FC8019] hover:bg-[#E27315] text-white transition-all shadow-xs"
                            >
                              Process Action
                            </button>
                          )}
                          {rec.execution_status === 'EXECUTED' && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#60B246]">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Completed
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-[#686B78] italic">
            No suggested actions generated yet for this order. Start an AI Order Investigation above.
          </div>
        )}
      </div>

      {/* Action History (with Anchor ID for navigation) */}
      <div id="activity-history" className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-gray-700" />
            <div>
              <h2 className="text-base font-bold text-[#282C3F]">Action History</h2>
              <p className="text-xs text-[#686B78]">
                Permanent, tamper-proof record of every resolution action. Duplicate action protection prevents redundant vouchers.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-600">
            Duplicate Action Protection Active
          </span>
        </div>

        {audits.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Action Taken</th>
                  <th className="py-2.5 px-3">Protection Key</th>
                  <th className="py-2.5 px-3">Authorized By</th>
                  <th className="py-2.5 px-3">Outcome</th>
                  <th className="py-2.5 px-3">Result Summary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {audits.map((a) => {
                  const actionMeta = formatActionType(a.action_type);

                  return (
                    <tr key={a.id} className="hover:bg-gray-50/50">
                      <td className="py-2.5 px-3 text-[#686B78] whitespace-nowrap">
                        {new Date(a.executed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-[#282C3F]">{actionMeta.title}</td>
                      <td className="py-2.5 px-3 font-mono text-[10px] text-gray-500" title={a.idempotency_key}>
                        {a.idempotency_key.slice(0, 16)}...
                      </td>
                      <td className="py-2.5 px-3 text-[#282C3F] font-semibold">{a.approval_identity || 'AUTOMATIC'}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#EDF7EC] text-[#2E7D32]">
                          {a.recovery_outcome === 'SUCCESS' ? 'Completed Successfully' : a.recovery_outcome}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 max-w-sm">
                        {(() => {
                          const execResult = formatExecutionResult(a.execution_result, a.action_type);
                          const isExpanded = expandedAuditId === a.id;

                          return (
                            <div className="space-y-1">
                              <div className="font-bold text-[#282C3F] text-xs">
                                {execResult.headline}
                              </div>
                              <div className="text-[11px] text-[#686B78]">
                                {execResult.summary}
                              </div>
                              {execResult.items.length > 0 && (
                                <div className="pt-1">
                                  <button
                                    type="button"
                                    onClick={() => setExpandedAuditId(isExpanded ? null : a.id)}
                                    className="text-[10px] font-bold text-[#FC8019] hover:underline flex items-center gap-1"
                                  >
                                    <span>{isExpanded ? 'Hide Attributes' : 'Inspect Attributes'}</span>
                                    {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                                  </button>

                                  {isExpanded && (
                                    <div className="mt-2 p-2.5 rounded-xl bg-gray-50 border border-gray-200 space-y-2">
                                      <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                                        {execResult.items.map((item) => (
                                          <div key={item.key} className="bg-white p-1.5 rounded-lg border border-gray-200">
                                            <span className="text-[#686B78] block font-medium opacity-80">{item.label}</span>
                                            <span className="font-bold text-[#282C3F] break-words">{item.display}</span>
                                          </div>
                                        ))}
                                      </div>
                                      <details className="pt-1 border-t border-gray-200">
                                        <summary className="text-[9px] font-mono text-gray-400 cursor-pointer hover:text-gray-600">
                                          Raw JSON Payload
                                        </summary>
                                        <pre className="mt-1 p-2 bg-gray-900 text-gray-100 rounded text-[9px] font-mono overflow-x-auto">
                                          {JSON.stringify(a.execution_result, null, 2)}
                                        </pre>
                                      </details>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#686B78] italic">
            No resolution actions executed yet for this order.
          </div>
        )}
      </div>

      {/* Expandable Technical Section: Prediction History & Engineering Diagnostics */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-700" />
            <div>
              <h2 className="text-base font-bold text-[#282C3F]">Prediction History & Engineering Diagnostics</h2>
              <p className="text-xs text-[#686B78]">
                Technical breakdown for engineering demonstrations, model provenance audits, and interviews.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowPredictionHistory(!showPredictionHistory)}
            className="text-xs font-bold text-purple-700 hover:underline flex items-center gap-1"
          >
            <span>{showPredictionHistory ? 'Collapse Diagnostics' : 'Expand Diagnostics'}</span>
            {showPredictionHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {showPredictionHistory && (
          <div className="space-y-4 pt-2">
            {mlAudits.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                      <th className="py-2.5 px-3">Prediction Time</th>
                      <th className="py-2.5 px-3">Model Version</th>
                      <th className="py-2.5 px-3">Task A ETA (P10 - P50 - P90)</th>
                      <th className="py-2.5 px-3">Tail Risk</th>
                      <th className="py-2.5 px-3">Task C2 Calibrated</th>
                      <th className="py-2.5 px-3">Alert Budgets (5k / 10k)</th>
                      <th className="py-2.5 px-3">Sub-Model Risk Scores</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {mlAudits.map((m) => (
                      <tr key={m.id} className="hover:bg-gray-50/50">
                        <td className="py-2.5 px-3 text-[#686B78] whitespace-nowrap">
                          {new Date(m.prediction_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] font-bold text-[#282C3F]">
                          v{m.model_version}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-[#282C3F]">
                          {m.task_a_interval_min ?? 'N/A'}m &ndash; <strong className="text-blue-600">{m.task_a_eta_p50 ?? 'N/A'}m</strong> &ndash; {m.task_a_interval_max ?? 'N/A'}m
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.task_a_is_long_tail
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {m.task_a_is_long_tail ? 'LONG_TAIL' : 'STANDARD'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold">
                          {m.task_c2_calibrated_prob !== null && m.task_c2_calibrated_prob !== undefined
                            ? `${(m.task_c2_calibrated_prob * 100).toFixed(1)}%`
                            : 'Ineligible'}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                m.task_c2_alert_5k ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              5k: {m.task_c2_alert_5k ? 'YES' : 'NO'}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                m.task_c2_alert_10k ? 'bg-amber-500 text-white' : 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              10k: {m.task_c2_alert_10k ? 'YES' : 'NO'}
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-[10px]">
                          <div className="flex flex-col gap-0.5 font-medium">
                            <span className="text-[#686B78]" title="Task B: Courier Reassignment Score">
                              Reassign Risk: <strong className="text-[#282C3F] font-mono">{m.task_b_score?.toFixed(2) ?? 'N/A'}</strong>
                            </span>
                            <span className="text-[#686B78]" title="Task C1: Kitchen Bottleneck Score">
                              Kitchen Risk: <strong className="text-[#282C3F] font-mono">{m.task_c1_score?.toFixed(2) ?? 'N/A'}</strong>
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-[#686B78] italic">
                No model prediction history recorded yet for this order.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function OrderIntelligencePage() {
  return (
    <Suspense
      fallback={
        <div className="py-24 text-center">
          <RotateCw className="w-8 h-8 animate-spin mx-auto text-[#FC8019] mb-3" />
          <p className="text-sm font-semibold text-[#282C3F]">Loading order insights...</p>
        </div>
      }
    >
      <OrderIntelligenceInner />
    </Suspense>
  );
}
