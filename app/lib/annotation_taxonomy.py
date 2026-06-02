"""
Annotation Taxonomy

Defines structured taxonomies for override tags, failure classification,
and disagreement categorization.
"""

# Override tag taxonomy organized by category
OVERRIDE_TAGS = {
    "data_quality": [
        "outlier_in_recent_sales",
        "missing_promotional_data",
        "supplier_disruption",
        "inventory_constraint",
        "measurement_error",
        "data_lag"
    ],

    "seasonal_adjustment": [
        "holiday_shift",
        "weather_event",
        "local_event",
        "calendar_effect",
        "unusual_pattern"
    ],

    "business_knowledge": [
        "category_manager_input",
        "new_product_launch",
        "competitor_action",
        "price_change",
        "promotion_planned",
        "store_remodel"
    ],

    "model_limitation": [
        "low_history",
        "volatility_not_captured",
        "trend_reversal",
        "regime_change",
        "external_shock"
    ],

    "risk_adjustment": [
        "stockout_prevention",
        "excess_inventory_risk",
        "margin_protection",
        "supply_chain_constraint",
        "capacity_limitation"
    ]
}


# Failure taxonomy for root cause analysis
FAILURE_TAXONOMY = {
    "data_quality": [
        "outlier_in_recent_sales",
        "missing_feature",
        "data_lag",
        "measurement_error",
        "incomplete_history",
        "data_corruption"
    ],

    "model_error": [
        "underconfident_correct",
        "overconfident_wrong",
        "systematic_bias",
        "trend_not_detected",
        "seasonality_misestimated",
        "volatility_underestimated"
    ],

    "decision_logic": [
        "wrong_threshold",
        "missing_exception_rule",
        "incorrect_prioritization",
        "confidence_calibration_off",
        "risk_scoring_wrong"
    ],

    "context_missing": [
        "business_rule_not_encoded",
        "domain_knowledge_gap",
        "external_factor_unknown",
        "future_event_not_anticipated",
        "competitive_intelligence_gap"
    ]
}


# Disagreement reason categories by error type
DISAGREEMENT_REASON_CATEGORIES = {
    "underreaction": [
        "planner_saw_risk_model_missed",
        "planner_has_advance_information",
        "model_too_confident",
        "exception_rule_too_narrow",
        "threshold_too_strict"
    ],

    "overreaction": [
        "model_too_sensitive",
        "exception_rule_too_broad",
        "planner_risk_tolerant",
        "false_positive_pattern",
        "noise_misinterpreted_as_signal"
    ],

    "judgment_difference": [
        "risk_tolerance_difference",
        "action_preference_difference",
        "business_context_difference",
        "time_horizon_difference"
    ]
}


# Confidence levels for override decisions
CONFIDENCE_LEVELS = [
    "very_low",
    "low",
    "medium",
    "high",
    "very_high"
]


# Severity levels for failure taxonomy
SEVERITY_LEVELS = [
    "low",
    "medium",
    "high",
    "critical"
]


def get_all_override_tags() -> list:
    """
    Get flattened list of all override tags with category prefix.

    Returns:
        List of tags in format "category/tag"
    """
    all_tags = []
    for category, tags in OVERRIDE_TAGS.items():
        for tag in tags:
            all_tags.append(f"{category}/{tag}")
    return sorted(all_tags)


def parse_override_tag(tag: str) -> tuple:
    """
    Parse a category/tag string into components.

    Args:
        tag: Tag in format "category/tag"

    Returns:
        Tuple of (category, tag_name)
    """
    if "/" in tag:
        parts = tag.split("/", 1)
        return parts[0], parts[1]
    else:
        return "unknown", tag


def get_disagreement_reasons(error_type: str) -> list:
    """
    Get available disagreement reasons for a specific error type.

    Args:
        error_type: Error type (underreaction, overreaction, judgment_difference)

    Returns:
        List of reason categories for this error type
    """
    return DISAGREEMENT_REASON_CATEGORIES.get(error_type, [])


def validate_annotation(annotation: dict) -> dict:
    """
    Validate annotation structure and content.

    Args:
        annotation: Annotation dictionary to validate

    Returns:
        Dictionary with validation results and any errors
    """
    errors = []
    warnings = []

    # Validate override tags
    if "override_tags" in annotation:
        valid_tags = get_all_override_tags()
        for tag in annotation["override_tags"]:
            if tag not in valid_tags:
                warnings.append(f"Unknown override tag: {tag}")

    # Validate failure taxonomy
    if "failure_taxonomy" in annotation:
        taxonomy = annotation["failure_taxonomy"]
        category = taxonomy.get("category")

        if category and category not in FAILURE_TAXONOMY:
            errors.append(f"Unknown failure category: {category}")

        subcategory = taxonomy.get("subcategory")
        if category and subcategory:
            valid_subcategories = FAILURE_TAXONOMY.get(category, [])
            if subcategory not in valid_subcategories:
                errors.append(f"Invalid subcategory '{subcategory}' for category '{category}'")

        severity = taxonomy.get("severity")
        if severity and severity not in SEVERITY_LEVELS:
            errors.append(f"Invalid severity level: {severity}")

    # Validate disagreement classification
    if "disagreement_classification" in annotation:
        disagree = annotation["disagreement_classification"]
        reason_type = disagree.get("type")

        if reason_type and reason_type not in DISAGREEMENT_REASON_CATEGORIES:
            errors.append(f"Unknown disagreement type: {reason_type}")

        confidence = disagree.get("confidence_in_override")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            errors.append(f"Invalid confidence level: {confidence}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
