/**
 * Swiggy ResolveAI — Presentation & User-Friendly Language Utilities
 *
 * Translates machine learning and engineering terminology into clear,
 * business-oriented language for restaurant operators and delivery operations managers.
 *
 * Preserves all underlying technical semantics while ensuring default views
 * answer the 5 core operational questions:
 * 1. What happened?
 * 2. Why might it have happened?
 * 3. What could happen next?
 * 4. What action is recommended?
 * 5. Does it require manager approval?
 */

import { OrderDetail, OrderSummary, InvestigationResponse, RecommendationResponse } from './types';

// ============================================================================
// 1. CONSISTENT TERMINOLOGY DICTIONARY
// ============================================================================

export const TERMS = {
  // Navigation & Core Features
  orderIntelligence: 'Order Insights',
  multiAgentInvestigation: 'AI Order Investigation',
  operationalRiskTier: 'Order Risk',
  etaQuantiles: 'Estimated Delivery Time Range',
  cancellationProbability: 'Cancellation Risk',
  
  // Specialized Agent Roles
  restaurantAgent: 'Restaurant Status Check',
  deliveryAgent: 'Delivery Partner Status',
  customerResolutionAgent: 'Resolution Assistant',
  
  // Actions & Governance
  recoveryRecommendation: 'Suggested Action',
  humanInTheLoop: 'Requires Manager Approval',
  policyEngine: 'Action Approval Rules',
  recoveryExecutor: 'Action Processor',
  idempotency: 'Duplicate Action Protection',
  counterfactualEvaluation: 'Recovery Strategy Comparison',
  
  // Audits & Data
  modelPredictionAudit: 'Prediction History',
  mlProvenance: 'Prediction Details',
  syntheticOrder: 'Demo Order',
  historicalDataset: 'Historical Order Data',
  databaseHealth: 'Data Connection Status',
  shadowMode: 'Monitoring Only',
  executionAudit: 'Action History',
} as const;

// ============================================================================
// 2. STATUS & RISK FORMATTERS
// ============================================================================

export function formatRiskTier(tier?: string): {
  label: string;
  badgeClass: string;
  dotClass: string;
  description: string;
} {
  switch ((tier || '').toUpperCase()) {
    case 'CRITICAL':
      return {
        label: 'Critical Risk',
        badgeClass: 'bg-red-50 text-red-700 border-red-200',
        dotClass: 'bg-red-600',
        description: 'Severe delay detected. Customer satisfaction and SLA at imminent risk.',
      };
    case 'HIGH_RISK':
      return {
        label: 'High Delay Risk',
        badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
        dotClass: 'bg-amber-500',
        description: 'Noticeable delay expected. Proactive action recommended to prevent cancellation.',
      };
    case 'MONITORED':
      return {
        label: 'Under Monitoring',
        badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
        dotClass: 'bg-blue-500',
        description: 'Minor variance detected. System is keeping a close watch on prep and courier progress.',
      };
    case 'ON_TRACK':
    case 'NORMAL':
    default:
      return {
        label: 'On Track',
        badgeClass: 'bg-[#EDF7EC] text-[#2E7D32] border-[#C8E6C9]',
        dotClass: 'bg-[#60B246]',
        description: 'Delivery is proceeding normally within the promised timeframe.',
      };
  }
}

export function formatDataSource(source?: string): {
  label: string;
  shortLabel: string;
  description: string;
  badgeClass: string;
} {
  switch ((source || '').toUpperCase()) {
    case 'SYNTHETIC':
      return {
        label: 'Demo Order (Simulated)',
        shortLabel: 'Demo',
        description: 'Created in a simulated testing environment to demonstrate delay resolution.',
        badgeClass: 'bg-[#FFF5ED] text-[#FC8019] border-[#FED7AA]',
      };
    case 'PUBLIC_HISTORICAL':
      return {
        label: 'Historical Order Data',
        shortLabel: 'Historical',
        description: 'Archived public food delivery record used for baseline accuracy comparisons.',
        badgeClass: 'bg-gray-100 text-gray-700 border-gray-200',
      };
    default:
      return {
        label: 'Standard Order',
        shortLabel: 'Order',
        description: 'Operational delivery record.',
        badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
      };
  }
}

export function formatActionType(actionType?: string): {
  title: string;
  summary: string;
  iconType: 'voucher' | 'notification' | 'reassign' | 'kitchen' | 'general';
} {
  switch ((actionType || '').toUpperCase()) {
    case 'APOLOGY_CREDIT_VOUCHER':
      return {
        title: 'Customer Apology Voucher (₹50)',
        summary: 'Issues an automated ₹50 wallet credit to customer account for excessive delay.',
        iconType: 'voucher',
      };
    case 'PROACTIVE_CUSTOMER_NOTIFICATION':
      return {
        title: 'Proactive Delay Notification',
        summary: 'Sends an honest, empathetic progress update before customer needs to reach out.',
        iconType: 'notification',
      };
    case 'REASSIGN_DELIVERY_PARTNER':
      return {
        title: 'Reassign to Nearby Delivery Partner',
        summary: 'Replaces stalled or unresponsive courier with the nearest available partner.',
        iconType: 'reassign',
      };
    case 'ESCALATE_TO_RESTAURANT':
    case 'EXPEDITE_KITCHEN_PREP':
      return {
        title: 'Restaurant Kitchen Priority Check',
        summary: 'Alerts merchant kitchen staff to prioritize packaging this delayed order.',
        iconType: 'kitchen',
      };
    default:
      return {
        title: (actionType || 'Resolution Action').replace(/_/g, ' '),
        summary: 'Targeted operational recovery action.',
        iconType: 'general',
      };
  }
}

export function formatRoleLabel(role: string): string {
  switch (role) {
    case 'OPS_LEAD':
      return 'Operations Lead (Can Approve)';
    case 'OPERATOR':
      return 'Operations Manager (Can Approve)';
    case 'SUPERVISOR':
      return 'Shift Supervisor (Can Approve)';
    case 'JUNIOR_INTERN':
      return 'Support Intern (Read-Only • Approval Blocked)';
    default:
      return role;
  }
}

// ============================================================================
// 3. FIVE CORE QUESTIONS EXPLANATION BUILDER
// ============================================================================

export interface OrderOperationalStory {
  whatHappened: string;
  whyItHappened: string;
  whatCouldHappen: string;
  recommendedAction: string;
  requiresManagerApproval: boolean;
  approvalDetail: string;
  confidenceNote: string;
}

export function getOrderOperationalStory(
  order: OrderDetail | OrderSummary,
  investigation?: InvestigationResponse | null,
  recommendations?: RecommendationResponse[]
): OrderOperationalStory {
  const isDelayed = order.is_delayed;
  const status = (order.order_status || '').toUpperCase();
  const restEv = investigation?.restaurant_evidence || {};
  const delivEv = investigation?.delivery_evidence || {};
  const mlProv = investigation?.ml_provenance || {};
  const taskA = mlProv.task_a_eta || {};
  const taskC2 = mlProv.task_c2_cancellation || {};

  // 1. What Happened?
  let whatHappened = 'Order is currently progressing through normal delivery stages.';
  if (status === 'DELIVERED') {
    whatHappened = isDelayed
      ? 'Order was delivered to customer, but exceeded the initial promised delivery window.'
      : 'Order was successfully delivered to the customer on time.';
  } else if (status === 'RECOVERED') {
    whatHappened = 'Order encountered a delay, but automated support actions successfully resolved the issue.';
  } else if (status === 'ESCALATED' || status === 'CANCELLED') {
    whatHappened = 'Order encountered severe delivery bottlenecks and required operational escalation.';
  } else if (isDelayed) {
    whatHappened = 'Order is currently active but is running behind its promised delivery schedule.';
  } else if (status === 'PREPARING') {
    whatHappened = 'Food is currently being prepared in the restaurant kitchen.';
  } else if (status === 'OUT_FOR_DELIVERY') {
    whatHappened = 'Food has been picked up by the delivery partner and is en route to customer doorstep.';
  }

  // 2. Why might it have happened?
  let whyItHappened = 'Preparation and transit times are within standard operational limits.';
  if (restEv.prep_delay_min && restEv.prep_delay_min > 5) {
    whyItHappened = `Kitchen preparation backlog: restaurant required +${restEv.prep_delay_min} extra minutes due to high order volume.`;
  } else if (delivEv.transit_congestion_factor && parseFloat(delivEv.transit_congestion_factor) > 1.2) {
    whyItHappened = `Heavy road traffic along the delivery corridor slowed courier transit (${delivEv.transit_congestion_factor}x slowdown).`;
  } else if (delivEv.reassignment_count && delivEv.reassignment_count > 0) {
    whyItHappened = `Delivery partner search experienced delays (${delivEv.reassignment_count} courier reassignment logged).`;
  } else if (isDelayed) {
    whyItHappened = 'Combined kitchen handling and peak-hour delivery transit caused cumulative delay.';
  }

  // 3. What could happen next?
  let whatCouldHappen = 'Order is projected to arrive smoothly without customer intervention.';
  if (taskA.eta_p50_min) {
    const p10 = taskA.eta_p10_min;
    const p50 = taskA.eta_p50_min;
    const p90 = taskA.eta_p90_min;
    const cancelProb = taskC2.calibrated_probability
      ? (taskC2.calibrated_probability * 100).toFixed(0)
      : null;

    if (isDelayed || (investigation && investigation.risk_tier !== 'NOMINAL')) {
      whatCouldHappen = `Expected arrival between ${p10}–${p90} mins (most likely ~${p50} mins). ${
        cancelProb && parseInt(cancelProb) > 10
          ? `Estimated ${cancelProb}% risk of customer cancellation if delay remains unaddressed.`
          : 'Low immediate cancellation risk if kept informed.'
      }`;
    } else {
      whatCouldHappen = `Expected arrival between ${p10}–${p90} mins (most likely ~${p50} mins). Delivery on schedule.`;
    }
  } else if (isDelayed) {
    whatCouldHappen = 'Customer may inquire with support or request cancellation if not notified proactively.';
  }

  // 4. What action is recommended?
  let recommendedAction = 'No immediate action required. Continue passive monitoring.';
  let requiresManagerApproval = false;
  let approvalDetail = 'Automatic execution / Monitoring Only';

  if (recommendations && recommendations.length > 0) {
    const firstRec = recommendations[0];
    const actionMeta = formatActionType(firstRec.action_type);
    recommendedAction = `${actionMeta.title}: ${firstRec.title || actionMeta.summary}`;
    requiresManagerApproval = firstRec.requires_approval;
    approvalDetail = requiresManagerApproval
      ? 'Requires Manager Approval (involves customer compensation or dispatch change)'
      : 'Pre-Approved (can run automatically)';
  } else if (investigation?.agent_reasoning?.root_cause_summary) {
    recommendedAction = investigation.agent_reasoning.root_cause_summary;
  }

  return {
    whatHappened,
    whyItHappened,
    whatCouldHappen,
    recommendedAction,
    requiresManagerApproval,
    approvalDetail,
    confidenceNote: 'Forecasts are statistical predictions based on historical patterns, not guaranteed delivery times.',
  };
}

// ============================================================================
// 4. DELIVERY TIME RANGE HELPER
// ============================================================================

export function formatDeliveryRange(
  p10?: number | null,
  p50?: number | null,
  p90?: number | null
): {
  headline: string;
  rangeText: string;
  explanation: string;
} {
  if (p50 === undefined || p50 === null) {
    return {
      headline: 'Awaiting delivery estimate',
      rangeText: 'Timing being calculated',
      explanation: 'Checking restaurant preparation and traffic patterns...',
    };
  }

  const p10Val = p10 ?? Math.max(5, Math.round(p50 * 0.7));
  const p90Val = p90 ?? Math.round(p50 * 1.5);

  return {
    headline: `~${p50} mins`,
    rangeText: `Expected ${p10Val} to ${p90Val} mins (80% confidence window)`,
    explanation: `Fastest expected ~${p10Val}m • Typical ~${p50}m • Latest expected ~${p90Val}m`,
  };
}
