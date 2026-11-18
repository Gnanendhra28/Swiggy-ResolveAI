from enum import Enum
from typing import Dict, Any


class ScenarioType(str, Enum):
    NORMAL_ORDER = "NORMAL_ORDER"
    RESTAURANT_DELAY = "RESTAURANT_DELAY"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    ASSIGNMENT_DELAY = "ASSIGNMENT_DELAY"
    FAILED_RECOVERY = "FAILED_RECOVERY"
    SUCCESSFUL_RECOVERY = "SUCCESSFUL_RECOVERY"


SCENARIO_METADATA: Dict[ScenarioType, Dict[str, Any]] = {
    ScenarioType.NORMAL_ORDER: {
        "title": "Normal Delivery Flow",
        "description": "Standard seamless lifecycle: acceptance, timely preparation, rider assignment, pickup, and doorstep handover within promised SLA.",
        "expected_status": "DELIVERED",
        "has_delays": False,
    },
    ScenarioType.RESTAURANT_DELAY: {
        "title": "Kitchen Overload & Preparation Delay",
        "description": "Kitchen backlog causes preparation delay exceeding baseline prep SLA. System detects delay and alerts customer.",
        "expected_status": "DELIVERED",
        "has_delays": True,
    },
    ScenarioType.DELIVERY_DELAY: {
        "title": "Transit & Traffic Route Delay",
        "description": "Severe route congestion or waterlogging delays rider transit. Dynamic ETA breaches promised delivery time.",
        "expected_status": "DELIVERED",
        "has_delays": True,
    },
    ScenarioType.ASSIGNMENT_DELAY: {
        "title": "Rider Fleet Shortage & Reassignment",
        "description": "Rider search initially times out due to high sector demand. Expanded search reassigns order to alternate partner.",
        "expected_status": "DELIVERED",
        "has_delays": True,
    },
    ScenarioType.FAILED_RECOVERY: {
        "title": "Unresolvable Disruption & Escalation",
        "description": "Critical failure occurs (kitchen equipment breakdown/stockout). Automated recovery fails and order is escalated to human support.",
        "expected_status": "ESCALATED",
        "has_delays": True,
    },
    ScenarioType.SUCCESSFUL_RECOVERY: {
        "title": "Autonomous Issue Detection & Recovery",
        "description": "Operational bottleneck detected early. Autonomous recovery engine re-routes fleet and applies proactive customer appeasement.",
        "expected_status": "RECOVERED",
        "has_delays": False,
    },
}
