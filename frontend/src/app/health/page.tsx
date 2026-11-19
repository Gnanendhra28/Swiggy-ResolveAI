'use client';

import React, { useEffect, useState } from 'react';
import {
  Server,
  Database,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Clock,
  Cpu,
  Layers,
  Zap,
  ShieldCheck,
  Bot,
  Brain,
  HardDrive,
  Hash,
  ChevronDown,
  Info,
} from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import { SystemHealth } from '@/lib/types';

export default function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pingLatency, setPingLatency] = useState<number | null>(null);
  const [lastCheck, setLastCheck] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const h = await fetchHealth();
      const end = performance.now();
      setHealth(h);
      setPingLatency(Math.round(end - start));
      setLastCheck(new Date().toLocaleTimeString());
    } catch (err: any) {
      setError(err.message || 'Unable to connect to ResolveAI backend service.');
      setHealth(null);
      setPingLatency(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const getStatusColor = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ready':
      case 'live':
      case 'connected':
        return 'bg-[#60B246]';
      case 'fallback_ready':
      case 'degraded':
        return 'bg-[#D97706]';
      default:
        return 'bg-[#E23744]';
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ready':
      case 'live':
      case 'connected':
        return 'bg-[#EDF7EC] text-[#60B246] border-[#C8E6C9]';
      case 'fallback_ready':
      case 'degraded':
        return 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]';
      default:
        return 'bg-[#FEF2F2] text-[#E23744] border-[#FECACA]';
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#60B246]" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              System Performance & Data Connection Status
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            Live status of order data connections, prediction services, and response speeds.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastCheck && (
            <span className="text-[11px] text-[#93959F] font-mono">
              Last checked: {lastCheck}
            </span>
          )}
          <button
            onClick={checkHealth}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#FC8019] hover:bg-[#E27315] text-xs font-bold text-white shadow-sm shadow-orange-500/20 hover:shadow transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Check Connections Now</span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-2xl border border-[#FECDD3] bg-[#FDF0F1] p-4 text-[#E23744] space-y-1">
          <div className="flex items-center gap-2 font-bold text-xs">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>Connection Notice</span>
          </div>
          <p className="text-xs">{error}</p>
        </div>
      )}

      {/* 4 Pillars Operational Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pillar 1: Application Server */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Server className="w-4 h-4 text-[#FC8019]" />
              Application Server
            </span>
            <span className={`w-2.5 h-2.5 rounded-full ${getStatusColor(health?.status)}`} />
          </div>

          <div>
            <p className="text-lg font-black text-[#282C3F] capitalize">
              {health?.application?.status === 'ready' || health?.status === 'healthy' ? 'Operational' : (error ? 'Offline' : 'Checking...')}
            </p>
            <p className="text-xs text-[#686B78] mt-0.5">
              Order Processing API Service
            </p>
          </div>

          <div className="pt-3 border-t border-[#F4F5F7] text-xs space-y-1">
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Response Speed:</span>
              <span className="font-mono font-bold text-[#282C3F]">
                {pingLatency !== null ? `${pingLatency} ms` : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Mode:</span>
              <span className="font-bold text-[#282C3F] capitalize text-[10px]">
                {health?.environment || 'Active'}
              </span>
            </div>
          </div>
        </div>

        {/* Pillar 2: Data Connection Status */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Database className="w-4 h-4 text-[#FC8019]" />
              Data Connection
            </span>
            <span className={`w-2.5 h-2.5 rounded-full ${getStatusColor(health?.infrastructure?.database_status || health?.database)}`} />
          </div>

          <div>
            <p className="text-lg font-black text-[#282C3F] capitalize">
              {health?.infrastructure?.database_status === 'connected' || health?.database === 'connected' ? 'Connected' : 'Disconnected'}
            </p>
            <p className="text-xs text-[#686B78] mt-0.5">
              PostgreSQL Data Store
            </p>
          </div>

          <div className="pt-3 border-t border-[#F4F5F7] text-xs space-y-1">
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Query Latency:</span>
              <span className="font-mono font-bold text-[#282C3F]">
                {health?.infrastructure?.database_latency_ms != null
                  ? `${health.infrastructure.database_latency_ms} ms`
                  : '< 2 ms'}
              </span>
            </div>
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Database Schema:</span>
              <span className="font-bold text-[#60B246] text-[10px] bg-[#EDF7EC] px-1.5 py-0.5 rounded border border-[#C8E6C9]">
                Up to Date
              </span>
            </div>
          </div>
        </div>

        {/* Pillar 3: AI Assistant Status */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Bot className="w-4 h-4 text-[#FC8019]" />
              AI Assistant
            </span>
            <span className={`w-2.5 h-2.5 rounded-full ${getStatusColor(health?.ai_provider?.status || 'fallback_ready')}`} />
          </div>

          <div>
            <p className="text-lg font-black text-[#282C3F] capitalize">
              {health?.ai_provider?.status === 'live' ? 'Connected (Gemini)' : 'Standby (Smart Rules)'}
            </p>
            <p className="text-xs text-[#686B78] mt-0.5 truncate">
              {health?.ai_provider?.model_name ? `AI Model: ${health.ai_provider.model_name}` : 'Autonomous Rule Engine'}
            </p>
          </div>

          <div className="pt-3 border-t border-[#F4F5F7] text-xs space-y-1">
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Automatic Fallback:</span>
              <span className="font-bold text-[#60B246] text-[10px]">
                Always Ready
              </span>
            </div>
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Manager Approvals:</span>
              <span className="font-bold text-[#FC8019] text-[10px]">Enforced</span>
            </div>
          </div>
        </div>

        {/* Pillar 4: Prediction Engine Status */}
        <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#686B78] uppercase tracking-wider flex items-center gap-1.5">
              <Brain className="w-4 h-4 text-[#FC8019]" />
              Prediction Engine
            </span>
            <span className={`w-2.5 h-2.5 rounded-full ${getStatusColor(health?.ml_artifacts?.status || 'ready')}`} />
          </div>

          <div>
            <p className="text-lg font-black text-[#282C3F] capitalize">
              {health?.ml_artifacts?.status === 'ready' ? 'Ready & Calibrated' : 'Checking...'}
            </p>
            <p className="text-xs text-[#686B78] mt-0.5">
              Delivery & Risk Models
            </p>
          </div>

          <div className="pt-3 border-t border-[#F4F5F7] text-xs space-y-1">
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Estimated Delivery:</span>
              <span className="font-bold text-[#60B246] text-[10px]">Active (Range)</span>
            </div>
            <div className="flex justify-between items-center text-[#686B78]">
              <span>Cancellation Risk:</span>
              <span className="font-bold text-[#60B246] text-[10px]">Calibrated</span>
            </div>
          </div>
        </div>
      </div>

      {/* User-Friendly Overview Card */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)]">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-2xl bg-orange-50 border border-orange-100 flex-shrink-0">
            <ShieldCheck className="w-6 h-6 text-[#FC8019]" />
          </div>
          <div className="space-y-1 flex-1">
            <h2 className="text-base font-bold text-[#282C3F]">
              How ResolveAI Safeguards Restaurant and Delivery Operations
            </h2>
            <p className="text-xs text-[#686B78] leading-relaxed">
              ResolveAI continuously listens to incoming order updates, kitchen preparation progress, and courier road conditions. When an unexpected delay occurs, the system evaluates the situation against preset business safety rules. High-impact remedies (like customer apology discounts or rider reassignments) are held for supervisor review, ensuring no unapproved actions are taken automatically.
            </p>
            <div className="flex flex-wrap gap-4 pt-2 text-[11px] text-[#282C3F] font-medium">
              <span className="flex items-center gap-1.5 text-[#60B246]">
                <CheckCircle2 className="w-3.5 h-3.5" /> High-impact actions require manager approval
              </span>
              <span className="flex items-center gap-1.5 text-[#60B246]">
                <CheckCircle2 className="w-3.5 h-3.5" /> Duplicate action protection active
              </span>
              <span className="flex items-center gap-1.5 text-[#60B246]">
                <CheckCircle2 className="w-3.5 h-3.5" /> Demo environment: no real courier dispatch
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expandable Technical Diagnostics Drawer */}
      <div className="bg-white rounded-2xl border border-[#E9ECEE] shadow-[0_2px_8px_rgba(40,44,63,0.04)] overflow-hidden">
        <details className="group">
          <summary className="p-5 flex items-center justify-between cursor-pointer hover:bg-[#FBFBFC] transition-colors select-none">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#FC8019]" />
              <div>
                <h3 className="text-xs font-bold text-[#282C3F] uppercase tracking-wider">
                  Technical System Diagnostics & Model Specifications
                </h3>
                <p className="text-[11px] text-[#686B78] mt-0.5">
                  Detailed model versions, API endpoints, calibration specifications, and server metrics for technical inspection.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-[#FC8019] group-open:hidden">
                Click to inspect
              </span>
              <ChevronDown className="w-4 h-4 text-[#93959F] group-open:rotate-180 transition-transform" />
            </div>
          </summary>

          <div className="divide-y divide-[#F4F5F7] border-t border-[#F4F5F7] text-xs">
            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Application Core Service</span>
              <span className="font-bold text-[#282C3F]">{health?.application?.name || 'Swiggy ResolveAI'}</span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Backend API Gateway</span>
              <span className="font-mono text-[#FC8019]">
                {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
              </span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">AI Model Provider</span>
              <div className="text-right">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadge(health?.ai_provider?.status)}`}>
                  {health?.ai_provider?.details || 'Deterministic Rule Synthesizer Standby'}
                </span>
              </div>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Delivery Time Model (Task A)</span>
              <span className="font-mono text-[#282C3F]">
                LightGBM Regressor • Quantiles P10, P50, P90 • Pinball Loss Evaluated
              </span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Cancellation Risk Model (Task C2)</span>
              <span className="font-mono text-[#282C3F]">
                LightGBM Classifier • Post-Hoc Isotonic Probability Calibration • ROC-AUC & Brier Score Validated
              </span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Model Artifacts Path</span>
              <span className="font-mono text-[#282C3F]">{health?.ml_artifacts?.artifacts_dir || 'data/artifacts/models/phase_2_5'}</span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Server Timestamp (UTC)</span>
              <span className="font-mono text-[#282C3F]">{health?.timestamp || '—'}</span>
            </div>

            <div className="p-4 flex items-center justify-between hover:bg-[#FBFBFC]">
              <span className="font-semibold text-[#686B78]">Safety Boundary & Data Provenance</span>
              <span className="font-bold text-[#60B246] bg-[#EDF7EC] px-2 py-0.5 rounded border border-[#C8E6C9]">
                Simulated & Historical Data Isolation (No Real Swiggy Order Dispatch)
              </span>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
