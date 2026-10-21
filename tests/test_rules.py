from pathlib import Path

import pytest

from vgpu_catalog.rules import RulesError, load_rules


def test_reference_rules_load_as_immutable_contract() -> None:
    rules = load_rules()

    assert rules.schema_version == "1.0"
    assert rules.measurement_window.minimum_samples_per_gpu == 10
    assert rules.duration.percentile == 95
    assert str(rules.duration.timeout_margin) == "1.25"
    assert rules.field_ownership.human == ("purpose", "notes")
    assert "timeout_seconds" in rules.field_ownership.derived


def test_rules_schema_rejects_unknown_property(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        Path("rules.yaml").read_text(encoding="utf-8") + "unknown_rule: true\n",
        encoding="utf-8",
    )

    with pytest.raises(RulesError, match="Additional properties"):
        load_rules(rules_path)


def test_rules_reject_overlapping_badge_thresholds(tmp_path: Path) -> None:
    rules_text = Path("rules.yaml").read_text(encoding="utf-8")
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        rules_text.replace("degraded_minimum_percent: 80", "degraded_minimum_percent: 95"),
        encoding="utf-8",
    )

    with pytest.raises(RulesError, match="must be lower"):
        load_rules(rules_path)
