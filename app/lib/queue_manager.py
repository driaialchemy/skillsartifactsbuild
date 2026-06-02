"""
Review Queue Manager

Defines and manages multiple review queue types with automatic filtering and sorting.
"""

from typing import List, Dict, Callable, Set


# Queue type definitions
QUEUE_TYPES = {
    "priority_exceptions": {
        "name": "Priority Exceptions",
        "icon": "🚨",
        "description": "Critical and high-priority exceptions requiring immediate attention",
        "filter_fn": lambda item: item.get("priority_tier") in ["critical", "high"],
        "sort_key": lambda item: -item.get("priority_score", 0)
    },

    "low_confidence": {
        "name": "Low Confidence Queue",
        "icon": "⚠️",
        "description": "Exceptions where the system has low confidence in its recommendation",
        "filter_fn": lambda item: (
            item.get("decision_confidence", 1.0) < 0.4 and
            item.get("is_exception", False)
        ),
        "sort_key": lambda item: item.get("decision_confidence", 1.0)
    },

    "high_risk_accepts": {
        "name": "High-Risk Auto-Accepts",
        "icon": "🔍",
        "description": "Items recommended for acceptance but with high risk or low confidence",
        "filter_fn": lambda item: (
            item.get("recommendation") == "accept" and
            (item.get("risk_level") == "high" or item.get("confidence_score", 1.0) < 0.5)
        ),
        "sort_key": lambda item: -item.get("confidence_gap", 0)
    },

    "random_sample_qa": {
        "name": "Random Sample QA",
        "icon": "🎲",
        "description": "Randomly sampled items for quality assurance",
        "filter_fn": lambda item: item.get("_sampled_for_qa", False),
        "sort_key": lambda item: item.get("_sample_sequence", 0)
    },

    "escalated_returns": {
        "name": "Escalated Returns",
        "icon": "↩️",
        "description": "Previously escalated items returning for re-review",
        "filter_fn": lambda item: item.get("_escalation_return", False),
        "sort_key": lambda item: -item.get("_escalation_priority", 0)
    },

    "all_exceptions": {
        "name": "All Exceptions",
        "icon": "📋",
        "description": "All items flagged as exceptions (default view)",
        "filter_fn": lambda item: item.get("is_exception", False),
        "sort_key": lambda item: -item.get("priority_score", 0)
    }
}


def apply_queue_filter(
    forecasts: List[Dict],
    queue_type: str,
    decided_ids: Set[str]
) -> List[Dict]:
    """
    Filter and sort forecasts based on queue type.

    Args:
        forecasts: All forecast items
        queue_type: Queue type identifier
        decided_ids: Set of item IDs that already have decisions

    Returns:
        Filtered and sorted list of items for this queue
    """
    if queue_type not in QUEUE_TYPES:
        raise ValueError(f"Unknown queue type: {queue_type}")

    config = QUEUE_TYPES[queue_type]

    # Get all exceptions
    exceptions = [f for f in forecasts if f.get("is_exception", False)]

    # Filter to undecided items
    undecided = [f for f in exceptions if f["item_id"] not in decided_ids]

    # Apply queue-specific filter
    filtered = [f for f in undecided if config["filter_fn"](f)]

    # Sort according to queue type
    sorted_items = sorted(filtered, key=config["sort_key"])

    return sorted_items


def get_queue_stats(
    forecasts: List[Dict],
    queue_type: str,
    decided_ids: Set[str]
) -> Dict:
    """
    Get statistics for a specific queue.

    Args:
        forecasts: All forecast items
        queue_type: Queue type identifier
        decided_ids: Set of item IDs that already have decisions

    Returns:
        Dictionary with queue statistics
    """
    filtered_queue = apply_queue_filter(forecasts, queue_type, decided_ids)

    return {
        "queue_type": queue_type,
        "name": QUEUE_TYPES[queue_type]["name"],
        "icon": QUEUE_TYPES[queue_type]["icon"],
        "total_items": len(filtered_queue),
        "description": QUEUE_TYPES[queue_type]["description"]
    }


def get_all_queue_stats(
    forecasts: List[Dict],
    decided_ids: Set[str]
) -> List[Dict]:
    """
    Get statistics for all queue types.

    Args:
        forecasts: All forecast items
        decided_ids: Set of item IDs that already have decisions

    Returns:
        List of queue statistics dictionaries
    """
    stats = []
    for queue_type in QUEUE_TYPES.keys():
        stats.append(get_queue_stats(forecasts, queue_type, decided_ids))

    return stats
