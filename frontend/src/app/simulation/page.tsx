'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  PlayCircle,
  Settings,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Eye,
  Sliders,
  Hash,
  ShieldCheck,
  ChevronRight,
  Flame,
  Truck,
  Layers,
  ArrowRight,
  Store,
  Clock,
  Package,
  BarChart3,
  TrendingUp,
  Percent,
  DollarSign,
  Activity,
  Cpu,
  ShieldAlert,
  HelpCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  fetchSimulationScenarios,
  triggerSimulation,
  runSimulationExperiment,
  fetchSimulationExperiments,
  runStressTest,
} from '@/lib/api';
import {
  ScenarioMeta,
  ScenarioType,
  SimulationResult,
  SimulationExperimentDetail,
  SimulationExperimentSummary,
  StressTestItem,
} from '@/lib/types';
import { OrderStatusBadge } from '@/components/OrderStatusBadge';
import { formatDataSource } from '@/lib/presentation';

export default function SimulationCenterPage() {
  const [activeTab, setActiveTab] = useState<'EXPERIMENTS' | 'GENERATOR'>('EXPERIMENTS');

  // Generator state (Demo Orders)
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('NORMAL_ORDER');
  const [orderCount, setOrderCount] = useState<number>(3);
  const [seed, setSeed] = useState<string>('');
  const [loadingScenarios, setLoadingScenarios] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Strategy Comparison state
  const [expScenario, setExpScenario] = useState<string>('COMBINED_KITCHEN_DELIVERY_DELAY');
  const [expVolume, setExpVolume] = useState<number>(50);
  const [expSeed, setExpSeed] = useState<number>(42);
  const [expPrepBase, setExpPrepBase] = useState<number>(18);
  const [expEffectiveness, setExpEffectiveness] = useState<number>(0.80);
  const [runningExperiment, setRunningExperiment] = useState<boolean>(false);
  const [currentExperiment, setCurrentExperiment] = useState<SimulationExperimentDetail | null>(null);
  const [recentExperiments, setRecentExperiments] = useState<SimulationExperimentSummary[]>([]);
  const [loadingRecent, setLoadingRecent] = useState<boolean>(false);

  // Stress test state
  const [runningStressTest, setRunningStressTest] = useState<boolean>(false);
  const [stressResults, setStressResults] = useState<StressTestItem[] | null>(null);

  // Selected comparison tab in experiment details
  const [activeComparisonIndex, setActiveComparisonIndex] = useState<number>(0);
  const [showTechnicalStats, setShowTechnicalStats] = useState<boolean>(false);

  useEffect(() => {
    const loadInitial = async () => {
      setLoadingScenarios(true);
      try {
        const scList = await fetchSimulationScenarios();
        setScenarios(scList);
      } catch (err: any) {
        console.error('Failed to load simulation scenarios:', err);
      } finally {
        setLoadingScenarios(false);
      }

      // Load recent experiments
      loadRecentExperiments();
    };
    loadInitial();
  }, []);

  const loadRecentExperiments = async () => {
    setLoadingRecent(true);
    try {
      const res = await fetchSimulationExperiments({ limit: 10 });
      setRecentExperiments(res.experiments);
    } catch (err) {
      console.error('Failed to fetch recent experiments:', err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    setError(null);
    try {
      const parsedSeed = seed.trim() !== '' ? parseInt(seed.trim(), 10) : undefined;
      const res = await triggerSimulation({
        scenario: selectedScenario,
        count: orderCount,
        seed: parsedSeed,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Demo order generation failed.');
    } finally {
      setSimulating(false);
    }
  };

  const handleRunExperiment = async () => {
    setRunningExperiment(true);
    setError(null);
    try {
      const exp = await runSimulationExperiment({
        scenario_type: expScenario,
        order_volume: expVolume,
        random_seed: expSeed,
        prep_time_base_min: expPrepBase,
        recovery_action_effectiveness: expEffectiveness,
        gross_order_value_inr: 450.0,
      });
      setCurrentExperiment(exp);
      setActiveComparisonIndex(0);
      loadRecentExperiments();
    } catch (err: any) {
      setError(err.message || 'Strategy comparison run failed.');
    } finally {
      setRunningExperiment(false);
    }
  };

  const handleRunStressSuite = async () => {
    setRunningStressTest(true);
    setError(null);
    try {
      const res = await runStressTest({ base_volume: 30, seed: 101 });
      setStressResults(res.stress_test_matrix);
    } catch (err: any) {
      setError(err.message || 'Stress test suite failed.');
    } finally {
      setRunningStressTest(false);
    }
  };

  const getScenarioIcon = (id: ScenarioType) => {
    switch (id) {
      case 'NORMAL_ORDER':
        return <Package className="w-5 h-5 text-[#60B246]" />;
      case 'RESTAURANT_DELAY':
        return <Flame className="w-5 h-5 text-[#FC8019]" />;
      case 'DELIVERY_DELAY':
        return <Truck className="w-5 h-5 text-[#D97706]" />;
      case 'ASSIGNMENT_DELAY':
        return <RefreshCw className="w-5 h-5 text-[#FC8019]" />;
      case 'FAILED_RECOVERY':
        return <AlertTriangle className="w-5 h-5 text-[#E23744]" />;
      case 'SUCCESSFUL_RECOVERY':
        return <Sparkles className="w-5 h-5 text-[#FC8019]" />;
      default:
        return <PlayCircle className="w-5 h-5 text-[#FC8019]" />;
    }
  };

  const EXP_SCENARIOS = [
    { id: 'NORMAL_DELIVERY', label: 'Normal Delivery', desc: 'Baseline operations without unexpected delays' },
    { id: 'RESTAURANT_PREP_DELAY', label: 'Kitchen Prep Delay', desc: '15-25 mins extra preparation time due to dish complexity' },
    { id: 'RESTAURANT_CAPACITY_OVERLOAD', label: 'Kitchen Overload', desc: 'Heavy kitchen queue (>8 orders ahead in kitchen)' },
    { id: 'COURIER_ASSIGNMENT_DELAY', label: 'Courier Search Delay', desc: 'Longer search time due to local courier shortage' },
    { id: 'COURIER_ACCEPTANCE_DELAY', label: 'Courier Response Delay', desc: 'Assigned courier delays moving towards restaurant' },
    { id: 'COURIER_REASSIGNMENT', label: 'Courier Reassignment', desc: 'Courier cancelled pickup; backup driver assigned' },
    { id: 'TRAFFIC_CONGESTION', label: 'Heavy Road Traffic', desc: 'Peak hour congestion doubling transit time' },
    { id: 'LONG_DISTANCE_DELIVERY', label: 'Long Distance Delivery', desc: 'Specialty restaurant order over a 10+ km route' },
    { id: 'COMBINED_KITCHEN_DELIVERY_DELAY', label: 'Double Bottleneck', desc: 'Both kitchen delay and road traffic combined' },
    { id: 'HIGH_CANCELLATION_RISK', label: 'High Cancellation Risk', desc: 'Orders matching historical cancellation patterns' },
    { id: 'FAILED_RECOVERY', label: 'Severe Breakdown', desc: 'Courier vehicle breakdown requiring emergency handling' },
    { id: 'SUCCESSFUL_RECOVERY', label: 'Prevented Delay', desc: 'Proactive support successfully prevented late delivery' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FC8019]" />
            <h1 className="text-2xl font-black text-[#282C3F] tracking-tight">
              Try Scenarios & Strategy Comparisons
            </h1>
          </div>
          <p className="text-xs text-[#686B78] mt-1 font-medium">
            Test how ResolveAI responds to delivery disruptions, compare recovery strategies, and create demo orders.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-[#F4F5F7] p-1 rounded-xl border border-[#E9ECEE]">
          <button
            onClick={() => setActiveTab('EXPERIMENTS')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'EXPERIMENTS'
                ? 'bg-white text-[#FC8019] shadow-sm'
                : 'text-[#686B78] hover:text-[#282C3F]'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Compare Recovery Strategies
          </button>
          <button
            onClick={() => setActiveTab('GENERATOR')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'GENERATOR'
                ? 'bg-white text-[#FC8019] shadow-sm'
                : 'text-[#686B78] hover:text-[#282C3F]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Create Demo Orders
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: RECOVERY STRATEGY COMPARISON                                        */}
      {/* ========================================================================= */}
      {activeTab === 'EXPERIMENTS' && (
        <div className="space-y-6">
          {/* Controls Card */}
          <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F4F5F7] pb-3">
              <div>
                <h2 className="text-sm font-bold text-[#282C3F] uppercase tracking-wider flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-[#FC8019]" />
                  1. Strategy Comparison Setup
                </h2>
                <p className="text-xs text-[#686B78] mt-0.5">
                  Simulates identical test orders side-by-side to compare business outcomes with and without ResolveAI.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-50 text-purple-700 border border-purple-200">
                  Simulated Comparison
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Scenario */}
              <div>
                <label className="block text-xs font-bold text-[#282C3F] mb-1.5">
                  Delivery Situation to Test
                </label>
                <select
                  value={expScenario}
                  onChange={(e) => setExpScenario(e.target.value)}
                  className="w-full text-xs bg-[#F8F9FA] border border-[#E9ECEE] rounded-xl px-3 py-2 text-[#282C3F] focus:outline-none focus:border-[#FC8019]"
                >
                  {EXP_SCENARIOS.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-[#93959F] mt-1 line-clamp-1">
                  {EXP_SCENARIOS.find((s) => s.id === expScenario)?.desc}
                </p>
              </div>

              {/* Volume */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-[#282C3F]">Batch Size (Number of Orders)</label>
                  <span className="text-xs font-bold text-[#FC8019]">{expVolume} orders</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={10}
                  value={expVolume}
                  onChange={(e) => setExpVolume(parseInt(e.target.value, 10))}
                  className="w-full accent-[#FC8019] cursor-pointer mt-1"
                />
                <div className="flex justify-between text-[10px] text-[#93959F] mt-1">
                  <span>10 (quick test)</span>
                  <span>50 (recommended)</span>
                  <span>100 (in-depth)</span>
                </div>
              </div>

              {/* Seed */}
              <div>
                <label className="block text-xs font-bold text-[#282C3F] mb-1.5">
                  Test Random Seed
                </label>
                <div className="relative">
                  <Hash className="w-3.5 h-3.5 text-[#93959F] absolute left-3 top-2.5" />
                  <input
                    type="number"
                    value={expSeed}
                    onChange={(e) => setExpSeed(parseInt(e.target.value, 10) || 42)}
                    className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#F8F9FA] border border-[#E9ECEE] rounded-xl text-[#282C3F] focus:outline-none focus:border-[#FC8019]"
                  />
                </div>
                <p className="text-[11px] text-[#93959F] mt-1">Guarantees identical simulated orders.</p>
              </div>

              {/* Action Effectiveness */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-[#282C3F]">Assumed Action Success Rate</label>
                  <span className="text-xs font-bold text-[#60B246]">{Math.round(expEffectiveness * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0.4}
                  max={1.0}
                  step={0.05}
                  value={expEffectiveness}
                  onChange={(e) => setExpEffectiveness(parseFloat(e.target.value))}
                  className="w-full accent-[#60B246] cursor-pointer mt-1"
                />
                <div className="flex justify-between text-[10px] text-[#93959F] mt-1">
                  <span>40% (low)</span>
                  <span>80% (typical)</span>
                  <span>100% (perfect)</span>
                </div>
              </div>
            </div>

            {/* CTAs */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#F4F5F7]">
              <div className="flex items-center gap-2 text-xs text-[#686B78]">
                <Clock className="w-3.5 h-3.5 text-[#FC8019]" />
                <span>Assumed Order Value: <b>₹450</b> | Notification: ₹5 | Priority: ₹15 | Reassign: ₹35 | Voucher: ₹50</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleRunStressSuite}
                  disabled={runningStressTest || runningExperiment}
                  className="px-4 py-2 rounded-xl border border-[#E9ECEE] hover:bg-[#F8F9FA] text-xs font-bold text-[#282C3F] flex items-center gap-1.5 disabled:opacity-50 transition-all"
                >
                  {runningStressTest ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#FC8019]" />
                  ) : (
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                  )}
                  Run 8-Case Stress Test
                </button>
                <button
                  onClick={handleRunExperiment}
                  disabled={runningExperiment || runningStressTest}
                  className="px-5 py-2.5 rounded-xl bg-[#FC8019] hover:bg-[#e67312] text-white text-xs font-bold flex items-center gap-2 shadow-[0_2px_8px_rgba(252,128,25,0.25)] disabled:opacity-50 transition-all"
                >
                  {runningExperiment ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Comparing 4 Strategies...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="w-4 h-4" />
                      Run Strategy Comparison
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Current Experiment Results */}
          {currentExperiment && (
            <div className="space-y-6">
              {/* Metadata Banner */}
              <div className="bg-[#FFFDFB] border border-[#FED7AA] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#FC8019]" />
                    <h3 className="text-sm font-black text-[#282C3F]">
                      {currentExperiment.name}
                    </h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
                      {currentExperiment.scenario_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-xs text-[#686B78] mt-0.5">
                    Evaluated {currentExperiment.num_orders} identical test orders across 4 recovery strategies | Random Seed: {currentExperiment.random_seed}
                  </p>
                </div>
                <div className="text-[11px] text-[#93959F]">
                  Run ID: <code className="text-[#282C3F] font-mono">{(currentExperiment?.id || (currentExperiment as any)?.experiment_id || 'UNKNOWN').slice(0, 8)}</code>
                </div>
              </div>

              {/* 4 Strategy Comparative Scorecards */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-[#686B78] uppercase tracking-wider">
                    2. Strategy Performance Comparison (Under Identical Delivery Conditions)
                  </h3>
                  <span className="text-[11px] text-[#93959F]">Side-by-side performance</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'baseline', title: '1. No Automated Support', sub: 'Passive Monitoring Only', color: 'border-slate-200' },
                    { key: 'rule_based', title: '2. Simple Rules Only', sub: 'Fixed Threshold Alerts', color: 'border-blue-200' },
                    { key: 'ml_assisted', title: '3. Early Risk Alerts', sub: 'Delivery Range + Risk Scoring', color: 'border-amber-200' },
                    { key: 'multi_agent', title: '4. ResolveAI', sub: 'Proactive Action & Manager Approvals', color: 'border-[#FC8019] bg-[#FFFDFB]' },
                  ].map((s) => {
                    const kpi = currentExperiment.kpi_results[s.key];
                    if (!kpi) return null;
                    const isResolveAI = s.key === 'multi_agent';
                    return (
                      <div
                        key={s.key}
                        className={`rounded-2xl p-5 border ${s.color} shadow-sm space-y-4`}
                      >
                        <div>
                          <div className="flex items-center justify-between gap-1">
                            <h4 className="text-xs font-black text-[#282C3F] leading-snug">{s.title}</h4>
                            {isResolveAI && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-[#FC8019] text-white">
                                RESOLVEAI
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-[#686B78] mt-0.5">{s.sub}</p>
                        </div>

                        {/* Top Metrics Grid */}
                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#F4F5F7]">
                          <div className="bg-[#F8F9FA] rounded-xl p-2.5">
                            <span className="text-[10px] text-[#93959F] font-semibold block">On-Time Rate</span>
                            <span className="text-base font-black text-[#282C3F]">
                              {kpi.delivery.on_time_delivery_rate_pct}%
                            </span>
                          </div>
                          <div className="bg-[#F8F9FA] rounded-xl p-2.5">
                            <span className="text-[10px] text-[#93959F] font-semibold block">Avg Delivery Time</span>
                            <span className="text-base font-black text-[#282C3F]">
                              {kpi.delivery.average_delivery_duration_min}m
                            </span>
                          </div>
                        </div>

                        {/* Middle Metrics Grid */}
                        <div className="space-y-1.5 text-xs">
                          <div className="flex justify-between items-center text-[#686B78]">
                            <span>Cancellation Rate:</span>
                            <span className="font-bold text-[#282C3F]">
                              {kpi.cancellation.overall_cancellation_rate_pct}%
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[#686B78]">
                            <span>Late Cancellations:</span>
                            <span className="font-bold text-[#282C3F]">
                              {kpi.cancellation.post_landmark_cancellation_rate_pct}%
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[#686B78]">
                            <span>Support Actions Taken:</span>
                            <span className="font-bold text-[#282C3F]">
                              {kpi.business_efficiency.total_interventions_count}
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[#686B78]">
                            <span>Action Cost:</span>
                            <span className="font-bold text-[#282C3F]">
                              ₹{kpi.business_efficiency.simulated_intervention_cost_inr}
                            </span>
                          </div>
                        </div>

                        {/* Economic Impact */}
                        <div className="pt-3 border-t border-[#F4F5F7]">
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] font-bold text-[#686B78]">Estimated Net Benefit:</span>
                            <span className={`text-xs font-black ${
                              kpi.business_efficiency.net_simulated_operational_benefit_inr >= 0
                                ? 'text-[#60B246]'
                                : 'text-[#E23744]'
                            }`}>
                              ₹{kpi.business_efficiency.net_simulated_operational_benefit_inr.toFixed(2)}
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[10px] text-[#93959F] mt-0.5">
                            <span>Saved Refund Losses:</span>
                            <span>₹{kpi.business_efficiency.estimated_cancellation_losses_avoided_inr.toFixed(0)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Matched Comparisons & Difference Highlights */}
              {currentExperiment.counterfactual_comparisons?.comparisons?.length > 0 && (
                <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F4F5F7] pb-3">
                    <div>
                      <h3 className="text-xs font-bold text-[#282C3F] uppercase tracking-wider flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-[#FC8019]" />
                        3. Measured Improvement vs Alternative Strategies
                      </h3>
                      <p className="text-xs text-[#686B78] mt-0.5">
                        Direct differences measured against alternative strategies under identical order conditions.
                      </p>
                    </div>
                    {/* Comparison Selector */}
                    <div className="flex items-center gap-1 bg-[#F4F5F7] p-1 rounded-xl">
                      {currentExperiment.counterfactual_comparisons.comparisons.map((c, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActiveComparisonIndex(idx)}
                          className={`px-2.5 py-1 text-[11px] font-bold rounded-lg transition-all ${
                            activeComparisonIndex === idx
                              ? 'bg-white text-[#FC8019] shadow-xs'
                              : 'text-[#686B78] hover:text-[#282C3F]'
                          }`}
                        >
                          ResolveAI vs {c.reference_name.split('—')[0].replace('Strategy ', 'S')}
                        </button>
                      ))}
                    </div>
                  </div>

                  {(() => {
                    const comp = currentExperiment.counterfactual_comparisons.comparisons[activeComparisonIndex] || currentExperiment.counterfactual_comparisons.comparisons[0];
                    if (!comp) return null;
                    return (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                          {/* Delta Duration */}
                          <div className="bg-[#F8F9FA] rounded-xl p-4 border border-[#E9ECEE] space-y-2">
                            <span className="text-[11px] font-bold text-[#686B78] block">Time Saved per Order</span>
                            <div className="flex items-baseline gap-2">
                              <span className={`text-xl font-black ${
                                comp.duration.mean_difference <= 0 ? 'text-[#60B246]' : 'text-[#E23744]'
                              }`}>
                                {comp.duration.mean_difference <= 0
                                  ? `${Math.abs(comp.duration.mean_difference).toFixed(1)} mins faster`
                                  : `+${comp.duration.mean_difference.toFixed(1)} mins slower`}
                              </span>
                            </div>
                            <p className="text-[11px] text-[#686B78] pt-1">
                              Average delivery duration improvement across the order batch.
                            </p>
                          </div>

                          {/* Delta On-time */}
                          <div className="bg-[#F8F9FA] rounded-xl p-4 border border-[#E9ECEE] space-y-2">
                            <span className="text-[11px] font-bold text-[#686B78] block">On-Time Delivery Increase</span>
                            <div className="flex items-baseline gap-2">
                              <span className={`text-xl font-black ${
                                comp.ontime.difference_pct >= 0 ? 'text-[#60B246]' : 'text-[#E23744]'
                              }`}>
                                {comp.ontime.difference_pct > 0 ? '+' : ''}{comp.ontime.difference_pct.toFixed(1)}%
                              </span>
                            </div>
                            <p className="text-[11px] text-[#686B78] pt-1">
                              More orders delivered within promised customer SLA.
                            </p>
                          </div>

                          {/* Delta Cancellation */}
                          <div className="bg-[#F8F9FA] rounded-xl p-4 border border-[#E9ECEE] space-y-2">
                            <span className="text-[11px] font-bold text-[#686B78] block">Cancellation Reduction</span>
                            <div className="flex items-baseline gap-2">
                              <span className={`text-xl font-black ${
                                comp.cancellation.difference_pct <= 0 ? 'text-[#60B246]' : 'text-[#E23744]'
                              }`}>
                                {comp.cancellation.difference_pct < 0
                                  ? `${Math.abs(comp.cancellation.difference_pct).toFixed(1)}% fewer`
                                  : `+${comp.cancellation.difference_pct.toFixed(1)}%`}
                              </span>
                            </div>
                            <p className="text-[11px] text-[#686B78] pt-1">
                              Net financial benefit difference: <b>₹{comp.net_benefit_difference_inr.toFixed(0)}</b>
                            </p>
                          </div>
                        </div>

                        {/* Technical Statistics Expandable Toggle */}
                        <div className="pt-2">
                          <button
                            type="button"
                            onClick={() => setShowTechnicalStats(!showTechnicalStats)}
                            className="text-[11px] font-semibold text-[#FC8019] hover:underline flex items-center gap-1"
                          >
                            <span>{showTechnicalStats ? 'Hide Statistical Verification Data' : 'View Statistical Verification Data (Confidence Intervals & p-values)'}</span>
                            {showTechnicalStats ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          </button>

                          {showTechnicalStats && (
                            <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-xl text-[11px] font-mono text-gray-700 space-y-1">
                              <div>Duration 95% Bootstrap CI: [{comp.duration.ci_95[0].toFixed(2)}, {comp.duration.ci_95[1].toFixed(2)}] min</div>
                              <div>Duration Cohen&apos;s d: {comp.duration.cohens_d.toFixed(3)} | p-value: {comp.duration.p_value.toFixed(4)}</div>
                              <div>On-Time 95% Bootstrap CI: [{comp.ontime.ci_95[0].toFixed(2)}%, {comp.ontime.ci_95[1].toFixed(2)}%]</div>
                              <div>Cancellation 95% Bootstrap CI: [{comp.cancellation.ci_95[0].toFixed(2)}%, {comp.cancellation.ci_95[1].toFixed(2)}%]</div>
                              <div>Causal Caveat: {comp.causal_claim_caveat}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          )}

          {/* Historical Persisted Strategy Comparisons */}
          <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-[#F4F5F7] pb-3">
              <div>
                <h3 className="text-xs font-bold text-[#282C3F] uppercase tracking-wider">
                  4. Past Strategy Comparison Tests
                </h3>
                <p className="text-xs text-[#686B78] mt-0.5">
                  Archived test comparisons saved with reproducible parameters.
                </p>
              </div>
              <button
                onClick={loadRecentExperiments}
                disabled={loadingRecent}
                className="text-xs text-[#FC8019] hover:underline flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${loadingRecent ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {loadingRecent ? (
              <div className="py-8 text-center text-xs text-[#686B78]">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#FC8019] mb-1" />
                Loading tests...
              </div>
            ) : recentExperiments.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#93959F]">
                No previous tests recorded yet. Run a comparison above to generate benchmark data.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] font-bold text-[#93959F] uppercase border-b border-[#E9ECEE] bg-[#F8F9FA]">
                    <tr>
                      <th className="py-2 px-3">Test Name</th>
                      <th className="py-2 px-3">Disruption Type</th>
                      <th className="py-2 px-3">Orders (N)</th>
                      <th className="py-2 px-3">ResolveAI On-Time %</th>
                      <th className="py-2 px-3">Estimated Benefit</th>
                      <th className="py-2 px-3">Created At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F4F5F7]">
                    {recentExperiments.map((e) => {
                      const multiKpi = e.kpi_summary?.multi_agent;
                      return (
                        <tr key={e.id} className="hover:bg-[#FFFDFB]">
                          <td className="py-2.5 px-3 font-bold text-[#282C3F]">{e.name}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
                              {e.scenario_type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-[#686B78]">{e.num_orders}</td>
                          <td className="py-2.5 px-3 font-bold text-[#282C3F]">
                            {multiKpi?.on_time_rate_pct != null ? `${multiKpi.on_time_rate_pct}%` : '—'}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[#60B246]">
                            {multiKpi?.net_benefit_inr != null ? `₹${multiKpi.net_benefit_inr.toFixed(0)}` : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-[11px] text-[#93959F]">
                            {new Date(e.created_at).toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CREATE DEMO ORDERS                                                 */}
      {/* ========================================================================= */}
      {activeTab === 'GENERATOR' && (
        <form onSubmit={handleRunSimulation} className="space-y-6">
          {/* Scenario Selection Grid */}
          <div className="space-y-3">
            <label className="block text-xs font-bold text-[#686B78] uppercase tracking-wider">
              1. Choose a Delivery Scenario to Test
            </label>

            {loadingScenarios ? (
              <div className="py-12 text-center bg-white rounded-2xl border border-[#E9ECEE]">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#FC8019] mb-2" />
                <p className="text-xs font-semibold text-[#686B78]">Loading test scenarios...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {scenarios.map((sc) => {
                  const isSelected = selectedScenario === sc.id;
                  return (
                    <div
                      key={sc.id}
                      onClick={() => setSelectedScenario(sc.id)}
                      className={`cursor-pointer rounded-2xl p-5 border transition-all flex flex-col justify-between ${
                        isSelected
                          ? 'bg-[#FFFDFB] border-[#FC8019] shadow-[0_4px_16px_rgba(252,128,25,0.12)] ring-1 ring-[#FC8019]'
                          : 'bg-white border-[#E9ECEE] hover:border-[#D1D5DB] hover:shadow-[0_2px_8px_rgba(40,44,63,0.06)]'
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                                isSelected ? 'bg-[#FFF5ED]' : 'bg-[#F4F5F7]'
                              }`}
                            >
                              {getScenarioIcon(sc.id)}
                            </div>
                            <h3 className="text-sm font-bold text-[#282C3F]">
                              {sc.title}
                            </h3>
                          </div>

                          <div
                            className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                              isSelected
                                ? 'border-[#FC8019] bg-[#FC8019]'
                                : 'border-[#D1D5DB]'
                            }`}
                          >
                            {isSelected && (
                              <span className="w-1.5 h-1.5 rounded-full bg-white" />
                            )}
                          </div>
                        </div>

                        <p className="text-xs text-[#686B78] mt-3 leading-relaxed">
                          {sc.description}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-[#F4F5F7] flex items-center justify-between text-[11px]">
                        <span className="text-[#93959F]">Expected Outcome:</span>
                        <span className="font-bold text-[#282C3F]">
                          {sc.expected_status.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Configuration Panel Card */}
          <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-6">
            <div className="border-b border-[#F4F5F7] pb-3">
              <h2 className="text-sm font-bold text-[#282C3F] uppercase tracking-wider">
                2. Order Generation Settings
              </h2>
              <p className="text-xs text-[#686B78] mt-0.5">
                Choose how many demo orders to create for live testing
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Batch Slider */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-xs font-bold text-[#282C3F]">
                    Number of Demo Orders
                  </label>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#FFF5ED] text-[#FC8019] border border-[#FED7AA]">
                    {orderCount} {orderCount === 1 ? 'Order' : 'Orders'}
                  </span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={orderCount}
                  onChange={(e) => setOrderCount(parseInt(e.target.value, 10))}
                  className="w-full accent-[#FC8019] cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-[#93959F] mt-1">
                  <span>1 order (single inspect)</span>
                  <span>5 orders</span>
                  <span>20 orders (batch test)</span>
                </div>
              </div>

              {/* Reproducible Seed Input */}
              <div>
                <label className="block text-xs font-bold text-[#282C3F] mb-1.5">
                  Reproducible Seed Number (Optional)
                </label>
                <div className="relative">
                  <Hash className="w-4 h-4 text-[#93959F] absolute left-3 top-2.5" />
                  <input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    placeholder="e.g. 42 (leave empty for random)"
                    className="w-full pl-9 pr-4 py-2 bg-[#F8F9FA] focus:bg-white text-xs text-[#282C3F] placeholder-[#93959F] rounded-xl border border-[#E9ECEE] focus:outline-none focus:border-[#FC8019]"
                  />
                </div>
                <p className="text-[11px] text-[#93959F] mt-1">
                  Optional: using the same seed number generates identical test conditions.
                </p>
              </div>
            </div>

            {/* Primary Simulation CTA Button */}
            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={simulating}
                className="px-6 py-3 rounded-xl bg-[#FC8019] hover:bg-[#e67312] text-white text-xs font-bold flex items-center gap-2 shadow-[0_4px_16px_rgba(252,128,25,0.25)] transition-all disabled:opacity-50"
              >
                {simulating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Creating Demo Orders...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4" />
                    Generate Demo Orders
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Summary Section */}
          {result && (
            <div className="bg-white rounded-2xl border border-[#E9ECEE] p-6 shadow-[0_2px_8px_rgba(40,44,63,0.04)] space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#F4F5F7]">
                <div>
                  <h3 className="text-sm font-bold text-[#282C3F]">
                    Demo Orders Created
                  </h3>
                  <p className="text-xs text-[#686B78] mt-0.5">
                    Batch Reference ID: <span className="font-mono text-[#FC8019]">{result.demo_run_id}</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[#F2FBF2] text-[#60B246] border border-[#C6E7C6]">
                    {result.generated_count} Demo Order(s)
                  </span>
                  <Link
                    href={`/orders?demo_run_id=${result.demo_run_id}`}
                    className="text-xs font-bold px-3 py-1.5 rounded-xl bg-[#FC8019] text-white hover:bg-[#e67312] transition-colors flex items-center gap-1"
                  >
                    View in All Orders
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              {/* Order Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                {result.orders.map((o) => (
                  <div
                    key={o.id}
                    className="p-4 rounded-xl border border-[#E9ECEE] bg-[#FAFAFA] hover:bg-white hover:border-[#FC8019] transition-all space-y-2.5"
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-mono font-bold text-[#282C3F]">
                        {o.external_order_id}
                      </span>
                      <OrderStatusBadge status={o.order_status} />
                    </div>

                    <div className="text-xs text-[#686B78] space-y-1">
                      <div className="flex items-center gap-1.5">
                        <Store className="w-3.5 h-3.5 text-[#93959F]" />
                        <span className="font-medium truncate">{o.restaurant_name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-[#93959F]" />
                        <span>Status: {o.is_delayed ? 'Delayed' : 'On Track'}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-[#E9ECEE] flex justify-between items-center text-[11px]">
                      <span className="text-[#93959F]">₹{o.order_value}</span>
                      <Link
                        href={`/orders/${o.id}`}
                        className="text-[#FC8019] font-bold hover:underline flex items-center gap-0.5"
                      >
                        View Details
                        <ChevronRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </form>
      )}
    </div>
  );
}
