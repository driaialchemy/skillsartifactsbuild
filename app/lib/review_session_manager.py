"""
Review Session Manager

Handles session lifecycle tracking for human-in-the-loop reviews.
Captures session context, metrics, and generates session artifacts.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import json


class ReviewSession:
    """
    Manages a single review session lifecycle.

    A session represents a bounded period of review activity by a single
    reviewer, typically focusing on a specific queue type.
    """

    def __init__(self, reviewer_id: str, queue_type: str, initial_queue_size: int = 0):
        """
        Initialize a new review session.

        Args:
            reviewer_id: Unique identifier for the reviewer
            queue_type: Type of review queue being processed
            initial_queue_size: Number of items in queue at session start
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.session_id = f"session-{timestamp}-{reviewer_id}"
        self.reviewer_id = reviewer_id
        self.queue_type = queue_type
        self.started_at = datetime.now(timezone.utc)
        self.initial_queue_size = initial_queue_size
        self.decisions: List[Dict] = []

    def record_decision(self, decision_record: Dict) -> None:
        """
        Record a decision made during this session.

        Args:
            decision_record: Full decision record with metadata
        """
        self.decisions.append({
            "item_id": decision_record["item_id"],
            "timestamp": decision_record["timestamp"],
            "action": decision_record["planner_action"],
            "review_duration": decision_record.get("decision_metadata", {}).get("review_duration_seconds", 0),
            "error_type": decision_record.get("error_type", "unknown")
        })

    def finalize(self) -> Dict:
        """
        Finalize session and generate session summary data.

        Returns:
            Complete session record with metrics
        """
        ended_at = datetime.now(timezone.utc)
        duration = (ended_at - self.started_at).total_seconds()

        # Calculate decision distribution
        actions = [d["action"] for d in self.decisions]
        decision_dist = {}
        for action in ["accept", "override", "investigate", "escalate"]:
            decision_dist[action] = actions.count(action)

        # Calculate review metrics
        review_times = [d["review_duration"] for d in self.decisions if d["review_duration"] > 0]
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0

        # Calculate agreement rate (error_type == "none")
        agreements = [d for d in self.decisions if d["error_type"] == "none"]
        agreement_rate = len(agreements) / len(self.decisions) if self.decisions else 0

        # Count structured annotations used
        structured_annotations_count = sum(
            1 for d in self.decisions
            if d.get("has_annotations", False)
        )

        return {
            "session_id": self.session_id,
            "schema_version": "1.0",
            "reviewer_id": self.reviewer_id,
            "started_at": self.started_at.isoformat().replace('+00:00', 'Z'),
            "ended_at": ended_at.isoformat().replace('+00:00', 'Z'),
            "duration_seconds": round(duration, 1),

            "session_context": {
                "queue_type": self.queue_type,
                "initial_queue_size": self.initial_queue_size,
                "completed_reviews": len(self.decisions)
            },

            "review_metrics": {
                "items_reviewed": len(self.decisions),
                "avg_review_time_seconds": round(avg_review_time, 1),
                "decision_distribution": decision_dist,
                "agreement_rate": round(agreement_rate, 3),
                "structured_annotations_used": structured_annotations_count
            },

            "decision_ids": [d["item_id"] for d in self.decisions]
        }

    def save(self, base_path: Path) -> Path:
        """
        Save session data to disk.

        Args:
            base_path: Base data directory path

        Returns:
            Path to saved session file
        """
        session_dir = base_path / "review_sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        session_data = self.finalize()
        session_file = session_dir / f"{self.session_id}.json"

        session_file.write_text(
            json.dumps(session_data, indent=2),
            encoding="utf-8"
        )

        # Update session index
        self._update_session_index(session_dir, session_data)

        return session_file

    def _update_session_index(self, session_dir: Path, session_data: Dict) -> None:
        """
        Update the session index with this session's summary.

        Args:
            session_dir: Directory containing session files
            session_data: Finalized session data
        """
        index_file = session_dir / "session_index.json"

        # Load existing index
        if index_file.exists():
            index = json.loads(index_file.read_text(encoding="utf-8"))
        else:
            index = {
                "schema_version": "1.0",
                "sessions": []
            }

        # Add this session to index
        index["sessions"].append({
            "session_id": session_data["session_id"],
            "reviewer_id": session_data["reviewer_id"],
            "queue_type": session_data["session_context"]["queue_type"],
            "started_at": session_data["started_at"],
            "items_reviewed": session_data["review_metrics"]["items_reviewed"],
            "duration_seconds": session_data["duration_seconds"]
        })

        # Sort by started_at descending (most recent first)
        index["sessions"].sort(key=lambda s: s["started_at"], reverse=True)

        # Save updated index
        index_file.write_text(
            json.dumps(index, indent=2),
            encoding="utf-8"
        )
