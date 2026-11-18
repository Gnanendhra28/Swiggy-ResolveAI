export type ScenarioType =
  | 'NORMAL_ORDER'
  | 'RESTAURANT_DELAY'
  | 'DELIVERY_DELAY'
  | 'ASSIGNMENT_DELAY'
  | 'FAILED_RECOVERY'
  | 'SUCCESSFUL_RECOVERY';

export interface Customer {
  id: string;
  name: string;
  phone: string;
  created_at: string;
}

export interface Restaurant {
  id: string;
  name: string;
  city: string;
  area: string;
  cuisine: string;
  rating?: number | null;
  rating_count?: number | null;
  average_price?: number | null;
  number_of_offers: number;
  offer_name?: string | null;
  pure_veg: boolean;
  location?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at: string;
}

export interface DeliveryPartner {
  id: string;
  name: string;
  availability_status: string;
  external_rider_id?: string | null;
  created_at: string;
}

export interface OrderEvent {
  id: string;
  order_id: string;
  event_type: string;
  event_timestamp: string;
  metadata: Record<string, any>;
  data_source: string;
  created_at: string;
}

export interface OrderSummary {
  id: string;
  external_order_id: string;
  customer_id: string;
  customer_name?: string | null;
  restaurant_id: string;
  restaurant_name?: string | null;
  restaurant_city?: string | null;
  delivery_partner_id?: string | null;
  delivery_partner_name?: string | null;
  order_status: string;
  order_value: number;
  promised_delivery_at: string;
  created_at: string;
  updated_at: string;
  demo_run_id?: string | null;
  data_source: string;
  event_count: number;
  is_delayed: boolean;
}

export interface OrderDetail {
  id: string;
  external_order_id: string;
  order_status: string;
  order_value: number;
  promised_delivery_at: string;
  created_at: string;
  updated_at: string;
  demo_run_id?: string | null;
  data_source: string;
  customer: Customer;
  restaurant: Restaurant;
  delivery_partner?: DeliveryPartner | null;
  events: OrderEvent[];
  is_delayed: boolean;
}

export interface PaginatedOrders {
  items: OrderSummary[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface DashboardMetrics {
  total_orders: number;
  active_orders: number;
  delivered_orders: number;
  delayed_orders: number;
  status_distribution: Record<string, number>;
  recent_activity: {
    id: string;
    order_id: string;
    external_order_id: string;
    restaurant_name: string;
    event_type: string;
    event_timestamp: string;
    metadata: Record<string, any>;
    data_source: string;
  }[];
}

export interface ScenarioMeta {
  id: ScenarioType;
  title: string;
  description: string;
  expected_status: string;
  has_delays: boolean;
}

export interface SimulationResult {
  demo_run_id: string;
  scenario: ScenarioType;
  generated_count: number;
  order_ids: string[];
  orders: OrderSummary[];
}

export interface ApplicationHealthInfo {
  name: string;
  status: string;
  version: string;
  environment: string;
}

export interface InfrastructureHealthInfo {
  database_status: string;
  database_engine: string;
  database_latency_ms: number;
  connection_pooling: Record<string, any>;
}

export interface AIProviderHealthInfo {
  provider_name: string;
  status: string;
  model_name: string;
  fallback_engine_available: boolean;
  details: string;
}

export interface MLArtifactHealthInfo {
  status: string;
  model_version: string;
  task_a_quantiles: boolean;
  task_c2_calibrated: boolean;
  registry_loaded: boolean;
  artifacts_dir: string;
}

export interface SystemHealth {
  status: string;
  database: string;
  version: string;
  environment?: string;
  timestamp: string;
  application?: ApplicationHealthInfo;
  infrastructure?: InfrastructureHealthInfo;
  ai_provider?: AIProviderHealthInfo;
  ml_artifacts?: MLArtifactHealthInfo;
}


export interface RecommendationResponse {
  id: string;
  investigation_id: string;
  order_id: string;
  action_type: string;
  title: string;
  rationale: string;
  sensitivity_level: string;
  estimated_impact?: string | null;
  requires_approval: boolean;
  approval_status: string;
  approved_by?: string | null;
  operator_role?: string | null;
  approval_notes?: string | null;
  approval_timestamp?: string | null;
  expires_at?: string | null;
  execution_status: string;
  execution_payload: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface MLPredictionAuditResponse {
  id: string;
  order_id: string;
  model_version: string;
  feature_schema_version: string;
  task_a_eta_p50?: number | null;
  task_a_interval_min?: number | null;
  task_a_interval_max?: number | null;
  task_a_is_long_tail: boolean;
  task_c2_is_eligible: boolean;
  task_c2_calibrated_prob?: number | null;
  task_c2_alert_5k: boolean;
  task_c2_alert_10k: boolean;
  task_b_score?: number | null;
  task_c1_score?: number | null;
  provenance_metadata: Record<string, any>;
  prediction_timestamp: string;
}

export interface InvestigationResponse {
  id: string;
  order_id: string;
  status: string;
  risk_tier: 'NOMINAL' | 'MONITORED' | 'HIGH_RISK' | 'CRITICAL';
  trigger_event?: string | null;
  eta_p10?: number | null;
  eta_p50?: number | null;
  eta_p90?: number | null;
  eta_interval_width?: number | null;
  is_long_tail: boolean;
  cancellation_probability?: number | null;
  cancellation_alert_budget_10k: boolean;
  ml_provenance: Record<string, any>;
  restaurant_evidence: Record<string, any>;
  delivery_evidence: Record<string, any>;
  agent_reasoning: Record<string, any>;
  workflow_execution: Record<string, any>;
  recommendations: RecommendationResponse[];
  created_at: string;
  updated_at: string;
}

export interface ExecutionAuditResponse {
  id: string;
  recommendation_id: string;
  order_id: string;
  action_type: string;
  initial_order_status: string;
  final_order_status: string;
  idempotency_key: string;
  trigger_reason: string;
  ml_model_version: string;
  approval_identity?: string | null;
  approval_timestamp?: string | null;
  execution_result: Record<string, any>;
  recovery_outcome: string;
  is_simulated: boolean;
  executed_at: string;
}


// ============================================================================
// Phase 5: Simulation Experiments & Counterfactual KPI Types
// ============================================================================

export interface StrategyKPIDelivery {
  on_time_delivery_rate_pct: number;
  average_delivery_duration_min: number;
  median_delivery_duration_min: number;
  p90_delivery_duration_min: number;
  eta_absolute_error_min?: number | null;
  eta_interval_coverage_pct?: number | null;
  long_tail_interval_undercoverage_pct: number;
}

export interface StrategyKPICancellation {
  overall_cancellation_rate_pct: number;
  post_landmark_cancellation_rate_pct: number;
  cancellation_detection_recall_pct: number;
  cancellation_detection_precision_pct: number;
  false_positive_rate_pct: number;
  missed_cancellations_count: number;
  total_cancellations: number;
}

export interface StrategyKPIOperational {
  average_restaurant_delay_min: number;
  average_courier_assignment_delay_min: number;
  courier_reassignment_rate_pct: number;
  recovery_success_rate_pct: number;
  average_time_to_intervention_min?: number | null;
  average_time_to_recovery_min?: number | null;
}

export interface StrategyKPIAgent {
  investigation_success_rate_pct: number;
  agent_failure_rate_pct: number;
  workflow_completion_rate_pct: number;
  average_investigation_latency_ms: number;
  recommendations_per_order: number;
  approval_rate_pct: number;
  rejection_rate_pct: number;
}

export interface StrategyKPIBusiness {
  total_interventions_count: number;
  simulated_intervention_cost_inr: number;
  cost_per_successful_recovery_inr: number;
  cancellations_prevented_count: number;
  estimated_cancellation_losses_avoided_inr: number;
  net_simulated_operational_benefit_inr: number;
  assumed_gross_order_value_inr: number;
}

export interface StrategyKPIGroup {
  delivery: StrategyKPIDelivery;
  cancellation: StrategyKPICancellation;
  operational: StrategyKPIOperational;
  agent: StrategyKPIAgent;
  business_efficiency: StrategyKPIBusiness;
}

export interface CounterfactualComparisonItem {
  candidate_name: string;
  reference_name: string;
  sample_size: number;
  duration: {
    metric_name: string;
    reference_mean: number;
    candidate_mean: number;
    mean_difference: number;
    median_difference: number;
    std_difference: number;
    cohens_d: number;
    ci_95: [number, number];
    p_value: number;
    statistically_significant_0_05: boolean;
    test_type: string;
  };
  ontime: {
    difference_pct: number;
    ci_95: [number, number];
    p_value: number;
    statistically_significant: boolean;
  };
  cancellation: {
    difference_pct: number;
    ci_95: [number, number];
    p_value: number;
    statistically_significant: boolean;
  };
  net_benefit_difference_inr: number;
  provenance: string;
  causal_claim_caveat: string;
}

export interface ActionEffectivenessItem {
  action_type: string;
  description: string;
  sample_evaluated: number;
  triggered_count: number;
  trigger_frequency_pct: number;
  successful_recoveries_count: number;
  action_success_rate_pct: number;
  average_delay_reduction_min: number;
  median_delay_reduction_min: number;
  cancellation_reduction_pct: number;
  unit_cost_inr: number;
  total_cost_inr: number;
  cost_per_successful_recovery_inr: number;
  estimated_losses_avoided_inr: number;
  net_simulated_benefit_inr: number;
  simulated_roi_ratio: number;
  provenance: string;
}

export interface StressTestItem {
  dimension_key: string;
  dimension_name: string;
  stress_parameters: Record<string, any>;
  sample_size: number;
  baseline_ontime_pct: number;
  multi_agent_ontime_pct: number;
  ontime_delta_pct: number;
  baseline_cancellation_pct: number;
  multi_agent_cancellation_pct: number;
  cancellation_delta_pct: number;
  baseline_avg_duration_min: number;
  multi_agent_avg_duration_min: number;
  duration_delta_min: number;
  net_operational_benefit_inr: number;
  resilience_verdict: 'ROBUST' | 'MODERATELY_DEGRADED' | 'SEVERE_BOTTLENECK';
  operational_observation: string;
  provenance: string;
}

export interface SimulationExperimentDetail {
  id: string;
  name: string;
  scenario_type: string;
  random_seed: number;
  num_orders: number;
  config_parameters: Record<string, any>;
  strategies_evaluated: string[];
  kpi_results: Record<string, StrategyKPIGroup>;
  counterfactual_comparisons: {
    comparisons: CounterfactualComparisonItem[];
  };
  action_effectiveness: {
    actions: ActionEffectivenessItem[];
  };
  created_at: string;
  provenance?: string;
}

export interface SimulationExperimentSummary {
  id: string;
  name: string;
  scenario_type: string;
  random_seed: number;
  num_orders: number;
  created_at: string;
  kpi_summary: Record<string, {
    on_time_rate_pct?: number | null;
    cancellation_rate_pct?: number | null;
    avg_duration_min?: number | null;
    net_benefit_inr?: number | null;
  }>;
}
