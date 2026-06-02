"""
Annotation Manager

Manages extraction, indexing, and analysis of structured annotations
from review decisions.
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime, timezone
from collections import Counter
import json


class AnnotationManager:
    """
    Manages annotation indexing and statistics.
    """

    def __init__(self, base_path: Path):
        """
        Initialize annotation manager.

        Args:
            base_path: Base data directory path
        """
        self.base_path = base_path
        self.annotation_dir = base_path / "review_annotations"
        self.annotation_dir.mkdir(parents=True, exist_ok=True)

    def extract_annotations(self, decisions: List[Dict]) -> List[Dict]:
        """
        Extract all annotations from decision records.

        Args:
            decisions: List of decision records

        Returns:
            List of extracted annotations with metadata
        """
        annotations = []

        for decision in decisions:
            if "decision_metadata" not in decision:
                continue

            metadata = decision["decision_metadata"]

            # Check if any annotations exist
            has_annotations = any([
                metadata.get("override_tags"),
                metadata.get("failure_taxonomy"),
                metadata.get("disagreement_classification"),
                metadata.get("structured_reason")
            ])

            if has_annotations:
                annotations.append({
                    "item_id": decision["item_id"],
                    "timestamp": decision["timestamp"],
                    "reviewer_id": metadata.get("reviewer_id", "unknown"),
                    "planner_action": decision["planner_action"],
                    "override_tags": metadata.get("override_tags", []),
                    "failure_taxonomy": metadata.get("failure_taxonomy"),
                    "disagreement_classification": metadata.get("disagreement_classification"),
                    "structured_reason": metadata.get("structured_reason"),
                    "confidence_in_decision": metadata.get("confidence_in_decision")
                })

        return annotations

    def build_annotation_index(self, decisions: List[Dict]) -> Dict:
        """
        Build annotation index with summary statistics.

        Args:
            decisions: List of all decision records

        Returns:
            Annotation index dictionary
        """
        annotations = self.extract_annotations(decisions)

        # Count override tag usage
        all_override_tags = []
        for ann in annotations:
            all_override_tags.extend(ann.get("override_tags", []))

        override_tag_counts = Counter(all_override_tags)

        # Count failure taxonomy categories
        failure_categories = []
        failure_subcategories = []
        for ann in annotations:
            taxonomy = ann.get("failure_taxonomy")
            if taxonomy:
                if taxonomy.get("category"):
                    failure_categories.append(taxonomy["category"])
                if taxonomy.get("subcategory"):
                    failure_subcategories.append(taxonomy["subcategory"])

        failure_category_counts = Counter(failure_categories)
        failure_subcategory_counts = Counter(failure_subcategories)

        # Count disagreement types
        disagreement_types = []
        for ann in annotations:
            disagree = ann.get("disagreement_classification")
            if disagree and disagree.get("type"):
                disagreement_types.append(disagree["type"])

        disagreement_type_counts = Counter(disagreement_types)

        # Calculate coverage metrics
        total_decisions = len(decisions)
        decisions_with_annotations = len(annotations)
        coverage_rate = decisions_with_annotations / total_decisions if total_decisions > 0 else 0

        # Build index
        index = {
            "schema_version": "1.0",
            "last_updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),

            "summary_statistics": {
                "total_decisions": total_decisions,
                "decisions_with_annotations": decisions_with_annotations,
                "annotation_coverage_rate": round(coverage_rate, 3),

                "override_tag_usage": dict(override_tag_counts.most_common(20)),

                "failure_taxonomy_distribution": {
                    "by_category": dict(failure_category_counts),
                    "by_subcategory": dict(failure_subcategory_counts.most_common(20))
                },

                "disagreement_type_distribution": dict(disagreement_type_counts)
            },

            "annotations": annotations
        }

        return index

    def save_annotation_index(self, decisions: List[Dict]) -> Path:
        """
        Build and save annotation index.

        Args:
            decisions: List of all decision records

        Returns:
            Path to saved annotation index
        """
        index = self.build_annotation_index(decisions)

        index_file = self.annotation_dir / "annotation_index.json"
        index_file.write_text(
            json.dumps(index, indent=2),
            encoding="utf-8"
        )

        return index_file

    def export_annotations(self, decisions: List[Dict]) -> Path:
        """
        Export annotations in a flat format for analysis.

        Args:
            decisions: List of all decision records

        Returns:
            Path to exported annotations file
        """
        annotations = self.extract_annotations(decisions)

        export_file = self.annotation_dir / "annotations_export.json"
        export_file.write_text(
            json.dumps(annotations, indent=2),
            encoding="utf-8"
        )

        return export_file

    def get_annotation_statistics(self, decisions: List[Dict]) -> Dict:
        """
        Get quick annotation statistics without full index.

        Args:
            decisions: List of decision records

        Returns:
            Dictionary of annotation statistics
        """
        annotations = self.extract_annotations(decisions)

        total_decisions = len(decisions)
        decisions_with_annotations = len(annotations)

        return {
            "total_decisions": total_decisions,
            "decisions_with_annotations": decisions_with_annotations,
            "coverage_rate": round(
                decisions_with_annotations / total_decisions if total_decisions > 0 else 0,
                3
            ),
            "avg_tags_per_annotation": round(
                sum(len(a.get("override_tags", [])) for a in annotations) / len(annotations)
                if annotations else 0,
                2
            )
        }
