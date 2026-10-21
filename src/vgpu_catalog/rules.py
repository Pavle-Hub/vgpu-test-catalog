"""Loading and validation of the declarative catalog maintenance contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from vgpu_catalog.schema_validation import PROJECT_ROOT, iter_schema_errors

DEFAULT_RULES_PATH = PROJECT_ROOT / "rules.yaml"


class RulesError(ValueError):
    """Raised when the derivation contract cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class FieldOwnershipRules:
    human: tuple[str, ...]
    derived: tuple[str, ...]
    semantic: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MeasurementWindowRules:
    lookback_days: int
    minimum_samples_per_gpu: int


@dataclass(frozen=True, slots=True)
class DurationRules:
    percentile: int
    percentile_method: str
    gpu_aggregation: str
    timeout_margin: Decimal
    timeout_rounding: str


@dataclass(frozen=True, slots=True)
class PassRateRules:
    gpu_aggregation: str
    decimal_places: int
    healthy_minimum_percent: Decimal
    degraded_minimum_percent: Decimal


@dataclass(frozen=True, slots=True)
class FreshnessRules:
    maximum_age_days: int


@dataclass(frozen=True, slots=True)
class ComparisonRules:
    numeric_tolerance: Decimal


@dataclass(frozen=True, slots=True)
class CatalogRules:
    schema_version: str
    field_ownership: FieldOwnershipRules
    measurement_window: MeasurementWindowRules
    duration: DurationRules
    pass_rate: PassRateRules
    freshness: FreshnessRules
    comparison: ComparisonRules


def _as_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def load_rules(path: Path = DEFAULT_RULES_PATH) -> CatalogRules:
    """Load a YAML rule file, validate its schema, and return immutable rules."""

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RulesError(f"Cannot read rules file {path}: {error}") from error
    except yaml.YAMLError as error:
        raise RulesError(f"Invalid YAML in {path}: {error}") from error

    if not isinstance(document, dict):
        raise RulesError("Rules document must be a YAML mapping.")

    schema_errors = iter_schema_errors("rules", document)
    if schema_errors:
        raise RulesError("Rules violate their schema:\n" + "\n".join(schema_errors))

    pass_rate = document["pass_rate"]
    healthy = _as_decimal(pass_rate["healthy_minimum_percent"])
    degraded = _as_decimal(pass_rate["degraded_minimum_percent"])
    if degraded >= healthy:
        raise RulesError(
            "pass_rate.degraded_minimum_percent must be lower than healthy_minimum_percent."
        )

    ownership = document["field_ownership"]
    window = document["measurement_window"]
    duration = document["duration"]
    freshness = document["freshness"]
    comparison = document["comparison"]

    return CatalogRules(
        schema_version=document["schema_version"],
        field_ownership=FieldOwnershipRules(
            human=tuple(ownership["human"]),
            derived=tuple(ownership["derived"]),
            semantic=tuple(ownership["semantic"]),
        ),
        measurement_window=MeasurementWindowRules(
            lookback_days=window["lookback_days"],
            minimum_samples_per_gpu=window["minimum_samples_per_gpu"],
        ),
        duration=DurationRules(
            percentile=duration["percentile"],
            percentile_method=duration["percentile_method"],
            gpu_aggregation=duration["gpu_aggregation"],
            timeout_margin=_as_decimal(duration["timeout_margin"]),
            timeout_rounding=duration["timeout_rounding"],
        ),
        pass_rate=PassRateRules(
            gpu_aggregation=pass_rate["gpu_aggregation"],
            decimal_places=pass_rate["decimal_places"],
            healthy_minimum_percent=healthy,
            degraded_minimum_percent=degraded,
        ),
        freshness=FreshnessRules(maximum_age_days=freshness["maximum_age_days"]),
        comparison=ComparisonRules(numeric_tolerance=_as_decimal(comparison["numeric_tolerance"])),
    )
