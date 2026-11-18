import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.logging import logger
from backend.app.agents.schemas import ActionType, SensitivityLevel, ApprovalStatus


class PolicyEngine:
    """
    Deterministic Policy and Approval Engine.
    Enforces operational boundaries, business eligibility, idempotency,
    role-based authorization, communication consent, and human-in-the-loop gates.
    The LLM is strictly prohibited from directly executing sensitive actions.
    """

    SENSITIVE_ACTIONS = {
        ActionType.REASSIGN_COURIER,
        ActionType.APOLOGY_CREDIT_VOUCHER,
    }

    AUTO_APPROVABLE_ACTIONS = {
        ActionType.MONITOR_ORDER,
        ActionType.EXPEDITE_KITCHEN_PING,
        ActionType.PRIORITIZE_COURIER_DISPATCH,
        ActionType.PROACTIVE_CUSTOMER_NOTIFICATION,
    }

    AUTHORIZED_ROLES = {
        "OPERATOR",
        "OPS_LEAD",
        "ADMIN",
        "SUPERVISOR",
        "OpsLead_Console",
        "lead_ops_officer",
        "ops_admin",
    }

    UNAUTHORIZED_IDENTITIES = {
        "GUEST",
        "ANONYMOUS",
        "UNAUTHORIZED",
        "UNAUTHORIZED_OPERATOR",
        "READ_ONLY_VIEWER",
    }

    @classmethod
    def check_operator_authorization(
        cls,
        operator_identity: str,
        role: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validates operator role-based authorization for approving sensitive recovery actions.
        """
        if not operator_identity or operator_identity in cls.UNAUTHORIZED_IDENTITIES:
            return False, f"Operator '{operator_identity}' is not authorized to approve sensitive actions."

        if role:
            role_norm = role.upper().strip()
            if role_norm not in {r.upper() for r in cls.AUTHORIZED_ROLES}:
                return False, f"Role '{role}' is not permitted to approve recovery operations."

        return True, "Operator authorization confirmed."

    @classmethod
    def generate_idempotency_key(cls, order_id: str, action_type: str, disambiguator: str = "") -> str:
        raw = f"{order_id}:{action_type}:{disambiguator}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def check_recommendation_expiry(
        cls,
        expires_at: Optional[Any],
        now: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Validates whether a recommendation has exceeded its 30-minute validity window.
        """
        if expires_at is None:
            return False, "No expiration set"

        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except Exception:
                return False, "Unparseable expiration timestamp"

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now > expires_at:
            return True, f"Recommendation expired at {expires_at.isoformat()} (now: {now.isoformat()})"
        return False, "Recommendation is within validity window"

    @classmethod
    def check_fleet_availability_threshold(
        cls,
        courier_availability_ratio: float,
        threshold: float = 0.35,
    ) -> bool:
        """
        Policy check for fleet availability: suppresses futile courier prioritization
        when localized fleet availability drops below threshold (e.g. 35%).
        """
        return courier_availability_ratio >= threshold

    @classmethod
    def validate_order_state_drift(
        cls,
        action_type: str,
        current_status: str,
    ) -> Tuple[bool, str]:
        """
        Ensures the order has not drifted into an incompatible state between recommendation and execution.
        """
        if current_status in ("DELIVERED", "CANCELLED"):
            return False, f"Order has reached terminal state '{current_status}'. Recovery action aborted."

        if action_type == ActionType.REASSIGN_COURIER.value and current_status == "OUT_FOR_DELIVERY":
            return False, "Order is already OUT_FOR_DELIVERY; courier reassignment no longer eligible."

        if action_type == ActionType.EXPEDITE_KITCHEN_PING.value and current_status in (
            "FOOD_READY",
            "READY_FOR_PICKUP",
            "OUT_FOR_DELIVERY",
        ):
            return False, f"Food already prepared or dispatched (current status: '{current_status}'). Kitchen ping aborted."

        return True, "Order state is consistent and eligible for execution."

    @classmethod
    def validate_action_eligibility(
        cls,
        action_type: str,
        order_status: str,
        existing_actions: List[Dict[str, Any]],
        order_context: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Validates whether an action is operationally eligible on the order.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        order_context = order_context or {}

        # Rule 1: Terminal orders cannot receive interventions
        if order_status in ("DELIVERED", "CANCELLED"):
            return False, f"Order is already in terminal state: {order_status}"

        # Rule 2: Kitchen pings only valid before food is picked up or marked ready
        if action_type == ActionType.EXPEDITE_KITCHEN_PING.value:
            if order_status in ("FOOD_READY", "READY_FOR_PICKUP", "OUT_FOR_DELIVERY"):
                return False, f"Kitchen ping rejected: order status is already {order_status}"

        # Rule 3: Reassignment cannot occur if courier already picked up food
        if action_type == ActionType.REASSIGN_COURIER.value:
            if order_status == "OUT_FOR_DELIVERY":
                return False, "Courier reassignment rejected: courier has already picked up the order"

        # Rule 4: Communication Consent & Cooldown Check for Customer Notification
        if action_type == ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value:
            # Explicit communication consent check
            cust_consent = order_context.get("customer_consent")
            notif_enabled = order_context.get("customer", {}).get("notifications_enabled")
            if cust_consent is False or notif_enabled is False:
                return (
                    False,
                    "Suppressed: customer has explicitly opted out of automated notifications. AI recommendation cannot bypass consent.",
                )

            # 15-minute cooldown window
            for act in existing_actions:
                if act.get("action_type") == ActionType.PROACTIVE_CUSTOMER_NOTIFICATION.value:
                    act_time = act.get("created_at")
                    if isinstance(act_time, str):
                        try:
                            act_time = datetime.fromisoformat(act_time)
                        except Exception:
                            act_time = None
                    if act_time:
                        if act_time.tzinfo is None:
                            act_time = act_time.replace(tzinfo=timezone.utc)
                        if (now - act_time).total_seconds() < 15 * 60:
                            return (
                                False,
                                "Suppressed duplicate customer notification within 15-minute cooldown window",
                            )

        # Rule 5: Duplicate Apology Credit Voucher check (max 1 voucher per order)
        if action_type == ActionType.APOLOGY_CREDIT_VOUCHER.value:
            for act in existing_actions:
                if act.get("action_type") == ActionType.APOLOGY_CREDIT_VOUCHER.value:
                    return False, "Apology credit voucher already issued for this order (limit: 1 per order)"

        # Rule 6: Duplicate courier reassignment within 10 minutes
        if action_type == ActionType.REASSIGN_COURIER.value:
            for act in existing_actions:
                if act.get("action_type") == ActionType.REASSIGN_COURIER.value:
                    act_time = act.get("created_at")
                    if isinstance(act_time, str):
                        try:
                            act_time = datetime.fromisoformat(act_time)
                        except Exception:
                            act_time = None
                    if act_time:
                        if act_time.tzinfo is None:
                            act_time = act_time.replace(tzinfo=timezone.utc)
                        if (now - act_time).total_seconds() < 10 * 60:
                            return (
                                False,
                                "Suppressed duplicate courier reassignment within 10-minute cooldown window",
                            )

        return True, "Policy check passed: action is eligible"

    @classmethod
    def apply_policy(
        cls,
        recommendation: Dict[str, Any],
        order_status: str,
        existing_actions: List[Dict[str, Any]],
        order_context: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Enforces approval gating, eligibility rules, and expiration on a recommendation.
        Returns the policy-adjusted recommendation dictionary.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        action_type = recommendation.get("action_type")
        is_eligible, reason = cls.validate_action_eligibility(
            action_type=action_type,
            order_status=order_status,
            existing_actions=existing_actions,
            order_context=order_context,
            now=now,
        )

        rec = dict(recommendation)
        rec["is_eligible"] = is_eligible
        rec["policy_evaluation"] = reason

        # Set 30-minute validity window
        expires_at = now + timedelta(minutes=30)
        rec["expires_at"] = expires_at.isoformat()

        if not is_eligible:
            rec["approval_status"] = ApprovalStatus.REJECTED.value
            rec["rejection_reason"] = f"Ineligible by policy: {reason}"
            rec["requires_approval"] = False
            return rec

        # Enforce Human-In-The-Loop gate for sensitive actions
        if action_type in [a.value for a in cls.SENSITIVE_ACTIONS]:
            rec["requires_approval"] = True
            rec["approval_status"] = ApprovalStatus.PENDING_APPROVAL.value
            rec["approval_notes"] = "Sensitive operational action: requires explicit operator approval."
        else:
            rec["requires_approval"] = False
            rec["approval_status"] = ApprovalStatus.AUTO_APPROVED.value
            rec["approval_notes"] = "Auto-approved non-intrusive action under ResolveAI governance policy."

        return rec

    @classmethod
    def evaluate_recommendations(
        cls,
        recommendations: List[Dict[str, Any]],
        order_status: str,
        existing_actions: List[Dict[str, Any]],
        order_context: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluates a batch of recommendations, returning validated recommendations
        and summary metrics.
        """
        evaluated: List[Dict[str, Any]] = []
        pending_count = 0
        auto_approved_count = 0
        rejected_count = 0

        for r in recommendations:
            res = cls.apply_policy(r, order_status, existing_actions, order_context=order_context, now=now)
            evaluated.append(res)
            if res.get("approval_status") == ApprovalStatus.PENDING_APPROVAL.value:
                pending_count += 1
            elif res.get("approval_status") == ApprovalStatus.AUTO_APPROVED.value:
                auto_approved_count += 1
            elif res.get("approval_status") == ApprovalStatus.REJECTED.value:
                rejected_count += 1

        summary = {
            "total_evaluated": len(evaluated),
            "auto_approved": auto_approved_count,
            "pending_approval": pending_count,
            "rejected_by_policy": rejected_count,
            "evaluated_at": (now or datetime.now(timezone.utc)).isoformat(),
        }
        return evaluated, summary

    @classmethod
    def mask_pii(cls, value: Optional[str]) -> str:
        """
        Masks sensitive PII such as phone numbers, emails, or personal identifiers.
        E.g. '+919876543210' -> '+9198*****210'
        """
        if not value:
            return ""
        val = str(value).strip()
        if len(val) <= 6:
            return "*" * len(val)
        prefix_len = 5 if len(val) >= 10 else 2
        suffix_len = 3
        mask_len = max(len(val) - prefix_len - suffix_len, 3)
        return f"{val[:prefix_len]}{'*' * mask_len}{val[-suffix_len:]}"
