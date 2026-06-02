"""Policy Configuration Manager - Centralized policy versioning and management."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class PolicyManager:
    """Manages policy configuration versioning and loading."""

    def __init__(self, policies_dir: Optional[Path] = None):
        if policies_dir is None:
            # Default to config/policies relative to project root
            self.policies_dir = Path(__file__).parent / "policies"
        else:
            self.policies_dir = Path(policies_dir)

        self.schema_path = self.policies_dir / "policy_schema.json"
        self.default_path = self.policies_dir / "default_policy.json"
        self.versions_dir = self.policies_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def load_policy(self, version: Optional[str] = None, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Load policy configuration.

        Args:
            version: Specific version to load (e.g., "v1.0.0"). If None, loads default/latest.
            environment: Environment override to apply (dev, test, prod). If None, no override.

        Returns:
            Policy configuration dictionary
        """
        # Load base policy
        if version:
            policy = self._load_version(version)
        else:
            # Check if environment variable specifies a version
            env_version = os.environ.get("POLICY_VERSION")
            if env_version:
                policy = self._load_version(env_version)
            else:
                policy = self._load_default()

        # Apply environment overrides if specified
        if environment:
            policy = self._apply_environment_override(policy, environment)

        return policy

    def _load_default(self) -> Dict[str, Any]:
        """Load default policy."""
        if not self.default_path.exists():
            raise FileNotFoundError(f"Default policy not found: {self.default_path}")

        return json.loads(self.default_path.read_text(encoding="utf-8"))

    def _load_version(self, version: str) -> Dict[str, Any]:
        """Load specific policy version."""
        # Look for version file
        version_file = self.versions_dir / f"{version}.json"

        if not version_file.exists():
            # Fallback: check if it's the default version
            default = self._load_default()
            if default.get("policy_version") == version:
                return default
            raise FileNotFoundError(f"Policy version not found: {version}")

        return json.loads(version_file.read_text(encoding="utf-8"))

    def save_policy_version(self, policy: Dict[str, Any], version: str, change_summary: str,
                           created_by: str = "system") -> Path:
        """
        Save a new policy version.

        Args:
            policy: Policy configuration to save
            version: Version string (e.g., "v1.1.0")
            change_summary: Human-readable description of changes
            created_by: Creator identifier

        Returns:
            Path to saved policy file
        """
        # Update metadata
        policy["policy_version"] = version
        policy["created_at"] = datetime.now(timezone.utc).isoformat()
        policy["created_by"] = created_by
        policy["change_summary"] = change_summary

        # Validate before saving
        self.validate_policy(policy)

        # Save to versions directory
        version_file = self.versions_dir / f"{version}.json"
        version_file.write_text(json.dumps(policy, indent=2), encoding="utf-8")

        print(f"Saved policy version {version} to {version_file}")
        return version_file

    def get_policy_diff(self, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two policy versions and return differences.

        Args:
            version1: First version (e.g., "v1.0.0")
            version2: Second version (e.g., "v1.1.0")

        Returns:
            Dictionary of differences organized by section
        """
        policy1 = self.load_policy(version=version1)
        policy2 = self.load_policy(version=version2)

        diff = {
            "version_from": version1,
            "version_to": version2,
            "changes": {}
        }

        # Compare threshold sections
        sections = ["exception_detection", "decision_generation", "scoring_weights", "tier_boundaries", "calibration"]

        for section in sections:
            if section not in policy1 and section not in policy2:
                continue

            section1 = policy1.get(section, {})
            section2 = policy2.get(section, {})

            section_diff = self._compare_dicts(section1, section2)
            if section_diff:
                diff["changes"][section] = section_diff

        return diff

    def _compare_dicts(self, dict1: Dict, dict2: Dict) -> Dict[str, Any]:
        """Compare two dictionaries and return differences."""
        changes = {}

        all_keys = set(dict1.keys()) | set(dict2.keys())

        for key in all_keys:
            val1 = dict1.get(key)
            val2 = dict2.get(key)

            if val1 != val2:
                change_info = {
                    "old": val1,
                    "new": val2
                }

                # Calculate percentage change for numeric values
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)) and val1 != 0:
                    pct_change = ((val2 - val1) / val1) * 100
                    change_info["percent_change"] = round(pct_change, 1)

                changes[key] = change_info

        return changes

    def validate_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Validate policy against schema.

        Args:
            policy: Policy configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If policy is invalid
        """
        # Basic validation - check required fields
        required_fields = [
            "schema_version",
            "policy_version",
            "created_at",
            "created_by",
            "change_summary",
            "exception_detection",
            "decision_generation",
            "scoring_weights",
            "tier_boundaries"
        ]

        for field in required_fields:
            if field not in policy:
                raise ValueError(f"Missing required field: {field}")

        # Validate version format
        version = policy["policy_version"]
        if not version.startswith("v") or version.count(".") != 2:
            raise ValueError(f"Invalid policy version format: {version}. Expected format: v1.0.0")

        return True

    def _apply_environment_override(self, policy: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """Apply environment-specific overrides to policy."""
        override_file = self.policies_dir.parent / "environments" / f"{environment}_overrides.json"

        if not override_file.exists():
            # No overrides for this environment
            return policy

        overrides = json.loads(override_file.read_text(encoding="utf-8"))

        # Deep merge overrides into policy
        policy = policy.copy()
        for section, values in overrides.items():
            if section in policy and isinstance(policy[section], dict):
                policy[section] = {**policy[section], **values}

        return policy


# Global instance
_policy_manager = PolicyManager()


def load_policy(version: Optional[str] = None, environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Load policy configuration (convenience function).

    Args:
        version: Specific version to load. If None, uses POLICY_VERSION env var or default.
        environment: Environment override to apply (dev, test, prod).

    Returns:
        Policy configuration dictionary
    """
    return _policy_manager.load_policy(version=version, environment=environment)


def get_policy_manager() -> PolicyManager:
    """Get the global policy manager instance."""
    return _policy_manager


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Policy Manager CLI")
    parser.add_argument("--diff", nargs=2, metavar=("V1", "V2"), help="Compare two policy versions")
    parser.add_argument("--show", metavar="VERSION", help="Show specific policy version")
    parser.add_argument("--validate", metavar="FILE", help="Validate a policy file")

    args = parser.parse_args()

    if args.diff:
        diff = _policy_manager.get_policy_diff(args.diff[0], args.diff[1])
        print(f"\nPolicy Diff: {diff['version_from']} → {diff['version_to']}")
        print("=" * 70)

        if not diff["changes"]:
            print("\nNo changes detected.")
        else:
            for section, changes in diff["changes"].items():
                print(f"\n{section}:")
                for param, change_info in changes.items():
                    old_val = change_info["old"]
                    new_val = change_info["new"]
                    print(f"  {param}: {old_val} → {new_val}", end="")
                    if "percent_change" in change_info:
                        pct = change_info["percent_change"]
                        sign = "+" if pct > 0 else ""
                        print(f" ({sign}{pct}%)")
                    else:
                        print()

    elif args.show:
        policy = _policy_manager.load_policy(version=args.show)
        print(json.dumps(policy, indent=2))

    elif args.validate:
        policy = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        try:
            _policy_manager.validate_policy(policy)
            print(f"✓ Policy is valid: {policy['policy_version']}")
        except ValueError as e:
            print(f"✗ Policy validation failed: {e}")

    else:
        # Show default policy
        policy = _policy_manager.load_policy()
        print(f"Default Policy: {policy['policy_version']}")
        print(json.dumps(policy, indent=2))
