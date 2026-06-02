"""
Review Summary Generator

Generates human-readable markdown summaries of review sessions,
daily activity, reviewer performance, and governance reports.
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import Counter, defaultdict
import json


def generate_session_summary(session_data: Dict) -> str:
    """
    Generate markdown summary for a single review session.

    Args:
        session_data: Finalized session data from ReviewSession

    Returns:
        Markdown-formatted summary string
    """
    metrics = session_data["review_metrics"]
    context = session_data["session_context"]

    # Calculate duration in minutes
    duration_mins = session_data["duration_seconds"] / 60

    # Decision distribution with percentages
    total_decisions = metrics["items_reviewed"]
    dist = metrics["decision_distribution"]

    md = f"""# Review Session Summary: {session_data['session_id']}

## Session Overview
- **Reviewer**: {session_data['reviewer_id']}
- **Queue Type**: {context['queue_type']}
- **Duration**: {duration_mins:.1f} minutes
- **Items Reviewed**: {total_decisions}
- **Date**: {session_data['started_at'][:10]}

## Decision Distribution
"""

    for action in ["accept", "override", "investigate", "escalate"]:
        count = dist.get(action, 0)
        pct = (count / total_decisions * 100) if total_decisions > 0 else 0
        md += f"- **{action.title()}**: {count} ({pct:.1f}%)\n"

    md += f"""
## Performance Metrics
- **Agreement Rate**: {metrics['agreement_rate'] * 100:.1f}%
- **Average Review Time**: {metrics['avg_review_time_seconds']:.1f} seconds
- **Structured Annotations Used**: {metrics['structured_annotations_used']} of {total_decisions}

## Queue Context
- **Initial Queue Size**: {context.get('initial_queue_size', 'N/A')}
- **Completed Reviews**: {context['completed_reviews']}
"""

    return md


def generate_daily_summary(sessions: List[Dict], date: str) -> str:
    """
    Generate markdown summary for all sessions on a specific date.

    Args:
        sessions: List of session data dictionaries for this date
        date: Date string in YYYY-MM-DD format

    Returns:
        Markdown-formatted daily summary
    """
    total_reviews = sum(s["review_metrics"]["items_reviewed"] for s in sessions)
    total_duration = sum(s["duration_seconds"] for s in sessions)

    # Aggregate decision distribution
    total_dist = Counter()
    for session in sessions:
        dist = session["review_metrics"]["decision_distribution"]
        total_dist.update(dist)

    # Aggregate by reviewer
    by_reviewer = defaultdict(lambda: {"sessions": 0, "reviews": 0})
    for session in sessions:
        reviewer = session["reviewer_id"]
        by_reviewer[reviewer]["sessions"] += 1
        by_reviewer[reviewer]["reviews"] += session["review_metrics"]["items_reviewed"]

    # Aggregate by queue type
    by_queue = Counter()
    for session in sessions:
        by_queue[session["session_context"]["queue_type"]] += 1

    md = f"""# Daily Review Summary: {date}

## Overview
- **Total Sessions**: {len(sessions)}
- **Total Reviews**: {total_reviews}
- **Total Time**: {total_duration / 60:.1f} minutes
- **Average Reviews per Session**: {total_reviews / len(sessions):.1f}

## Decision Distribution
"""

    for action in ["accept", "override", "investigate", "escalate"]:
        count = total_dist.get(action, 0)
        pct = (count / total_reviews * 100) if total_reviews > 0 else 0
        md += f"- **{action.title()}**: {count} ({pct:.1f}%)\n"

    md += "\n## Activity by Reviewer\n"
    for reviewer, stats in sorted(by_reviewer.items()):
        md += f"- **{reviewer}**: {stats['sessions']} sessions, {stats['reviews']} reviews\n"

    md += "\n## Activity by Queue Type\n"
    for queue_type, count in by_queue.most_common():
        md += f"- **{queue_type}**: {count} sessions\n"

    md += "\n## Session Details\n"
    for session in sorted(sessions, key=lambda s: s["started_at"]):
        start_time = session["started_at"][11:19]  # Extract HH:MM:SS
        reviewer = session["reviewer_id"]
        queue = session["session_context"]["queue_type"]
        items = session["review_metrics"]["items_reviewed"]
        md += f"- `{start_time}` - {reviewer} - {queue} - {items} items\n"

    return md


def generate_reviewer_activity(sessions: List[Dict], reviewer_id: str) -> str:
    """
    Generate markdown summary of all activity for a specific reviewer.

    Args:
        sessions: List of all session data for this reviewer
        reviewer_id: Reviewer identifier

    Returns:
        Markdown-formatted reviewer activity summary
    """
    total_sessions = len(sessions)
    total_reviews = sum(s["review_metrics"]["items_reviewed"] for s in sessions)
    total_time = sum(s["duration_seconds"] for s in sessions)

    # Aggregate decision distribution
    total_dist = Counter()
    for session in sessions:
        dist = session["review_metrics"]["decision_distribution"]
        total_dist.update(dist)

    # Calculate averages
    avg_reviews_per_session = total_reviews / total_sessions if total_sessions > 0 else 0
    avg_review_time = sum(
        s["review_metrics"]["avg_review_time_seconds"] * s["review_metrics"]["items_reviewed"]
        for s in sessions
    ) / total_reviews if total_reviews > 0 else 0

    # Aggregate annotations usage
    total_annotations = sum(s["review_metrics"]["structured_annotations_used"] for s in sessions)
    annotation_rate = (total_annotations / total_reviews * 100) if total_reviews > 0 else 0

    md = f"""# Reviewer Activity Report: {reviewer_id}

## All-Time Statistics
- **Total Sessions**: {total_sessions}
- **Total Reviews**: {total_reviews}
- **Avg Reviews per Session**: {avg_reviews_per_session:.1f}
- **Total Review Time**: {total_time / 3600:.1f} hours
- **Avg Review Time per Item**: {avg_review_time:.1f} seconds

## Decision Pattern
"""

    for action in ["accept", "override", "investigate", "escalate"]:
        count = total_dist.get(action, 0)
        pct = (count / total_reviews * 100) if total_reviews > 0 else 0
        md += f"- **{action.title()}**: {count} ({pct:.1f}%)\n"

    md += f"""
## Annotation Usage
- **Structured Annotations Used**: {total_annotations} of {total_reviews}
- **Annotation Rate**: {annotation_rate:.1f}%

## Session History
"""

    for session in sorted(sessions, key=lambda s: s["started_at"], reverse=True)[:20]:
        date = session["started_at"][:10]
        queue = session["session_context"]["queue_type"]
        items = session["review_metrics"]["items_reviewed"]
        duration = session["duration_seconds"] / 60
        md += f"- `{date}` - {queue} - {items} items in {duration:.1f} min\n"

    if len(sessions) > 20:
        md += f"\n*Showing most recent 20 of {len(sessions)} sessions*\n"

    return md


def generate_override_audit(decisions: List[Dict]) -> str:
    """
    Generate governance report auditing all overrides.

    Args:
        decisions: List of all decision records

    Returns:
        Markdown-formatted override audit report
    """
    overrides = [d for d in decisions if d["planner_action"] == "override"]
    total_decisions = len(decisions)
    total_overrides = len(overrides)

    override_rate = (total_overrides / total_decisions * 100) if total_decisions > 0 else 0

    # Extract override tags
    all_tags = []
    for decision in overrides:
        if "decision_metadata" in decision:
            tags = decision["decision_metadata"].get("override_tags", [])
            all_tags.extend(tags)

    tag_counts = Counter(all_tags)

    # Extract failure categories
    failure_categories = []
    for decision in overrides:
        if "decision_metadata" in decision:
            taxonomy = decision["decision_metadata"].get("failure_taxonomy")
            if taxonomy and taxonomy.get("category"):
                failure_categories.append(taxonomy["category"])

    category_counts = Counter(failure_categories)

    # High-confidence overrides
    high_conf_overrides = []
    for decision in overrides:
        if "decision_metadata" in decision:
            conf = decision["decision_metadata"].get("confidence_in_decision", 0)
            if conf >= 0.8:
                high_conf_overrides.append(decision)

    md = f"""# Override Audit Report

## Summary
- **Total Decisions**: {total_decisions}
- **Total Overrides**: {total_overrides}
- **Override Rate**: {override_rate:.1f}%

## Most Common Override Reasons
"""

    for tag, count in tag_counts.most_common(10):
        pct = (count / total_overrides * 100) if total_overrides > 0 else 0
        md += f"- **{tag}**: {count} ({pct:.1f}%)\n"

    md += f"""
## Overrides by Failure Category
"""

    for category, count in category_counts.most_common():
        pct = (count / total_overrides * 100) if total_overrides > 0 else 0
        md += f"- **{category}**: {count} ({pct:.1f}%)\n"

    high_conf_rate = (len(high_conf_overrides) / total_overrides * 100) if total_overrides > 0 else 0

    md += f"""
## High-Confidence Overrides
- **Count**: {len(high_conf_overrides)} ({high_conf_rate:.1f}% of all overrides)
- **Definition**: Overrides where reviewer confidence ≥ 0.8
"""

    return md


def generate_disagreement_analysis(decisions: List[Dict]) -> str:
    """
    Generate governance report analyzing disagreements between system and planner.

    Args:
        decisions: List of all decision records

    Returns:
        Markdown-formatted disagreement analysis
    """
    total_decisions = len(decisions)

    # Count by error type
    error_type_counts = Counter([d["error_type"] for d in decisions])

    # Extract disagreement reasons
    disagreement_reasons = []
    for decision in decisions:
        if decision["error_type"] != "none" and "decision_metadata" in decision:
            disagree = decision["decision_metadata"].get("disagreement_classification")
            if disagree and disagree.get("reason_category"):
                disagreement_reasons.append(disagree["reason_category"])

    reason_counts = Counter(disagreement_reasons)

    md = f"""# Disagreement Analysis Report

## Error Type Distribution
- **Total Decisions**: {total_decisions}

"""

    for error_type in ["none", "underreaction", "overreaction", "judgment_difference"]:
        count = error_type_counts.get(error_type, 0)
        pct = (count / total_decisions * 100) if total_decisions > 0 else 0
        label = "Agreement" if error_type == "none" else error_type.replace("_", " ").title()
        md += f"- **{label}**: {count} ({pct:.1f}%)\n"

    disagreements = total_decisions - error_type_counts.get("none", 0)
    disagreement_rate = (disagreements / total_decisions * 100) if total_decisions > 0 else 0

    md += f"""
## Overall Metrics
- **Total Disagreements**: {disagreements}
- **Disagreement Rate**: {disagreement_rate:.1f}%
- **Agreement Rate**: {100 - disagreement_rate:.1f}%

## Top Disagreement Reasons
"""

    for reason, count in reason_counts.most_common(10):
        pct = (count / disagreements * 100) if disagreements > 0 else 0
        md += f"- **{reason}**: {count} ({pct:.1f}%)\n"

    return md


def save_summary(summary_content: str, summary_path: Path) -> Path:
    """
    Save a summary to a markdown file.

    Args:
        summary_content: Markdown content
        summary_path: Path to save file

    Returns:
        Path to saved file
    """
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary_content, encoding="utf-8")
    return summary_path
