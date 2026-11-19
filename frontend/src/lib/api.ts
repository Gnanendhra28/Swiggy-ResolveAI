import {
  DashboardMetrics,
  OrderDetail,
  OrderEvent,
  PaginatedOrders,
  ScenarioMeta,
  ScenarioType,
  SimulationResult,
  SystemHealth,
  InvestigationResponse,
  RecommendationResponse,
  ExecutionAuditResponse,
  MLPredictionAuditResponse,
} from './types';

/**
 * Resolves the API base URL depending on execution environment:
 * 1. Explicit NEXT_PUBLIC_API_URL if configured.
 * 2. In browser (client-side): uses window.location.origin + '/api/v1', routing through Vercel's /api/(.*) rewrite.
 * 3. On server (SSR / Route Handlers): uses Vercel's injected internal service binding BACKEND_URL.
 * 4. Local standalone development fallback: http://localhost:8000/api/v1.
 */
export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    // If running in local development on port 3000 without explicit NEXT_PUBLIC_API_URL,
    // point directly to the backend on port 8000
    if (
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') &&
      window.location.port === '3000'
    ) {
      return 'http://localhost:8000/api/v1';
    }
    return `${window.location.origin}/api/v1`;
  }
  if (process.env.BACKEND_URL) {
    return `${process.env.BACKEND_URL.replace(/\/$/, '')}/api/v1`;
  }
  return 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const text = await res.text();
      try {
        const errorJson = JSON.parse(text);
        errorDetail =
          errorJson.error?.message ||
          errorJson.detail ||
          text;
      } catch {
        errorDetail = text || `HTTP ${res.status}`;
      }
    } catch {
      errorDetail = `HTTP ${res.status} (${res.statusText})`;
    }
    throw new Error(`[${res.status}] ${errorDetail}`);
  }
  return res.json();
}

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE_URL}/health`, { cache: 'no-store' });
  return handleResponse<SystemHealth>(res);
}

export async function fetchMetrics(): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE_URL}/orders/metrics`, {
    cache: 'no-store',
  });
  return handleResponse<DashboardMetrics>(res);
}

export async function fetchOrders(params: {
  page?: number;
  limit?: number;
  status?: string;
  demo_run_id?: string;
  data_source?: string;
  search?: string;
}): Promise<PaginatedOrders> {
  const url = new URL(`${API_BASE_URL}/orders`);
  if (params.page) url.searchParams.set('page', params.page.toString());
  if (params.limit) url.searchParams.set('limit', params.limit.toString());
  if (params.status) url.searchParams.set('status', params.status);
  if (params.demo_run_id) url.searchParams.set('demo_run_id', params.demo_run_id);
  if (params.data_source) url.searchParams.set('data_source', params.data_source);
  if (params.search) url.searchParams.set('search', params.search);

  const res = await fetch(url.toString(), { cache: 'no-store' });
  return handleResponse<PaginatedOrders>(res);
}

export async function fetchOrderById(orderId: string): Promise<OrderDetail> {
  const res = await fetch(`${API_BASE_URL}/orders/${orderId}`, {
    cache: 'no-store',
  });
  return handleResponse<OrderDetail>(res);
}

export async function fetchOrderEvents(orderId: string): Promise<OrderEvent[]> {
  const res = await fetch(`${API_BASE_URL}/orders/${orderId}/events`, {
    cache: 'no-store',
  });
  return handleResponse<OrderEvent[]>(res);
}

export async function fetchSimulationScenarios(): Promise<ScenarioMeta[]> {
  const res = await fetch(`${API_BASE_URL}/simulation/scenarios`, {
    cache: 'no-store',
  });
  const data = await handleResponse<{ scenarios: ScenarioMeta[] }>(res);
  return data.scenarios;
}

export async function triggerSimulation(payload: {
  scenario: ScenarioType;
  count: number;
  seed?: number | null;
  custom_params?: Record<string, any>;
}): Promise<SimulationResult> {
  const res = await fetch(`${API_BASE_URL}/simulation/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<SimulationResult>(res);
}

export async function injectOrderEvent(payload: {
  order_id: string;
  event_type: string;
  metadata: Record<string, any>;
  data_source?: string;
}): Promise<OrderEvent> {
  const res = await fetch(`${API_BASE_URL}/simulation/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<OrderEvent>(res);
}


// ----------------------------------------------------------------------------
// Phase 3 Multi-Agent Intelligence & Recovery APIs
// ----------------------------------------------------------------------------

export async function triggerInvestigation(
  orderId: string,
  triggerEvent: string = 'MANUAL_OPERATOR_TRIGGER'
): Promise<InvestigationResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/investigate/${orderId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trigger_event: triggerEvent }),
  });
  return handleResponse<InvestigationResponse>(res);
}

export async function fetchInvestigation(
  investigationId: string
): Promise<InvestigationResponse> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/investigations/${investigationId}`,
    { cache: 'no-store' }
  );
  return handleResponse<InvestigationResponse>(res);
}

export async function fetchLatestOrderInvestigation(
  orderId: string
): Promise<InvestigationResponse | null> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/orders/${orderId}/latest`,
    { cache: 'no-store' }
  );
  if (res.status === 404 || res.status === 204) return null;
  return handleResponse<InvestigationResponse>(res);
}

export async function fetchPredictions(orderId: string): Promise<Record<string, any>> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/predictions/${orderId}`,
    { cache: 'no-store' }
  );
  return handleResponse<Record<string, any>>(res);
}

export async function fetchRecommendations(params?: {
  order_id?: string;
  pending_only?: boolean;
  limit?: number;
}): Promise<RecommendationResponse[]> {
  const url = new URL(`${API_BASE_URL}/intelligence/recommendations`);
  if (params?.order_id) url.searchParams.set('order_id', params.order_id);
  if (params?.pending_only !== undefined)
    url.searchParams.set('pending_only', params.pending_only.toString());
  if (params?.limit) url.searchParams.set('limit', params.limit.toString());

  const res = await fetch(url.toString(), { cache: 'no-store' });
  return handleResponse<RecommendationResponse[]>(res);
}

export async function approveRecommendation(
  recommendationId: string,
  payload: { operator_identity?: string; operator_role?: string; notes?: string } = {}
): Promise<RecommendationResponse> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/recommendations/${recommendationId}/approve`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operator_identity: payload.operator_identity || 'ops_lead',
        operator_role: payload.operator_role || 'OPS_LEAD',
        notes: payload.notes || 'Approved in ResolveAI Operations Control',
      }),
    }
  );
  return handleResponse<RecommendationResponse>(res);
}

export async function rejectRecommendation(
  recommendationId: string,
  payload: { operator_identity?: string; operator_role?: string; reason: string }
): Promise<RecommendationResponse> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/recommendations/${recommendationId}/reject`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operator_identity: payload.operator_identity || 'ops_lead',
        operator_role: payload.operator_role || 'OPS_LEAD',
        reason: payload.reason,
      }),
    }
  );
  return handleResponse<RecommendationResponse>(res);
}

export async function executeRecommendation(
  recommendationId: string,
  payload: { operator_identity?: string; operator_role?: string } = {}
): Promise<Record<string, any>> {
  const res = await fetch(
    `${API_BASE_URL}/intelligence/recommendations/${recommendationId}/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operator_identity: payload.operator_identity || 'ops_lead',
        operator_role: payload.operator_role || 'OPS_LEAD',
      }),
    }
  );
  return handleResponse<Record<string, any>>(res);
}

export async function fetchOrderAudits(
  orderId: string
): Promise<ExecutionAuditResponse[]> {
  const res = await fetch(`${API_BASE_URL}/intelligence/audit/${orderId}`, {
    cache: 'no-store',
  });
  return handleResponse<ExecutionAuditResponse[]>(res);
}

export async function fetchOrderMLAudits(
  orderId: string
): Promise<MLPredictionAuditResponse[]> {
  const res = await fetch(`${API_BASE_URL}/intelligence/ml-audits/${orderId}`, {
    cache: 'no-store',
  });
  return handleResponse<MLPredictionAuditResponse[]>(res);
}


// ============================================================================
// Phase 5: Simulation Experiments & Counterfactual KPI API Methods
// ============================================================================

import type {
  SimulationExperimentDetail,
  SimulationExperimentSummary,
  StressTestItem,
  ActionEffectivenessItem,
} from './types';

export async function runSimulationExperiment(payload: {
  name?: string;
  scenario_type?: string;
  order_volume?: number;
  random_seed?: number;
  prep_time_base_min?: number;
  kitchen_queue_length?: number;
  restaurant_capacity?: number;
  courier_availability_ratio?: number;
  courier_acceptance_delay_min?: number;
  first_mile_distance_km?: number;
  last_mile_distance_km?: number;
  traffic_congestion_factor?: number;
  recovery_action_effectiveness?: number;
  gross_order_value_inr?: number;
}): Promise<SimulationExperimentDetail> {
  const res = await fetch(`${API_BASE_URL}/simulation/experiments/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<SimulationExperimentDetail>(res);
}

export async function fetchSimulationExperiments(params: {
  limit?: number;
  offset?: number;
} = {}): Promise<{ total: number; experiments: SimulationExperimentSummary[] }> {
  const url = new URL(`${API_BASE_URL}/simulation/experiments`);
  if (params.limit) url.searchParams.set('limit', params.limit.toString());
  if (params.offset) url.searchParams.set('offset', params.offset.toString());

  const res = await fetch(url.toString(), { cache: 'no-store' });
  return handleResponse<{ total: number; experiments: SimulationExperimentSummary[] }>(res);
}

export async function fetchSimulationExperimentById(
  experimentId: string
): Promise<SimulationExperimentDetail> {
  const res = await fetch(`${API_BASE_URL}/simulation/experiments/${experimentId}`, {
    cache: 'no-store',
  });
  return handleResponse<SimulationExperimentDetail>(res);
}

export async function runStressTest(payload: {
  base_volume?: number;
  seed?: number;
} = {}): Promise<{
  status: string;
  base_volume: number;
  seed: number;
  total_dimensions: number;
  stress_test_matrix: StressTestItem[];
  provenance: string;
}> {
  const res = await fetch(`${API_BASE_URL}/simulation/experiments/stress-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<{
    status: string;
    base_volume: number;
    seed: number;
    total_dimensions: number;
    stress_test_matrix: StressTestItem[];
    provenance: string;
  }>(res);
}

export async function fetchActionEffectiveness(params: {
  scenario_type?: string;
  order_volume?: number;
  random_seed?: number;
} = {}): Promise<{
  scenario_type: string;
  order_volume: number;
  random_seed: number;
  actions: ActionEffectivenessItem[];
  provenance: string;
}> {
  const url = new URL(`${API_BASE_URL}/simulation/experiments/actions/effectiveness`);
  if (params.scenario_type) url.searchParams.set('scenario_type', params.scenario_type);
  if (params.order_volume) url.searchParams.set('order_volume', params.order_volume.toString());
  if (params.random_seed) url.searchParams.set('random_seed', params.random_seed.toString());

  const res = await fetch(url.toString(), { cache: 'no-store' });
  return handleResponse<{
    scenario_type: string;
    order_volume: number;
    random_seed: number;
    actions: ActionEffectivenessItem[];
    provenance: string;
  }>(res);
}
