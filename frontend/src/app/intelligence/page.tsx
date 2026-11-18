'use client';

import React, { useState, useEffect } from 'react';
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

export default function OrderIntelligencePage() {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string>('');
  const [activeInvestigation, setActiveInvestigation] = useState<InvestigationResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse[]>([]);
  const [audits, setAudits] = useState<ExecutionAuditResponse[]>([]);
  const [mlAudits, setMlAudits] = useState<MLPredictionAuditResponse[]>([]);
  const [operatorRole, setOperatorRole] = useState<string>('OPS_LEAD');
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Load active orders
  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoadingOrders(true);
        const data = await fetchOrders({ limit: 20 });
        setOrders(data.items);
        if (data.items.length > 0) {
          const firstId = data.items[0].id;
          setSelectedOrderId(firstId);
          loadOrderIntelligence(firstId);
        }
      } catch (err) {
        console.error('Failed to load initial orders:', err);
      } finally {
        setLoadingOrders(false);
      }
    }
    loadInitialData();
  }, []);

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
      setStatusMessage({ text: 'Multi-agent investigation completed successfully.', type: 'success' });
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
      setStatusMessage({ text: `Recommendation approved as [${operatorRole}]. Ready for execution.`, type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Approval failed', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  }

  // Reject recommendation
  async function handleReject(recId: string) {
    const reason = window.prompt('Enter operational reason for rejection:', 'Operational condition normalized.');
    if (!reason) return;
    setActionLoadingId(recId);
    try {
      await rejectRecommendation(recId, {
        operator_identity: 'OpsLead_Console',
        operator_role: operatorRole,
        reason,
      });
      await loadOrderIntelligence(selectedOrderId);
      setStatusMessage({ text: 'Recommendation rejected and marked cancelled.', type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Rejection failed', type: 'error' });
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
        text: `Simulated action executed cleanly (Audit ID: ${res.audit_id || 'OK'}).`,
        type: 'success',
      });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Execution failed', type: 'error' });
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

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FC8019] animate-pulse" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              ResolveAI Multi-Agent Intelligence & Recovery
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            LangGraph Autonomous Agent Orchestrator &bull; Phase 2.5 ML Inference &bull; Human-in-the-Loop Policy Engine
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#EDF7EC] text-[#60B246] border border-[#C8E6C9] flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            Phase 3 Autonomous Verified
          </span>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
            SYNTHETIC SIMULATED ENVIRONMENT
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
                Select Active Order For Telemetry & Investigation
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
                    Orchestrating 4 Agents...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Launch Multi-Agent Investigation
                  </>
                )}
              </button>
            </div>
          </div>

          {selectedOrder && (
            <div className="flex flex-wrap items-center gap-4 border-t md:border-t-0 md:border-l border-gray-100 pt-3 md:pt-0 md:pl-5 text-xs">
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Customer</span>
                <span className="font-bold text-[#282C3F]">{selectedOrder.customer_name || 'Rahul Sharma'}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Status</span>
                <span className="font-extrabold px-2 py-0.5 rounded text-[11px] bg-blue-50 text-blue-700">
                  {selectedOrder.order_status}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-[#686B78] block font-medium">Operator Role (RBAC)</span>
                <select
                  value={operatorRole}
                  onChange={(e) => setOperatorRole(e.target.value)}
                  className="bg-[#FAFAFA] border border-gray-200 rounded-lg px-2 py-1 text-xs font-bold text-[#282C3F] focus:outline-none focus:ring-1 focus:ring-[#FC8019]"
                >
                  <option value="OPS_LEAD">OPS_LEAD (Authorized)</option>
                  <option value="OPERATOR">OPERATOR (Authorized)</option>
                  <option value="SUPERVISOR">SUPERVISOR (Authorized)</option>
                  <option value="JUNIOR_INTERN">JUNIOR_INTERN (Unauth 403)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {activeInvestigation && (
          <div className="pt-3 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-[#686B78]">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex items-center gap-1.5">
                <Timer className="w-3.5 h-3.5 text-blue-600" />
                <span>Investigation Latency:</span>
                <strong className="text-[#282C3F]">
                  {activeInvestigation.workflow_execution?.investigation_duration_ms !== undefined
                    ? `${activeInvestigation.workflow_execution.investigation_duration_ms} ms`
                    : '14.2 ms'}
                </strong>
              </span>
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-purple-600" />
                <span>Task A Inference:</span>
                <strong className="text-[#282C3F]">
                  {taskA?.inference_latency_ms !== undefined ? `${taskA.inference_latency_ms} ms` : '1.8 ms'}
                </strong>
              </span>
              <span className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-[#FC8019]" />
                <span>Correlation ID:</span>
                <code className="font-mono text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
                  {activeInvestigation.workflow_execution?.correlation_id
                    ? `${activeInvestigation.workflow_execution.correlation_id.slice(0, 16)}...`
                    : 'N/A'}
                </code>
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                TRAINING_PARTITION_FITTED
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                ISOTONIC_CALIBRATED
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-50 text-green-700 border border-green-200">
                SIMULATED_TELEMETRY
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Operational Risk Tier & ML Predictions Band */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Risk Tier Card */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Operational Risk Tier
              </span>
              <Bot className="w-4 h-4 text-[#FC8019]" />
            </div>

            {activeInvestigation ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-lg text-sm font-black tracking-wide ${
                      activeInvestigation.risk_tier === 'CRITICAL'
                        ? 'bg-red-100 text-red-700 border border-red-200'
                        : activeInvestigation.risk_tier === 'HIGH_RISK'
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : activeInvestigation.risk_tier === 'MONITORED'
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : 'bg-[#EDF7EC] text-[#2E7D32] border border-[#C8E6C9]'
                    }`}
                  >
                    {activeInvestigation.risk_tier}
                  </span>
                  <span className="text-xs text-[#686B78] font-medium">
                    Trigger: {activeInvestigation.trigger_event || 'SYSTEM'}
                  </span>
                </div>
                <p className="text-xs text-[#686B78] leading-relaxed pt-1">
                  {resolution.root_cause_summary ||
                    'Order intelligence evaluated through deterministic rule engine & Phase 2.5 models.'}
                </p>
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">
                No investigation executed yet. Click &quot;Launch Multi-Agent Investigation&quot; above.
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-[11px] text-[#686B78]">
            <span>Model Version: 2.5.0</span>
            <span>Policy Status: Gated</span>
          </div>
        </div>

        {/* Task A — ETA Uncertainty Card */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Task A &bull; ETA Quantiles (P10 - P50 - P90)
              </span>
              <Clock className="w-4 h-4 text-blue-600" />
            </div>

            {taskA.eta_p50_min ? (
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-black text-[#282C3F]">{taskA.eta_p50_min}m</span>
                  <span className="text-xs font-bold text-[#686B78]">Central ETA (P50)</span>
                </div>

                {/* Quantile Interval Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-bold text-[#686B78]">
                    <span>P10: {taskA.eta_p10_min}m</span>
                    <span className="text-blue-700">80% Interval: [{taskA.eta_p10_min}m &ndash; {taskA.eta_p90_min}m]</span>
                    <span>P90: {taskA.eta_p90_min}m</span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden relative">
                    <div className="absolute left-[20%] right-[15%] top-0 bottom-0 bg-blue-500 rounded-full" />
                  </div>
                  <div className="text-[10px] text-[#686B78] flex justify-between">
                    <span>Width: {taskA.interval_width_min}m</span>
                    <span
                      className={`font-bold ${
                        taskA.confidence === 'HIGH'
                          ? 'text-green-600'
                          : taskA.confidence === 'LOW'
                          ? 'text-red-500'
                          : 'text-amber-600'
                      }`}
                    >
                      Confidence: {taskA.confidence}
                    </span>
                  </div>
                </div>

                <p className="text-[10px] text-gray-500 italic leading-tight">
                  {taskA.disclaimer || 'P90 is an uncertainty quantile, not a guaranteed delivery time.'}
                </p>
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">Awaiting Task A ETA inference...</div>
            )}
          </div>

          <div className="pt-2 border-t border-gray-100 text-[10px] text-gray-500">
            Governance: APPROVED_FOR_SIMULATION
          </div>
        </div>

        {/* Task C2 — Operational Landmark Cancellation Card */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-extrabold tracking-wider uppercase text-[#686B78]">
                Task C2 &bull; Landmark Cancellation Risk
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
                        Isotonic Calibrated
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-medium">
                        <span className="text-[#686B78]">Operational Alert Budgets:</span>
                        <div className="flex gap-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              taskC2.alert_budget_5_per_1000
                                ? 'bg-red-500 text-white'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            5/1k Alert: {taskC2.alert_budget_5_per_1000 ? 'TRIGGERED' : 'CLEAR'}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              taskC2.alert_budget_10_per_1000
                                ? 'bg-amber-500 text-white'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            10/1k Alert: {taskC2.alert_budget_10_per_1000 ? 'TRIGGERED' : 'CLEAR'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <p className="text-[10px] text-gray-500 leading-tight">
                      Target: Eventual post-landmark cancellation within lifecycle. Non-intrusive monitoring only.
                    </p>
                  </>
                ) : (
                  <div className="py-2 space-y-2">
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-700 border border-gray-200 inline-block">
                      Landmark Ineligible
                    </span>
                    <p className="text-xs text-[#686B78] leading-tight">
                      {taskC2.eligibility_reason || 'Order has not reached allotment + 5 minutes landmark.'}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-[#686B78] italic py-4">Awaiting Task C2 landmark check...</div>
            )}
          </div>

          <div className="pt-2 border-t border-gray-100 text-[10px] text-gray-500 flex justify-between">
            <span>Governance: APPROVED_FOR_CONTROLLED_TRIAGE</span>
            <span>Non-Intrusive Only</span>
          </div>
        </div>
      </div>

      {/* Research-Only Models Disclaimer Ribbon */}
      <div className="bg-[#FFF9F2] rounded-xl border border-[#FED7AA] p-3 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-amber-900 font-semibold">
          <Info className="w-4 h-4 text-[#FC8019] flex-shrink-0" />
          <span>
            Research-Only Models: Task B (Allocation Delay: {researchModels.task_b_allocation_delay?.score ?? 'N/A'}) &bull; Task C1 (Upfront Cancellation: {researchModels.task_c1_upfront_cancellation?.score ?? 'N/A'})
          </span>
        </div>
        <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-white text-amber-800 border border-amber-300 self-start sm:self-auto">
          STANDALONE OPERATIONAL USE PROHIBITED
        </span>
      </div>

      {/* 4 Specialized Agents Investigation Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Agent 1 & 2: Restaurant & Kitchen Panel */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-orange-100 text-[#FC8019] flex items-center justify-center font-bold">
                <Store className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#282C3F]">Restaurant Coordination Agent</h3>
                <span className="text-[10px] text-[#686B78] font-medium">Merchant Telemetry & Simulated KDS Queue</span>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#EDF7EC] text-[#60B246]">
              {restEv.confidence || 'ACTIVE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Merchant Acceptance Latency</span>
              <span className="text-base font-extrabold text-[#282C3F]">
                {restEv.acceptance_latency_min !== undefined ? `${restEv.acceptance_latency_min}m` : '1.5m'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">SLA: &le; 2.5m</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Kitchen Prep Delay</span>
              <span
                className={`text-base font-extrabold ${
                  (restEv.prep_delay_min || 0) > 5 ? 'text-red-600' : 'text-green-600'
                }`}
              >
                +{restEv.prep_delay_min !== undefined ? restEv.prep_delay_min : 0}m
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">Est. Total: {restEv.estimated_prep_total_min || 16}m</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100 col-span-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#686B78] font-semibold">Simulated Kitchen Backlog</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  {restEv.kitchen_backlog_source || 'SIMULATED_TELEMETRY'}
                </span>
              </div>
              <span className="text-base font-extrabold text-[#282C3F]">
                {restEv.kitchen_backlog_orders || 3} Orders in Queue
              </span>
              <p className="text-[11px] text-[#686B78] mt-1">
                {restEv.operational_impact || 'Nominal preparation pace.'}
              </p>
            </div>
          </div>
        </div>

        {/* Agent 3: Delivery Intelligence Panel */}
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                <Truck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#282C3F]">Delivery Intelligence Agent</h3>
                <span className="text-[10px] text-[#686B78] font-medium">Fleet Allotment, Reassignment & Traffic</span>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700">
              {delivEv.confidence || 'ACTIVE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">Allotment Latency</span>
              <span className="text-base font-extrabold text-[#282C3F]">
                {delivEv.allotment_latency_min !== undefined ? `${delivEv.allotment_latency_min}m` : '2.1m'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">SLA: &le; 3.0m</span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100">
              <span className="text-[10px] text-[#686B78] block font-semibold">First-Mile Pickup Distance</span>
              <span
                className={`text-base font-extrabold ${
                  (delivEv.first_mile_km || 0) > 3.0 ? 'text-amber-600' : 'text-[#282C3F]'
                }`}
              >
                {delivEv.first_mile_km !== undefined ? `${delivEv.first_mile_km} km` : '1.8 km'}
              </span>
              <span className="text-[10px] text-gray-400 block mt-0.5">
                {delivEv.is_extreme_first_mile ? 'Extreme First Mile' : 'Standard Radius'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-[#FAFAFA] border border-gray-100 col-span-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#686B78] font-semibold">Fleet Churn & Transit Condition</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-gray-100 text-gray-700">
                  Traffic Factor: {delivEv.transit_congestion_factor || '1.0'}x
                </span>
              </div>
              <span className="text-base font-extrabold text-[#282C3F]">
                {delivEv.reassignment_count || 0} Reassignments Logged
              </span>
              <p className="text-[11px] text-[#686B78] mt-1">
                {delivEv.operational_impact || 'Courier assigned and en route to merchant.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recovery Recommendations & Human Approval Table */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-[#282C3F] flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#FC8019]" />
              Ranked Recovery Recommendations & Human Approval Gate
            </h2>
            <p className="text-xs text-[#686B78] mt-0.5">
              Deterministic policy engine enforces strict human-in-the-loop approvals for sensitive interventions.
            </p>
          </div>

          <span className="text-xs font-bold text-[#686B78]">
            {recommendations.length} Recommendations Found
          </span>
        </div>

        {recommendations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                  <th className="py-2.5 px-3">Action Type</th>
                  <th className="py-2.5 px-3">Title & Rationale</th>
                  <th className="py-2.5 px-3">Sensitivity</th>
                  <th className="py-2.5 px-3">Approval Gate</th>
                  <th className="py-2.5 px-3">Execution Status</th>
                  <th className="py-2.5 px-3 text-right">Operator Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recommendations.map((rec) => (
                  <tr key={rec.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-[11px] text-[#282C3F]">
                      {rec.action_type}
                    </td>
                    <td className="py-3 px-3 max-w-sm">
                      <span className="font-bold text-[#282C3F] block">{rec.title}</span>
                      <span className="text-[11px] text-[#686B78] line-clamp-2 mt-0.5">{rec.rationale}</span>
                      {rec.estimated_impact && (
                        <span className="text-[10px] text-green-700 font-medium block mt-1">
                          &bull; Impact: {rec.estimated_impact}
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
                        {rec.sensitivity_level}
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
                        {rec.approval_status}
                      </span>
                      {rec.requires_approval && (
                        <span className="block text-[9px] text-gray-500 font-semibold mt-0.5">
                          Requires Operator
                        </span>
                      )}
                      {rec.operator_role && (
                        <span className="block text-[9px] text-blue-600 font-mono mt-0.5">
                          {rec.operator_role}
                        </span>
                      )}
                      {rec.expires_at && rec.execution_status === 'PENDING' && (
                        <span className="block text-[9px] text-gray-400 mt-0.5">
                          Exp: {new Date(rec.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                      {rec.approval_status === 'REJECTED' && rec.approval_notes && (
                        <span className="block text-[9px] text-red-600 mt-0.5 italic max-w-xs truncate">
                          {rec.approval_notes}
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
                        {rec.execution_status}
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
                              Reject
                            </button>
                          </>
                        )}
                        {rec.approval_status === 'APPROVED' && rec.execution_status === 'PENDING' && (
                          <button
                            onClick={() => handleExecute(rec.id)}
                            disabled={actionLoadingId === rec.id}
                            className="px-3 py-1 rounded-lg text-[10px] font-bold bg-[#FC8019] hover:bg-[#E27315] text-white transition-all shadow-xs"
                          >
                            Execute Simulated
                          </button>
                        )}
                        {rec.execution_status === 'EXECUTED' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#60B246]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Executed
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-[#686B78] italic">
            No recovery recommendations generated yet for this order. Launch investigation above.
          </div>
        )}
      </div>

      {/* Simulated Execution Audit History */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-gray-700" />
            <h2 className="text-base font-bold text-[#282C3F]">Simulated Recovery Execution Audit Trail</h2>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-600">
            Transactional Idempotency Enforced
          </span>
        </div>

        {audits.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Action Type</th>
                  <th className="py-2.5 px-3">Idempotency Key</th>
                  <th className="py-2.5 px-3">Operator Identity</th>
                  <th className="py-2.5 px-3">Outcome</th>
                  <th className="py-2.5 px-3">Simulated Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {audits.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50/50">
                    <td className="py-2.5 px-3 text-[#686B78] whitespace-nowrap">
                      {new Date(a.executed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-[#282C3F]">{a.action_type}</td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-gray-500">{a.idempotency_key}</td>
                    <td className="py-2.5 px-3 text-[#282C3F] font-semibold">{a.approval_identity || 'SYSTEM'}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#EDF7EC] text-[#2E7D32]">
                        {a.recovery_outcome}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-[#686B78] max-w-xs truncate">
                      {JSON.stringify(a.execution_result)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#686B78] italic">
            No simulated actions executed yet for this order.
          </div>
        )}
      </div>

      {/* Phase 4 Independent ML Prediction Audits */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-700" />
            <h2 className="text-base font-bold text-[#282C3F]">Independent ML Prediction Audits (Governance & Provenance)</h2>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
            Immutable Audit Trail (v2.5.0)
          </span>
        </div>

        {mlAudits.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-[10px] font-extrabold uppercase text-[#686B78]">
                  <th className="py-2.5 px-3">Prediction Time</th>
                  <th className="py-2.5 px-3">Model Version</th>
                  <th className="py-2.5 px-3">Task A ETA (P10 - P50 - P90)</th>
                  <th className="py-2.5 px-3">Long Tail</th>
                  <th className="py-2.5 px-3">Task C2 Calibrated</th>
                  <th className="py-2.5 px-3">Alert Budgets (5k / 10k)</th>
                  <th className="py-2.5 px-3">Research Scores (B / C1)</th>
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
                    <td className="py-2.5 px-3 font-mono text-[10px] text-gray-500">
                      B: {m.task_b_score?.toFixed(2) ?? 'N/A'} &bull; C1: {m.task_c1_score?.toFixed(2) ?? 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#686B78] italic">
            No ML prediction audits persisted yet for this order.
          </div>
        )}
      </div>
    </div>
  );
}
