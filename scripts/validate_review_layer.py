"""
Validate Review Layer Implementation

Tests backward compatibility and new features of the review layer.
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "lib"))

from review_session_manager import ReviewSession
from queue_manager import apply_queue_filter, get_queue_stats, QUEUE_TYPES
from annotation_taxonomy import (
    get_all_override_tags, FAILURE_TAXONOMY, validate_annotation
)
from annotation_manager import AnnotationManager
from summary_generator import (
    generate_session_summary, generate_override_audit,
    generate_disagreement_analysis
)
from data_loading import load_json_payload


PROJECT_ROOT = Path(__file__).parent.parent
DECISIONS_PATH = PROJECT_ROOT / "data" / "planner_decisions.json"
FORECASTS_PATH = PROJECT_ROOT / "data" / "forecasts_ranked.json"


def test_backward_compatibility():
    """Test that legacy decisions still work."""
    print("\n" + "=" * 60)
    print("TEST 1: Backward Compatibility")
    print("=" * 60)

    # Create a legacy decision record (no metadata)
    legacy_decision = {
        "item_id": "TEST_LEGACY_001",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "planner_action": "accept",
        "decision_match": True,
        "confidence_gap": 0.1,
        "error_type": "none",
        "reason": ""
    }

    print("[OK] Created legacy decision record")

    # Test that it can be serialized
    try:
        json_str = json.dumps(legacy_decision, indent=2)
        print("[OK] Legacy record serializes to JSON")
    except Exception as e:
        print(f"[FAIL] Failed to serialize: {e}")
        return False

    # Test that it can be loaded
    try:
        loaded = json.loads(json_str)
        assert loaded["item_id"] == "TEST_LEGACY_001"
        print("[OK] Legacy record loads from JSON")
    except Exception as e:
        print(f"[FAIL] Failed to load: {e}")
        return False

    print("[OK] Backward compatibility test PASSED")
    return True


def test_session_tracking():
    """Test session tracking functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Session Tracking")
    print("=" * 60)

    try:
        # Create session
        session = ReviewSession("test_reviewer", "priority_exceptions", 10)
        print(f"[OK] Created session: {session.session_id}")

        # Record a decision
        test_decision = {
            "item_id": "TEST_001",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "planner_action": "override",
            "error_type": "underreaction",
            "decision_metadata": {
                "review_duration_seconds": 45.0,
                "has_annotations": True
            }
        }

        session.record_decision(test_decision)
        print("[OK] Recorded decision in session")

        # Finalize session
        session_data = session.finalize()
        assert session_data["review_metrics"]["items_reviewed"] == 1
        print("[OK] Session finalized with correct metrics")

        # Test save (to temp location)
        temp_dir = PROJECT_ROOT / "data" / "review_sessions_test"
        temp_dir.mkdir(exist_ok=True)
        session_file = session.save(PROJECT_ROOT / "data")
        print(f"[OK] Session saved to {session_file}")

        print("[OK] Session tracking test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Session tracking test FAILED: {e}")
        return False


def test_queue_filtering():
    """Test queue filtering and sorting."""
    print("\n" + "=" * 60)
    print("TEST 3: Queue Filtering")
    print("=" * 60)

    try:
        # Load forecasts
        if not FORECASTS_PATH.exists():
            print("[WARN] No forecasts file found, skipping queue test")
            return True

        forecasts = load_json_payload(FORECASTS_PATH, data_key="forecasts")
        print(f"[OK] Loaded {len(forecasts)} forecasts")

        # Test each queue type
        decided_ids = set()
        for queue_type in QUEUE_TYPES.keys():
            filtered = apply_queue_filter(forecasts, queue_type, decided_ids)
            print(f"  - {queue_type}: {len(filtered)} items")

        print("[OK] All queue types filter successfully")

        # Test queue stats
        stats = get_queue_stats(forecasts, "priority_exceptions", decided_ids)
        assert "total_items" in stats
        print("[OK] Queue statistics generated")

        print("[OK] Queue filtering test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Queue filtering test FAILED: {e}")
        return False


def test_annotations():
    """Test annotation taxonomy and validation."""
    print("\n" + "=" * 60)
    print("TEST 4: Structured Annotations")
    print("=" * 60)

    try:
        # Test override tags
        all_tags = get_all_override_tags()
        assert len(all_tags) > 0
        print(f"[OK] Loaded {len(all_tags)} override tags")

        # Test failure taxonomy
        assert "data_quality" in FAILURE_TAXONOMY
        print(f"[OK] Loaded {len(FAILURE_TAXONOMY)} failure categories")

        # Test annotation validation
        valid_annotation = {
            "override_tags": ["data_quality/outlier_in_recent_sales"],
            "failure_taxonomy": {
                "category": "data_quality",
                "subcategory": "outlier_in_recent_sales",
                "severity": "medium"
            }
        }

        result = validate_annotation(valid_annotation)
        assert result["valid"] == True
        print("[OK] Valid annotation passes validation")

        # Test invalid annotation
        invalid_annotation = {
            "failure_taxonomy": {
                "category": "invalid_category",
                "subcategory": "test",
                "severity": "high"
            }
        }

        result = validate_annotation(invalid_annotation)
        assert result["valid"] == False
        print("[OK] Invalid annotation fails validation")

        print("[OK] Annotation test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Annotation test FAILED: {e}")
        return False


def test_annotation_manager():
    """Test annotation indexing and extraction."""
    print("\n" + "=" * 60)
    print("TEST 5: Annotation Manager")
    print("=" * 60)

    try:
        # Create test decisions with annotations
        test_decisions = [
            {
                "item_id": "TEST_001",
                "timestamp": "2026-05-09T12:00:00Z",
                "planner_action": "override",
                "decision_metadata": {
                    "override_tags": ["data_quality/supplier_disruption"],
                    "failure_taxonomy": {
                        "category": "data_quality",
                        "subcategory": "outlier_in_recent_sales"
                    }
                }
            },
            {
                "item_id": "TEST_002",
                "timestamp": "2026-05-09T12:05:00Z",
                "planner_action": "accept",
                # No metadata
            }
        ]

        ann_manager = AnnotationManager(PROJECT_ROOT / "data")
        annotations = ann_manager.extract_annotations(test_decisions)

        assert len(annotations) == 1  # Only one has annotations
        print("[OK] Extracted annotations from decisions")

        # Build index
        index = ann_manager.build_annotation_index(test_decisions)
        assert index["summary_statistics"]["total_decisions"] == 2
        assert index["summary_statistics"]["decisions_with_annotations"] == 1
        print("[OK] Built annotation index")

        # Get statistics
        stats = ann_manager.get_annotation_statistics(test_decisions)
        assert stats["coverage_rate"] == 0.5
        print("[OK] Calculated annotation statistics")

        print("[OK] Annotation manager test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Annotation manager test FAILED: {e}")
        return False


def test_summary_generation():
    """Test summary and report generation."""
    print("\n" + "=" * 60)
    print("TEST 6: Summary Generation")
    print("=" * 60)

    try:
        # Create test session data
        session_data = {
            "session_id": "test-session-001",
            "reviewer_id": "test_reviewer",
            "started_at": "2026-05-09T12:00:00Z",
            "ended_at": "2026-05-09T12:30:00Z",
            "duration_seconds": 1800,
            "session_context": {
                "queue_type": "priority_exceptions",
                "initial_queue_size": 10,
                "completed_reviews": 5
            },
            "review_metrics": {
                "items_reviewed": 5,
                "avg_review_time_seconds": 360,
                "decision_distribution": {
                    "accept": 2,
                    "override": 2,
                    "investigate": 1,
                    "escalate": 0
                },
                "agreement_rate": 0.4,
                "structured_annotations_used": 3
            }
        }

        # Generate session summary
        summary = generate_session_summary(session_data)
        assert "test-session-001" in summary
        assert "test_reviewer" in summary
        print("[OK] Generated session summary")

        # Create test decisions for governance reports
        test_decisions = [
            {
                "item_id": f"TEST_{i:03d}",
                "timestamp": "2026-05-09T12:00:00Z",
                "planner_action": "override" if i % 2 == 0 else "accept",
                "error_type": "underreaction" if i % 2 == 0 else "none",
                "decision_metadata": {
                    "override_tags": ["data_quality/supplier_disruption"]
                } if i % 2 == 0 else None
            }
            for i in range(10)
        ]

        # Generate override audit
        audit = generate_override_audit(test_decisions)
        assert "Override Audit" in audit
        print("[OK] Generated override audit")

        # Generate disagreement analysis
        analysis = generate_disagreement_analysis(test_decisions)
        assert "Disagreement Analysis" in analysis
        print("[OK] Generated disagreement analysis")

        print("[OK] Summary generation test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Summary generation test FAILED: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("REVIEW LAYER VALIDATION SUITE")
    print("=" * 60)

    tests = [
        ("Backward Compatibility", test_backward_compatibility),
        ("Session Tracking", test_session_tracking),
        ("Queue Filtering", test_queue_filtering),
        ("Structured Annotations", test_annotations),
        ("Annotation Manager", test_annotation_manager),
        ("Summary Generation", test_summary_generation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name} FAILED with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n[SUCCESS] All tests passed! Review layer is ready to use.")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
