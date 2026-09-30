"""Framework-independent distance-trend and IDW residual freight estimator."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Mapping, Sequence, TypeAlias

from freight_estimator.coverage import Coverage, rate_coverage

EARTH_RADIUS_MILES = 3958.7613
DEFAULT_MAX_OBSERVATION_DISTANCE_MILES = 600.0
DEFAULT_ROAD_DISTANCE_FACTOR = 1.18


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Observation:
    destination: Location
    cost: float


@dataclass(frozen=True)
class NeighborContribution:
    destination: Location
    observed_cost: float
    distance_miles: float
    idw_weight: float
    normalized_weight: float
    contribution: float
    residual: float = 0.0
    residual_contribution: float = 0.0
    baseline_distance_miles: float | None = None
    baseline_distance_source: str = "factor_fallback"


@dataclass(frozen=True)
class Estimate:
    estimated_cost: float
    is_observed: bool
    k: int
    power: float
    max_observation_distance_miles: float
    eligible_observation_count: int
    coverage: Coverage | None
    neighbors: tuple[NeighborContribution, ...]
    distance_baseline: float | None = None
    baseline_fixed_cost: float | None = None
    baseline_per_mile_rate: float | None = None
    baseline_distance_miles: float | None = None
    baseline_distance_source: str | None = None


@dataclass(frozen=True)
class InsufficientData:
    """A valid model result when no historical observation is within the radius."""

    max_observation_distance_miles: float
    coverage: Coverage
    nearest_available_observation_distance_miles: float | None


EstimateResult: TypeAlias = Estimate | InsufficientData


def great_circle_miles(a: Location, b: Location) -> float:
    """Return great-circle distance between two coordinates in miles."""
    lat1, lat2 = radians(a.latitude), radians(b.latitude)
    dlat = lat2 - lat1
    dlon = radians(b.longitude - a.longitude)
    haversine = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * asin(sqrt(min(1.0, haversine)))


def resolve_baseline_distance(
    origin: Location,
    destination: Location,
    driving_miles: Mapping[str, float],
) -> tuple[float, str]:
    """Use a saved OSRM route distance, or the calibrated factor fallback."""
    route_distance = driving_miles.get(destination.id)
    if route_distance is not None:
        return route_distance, "osrm"
    return DEFAULT_ROAD_DISTANCE_FACTOR * great_circle_miles(origin, destination), "factor_fallback"


def fit_distance_baseline(
    origin: Location,
    observations: Sequence[Observation],
    driving_miles: Mapping[str, float] | None = None,
) -> tuple[float, float]:
    """Fit a linear baseline cost = fixed charge + per-mile rate * distance."""
    if not observations:
        return 0.0, 0.0

    routes = driving_miles or {}
    distances = [resolve_baseline_distance(origin, row.destination, routes)[0] for row in observations]
    mean_distance = sum(distances) / len(distances)
    mean_cost = sum(row.cost for row in observations) / len(observations)
    variance = sum((distance - mean_distance) ** 2 for distance in distances)
    if variance == 0:
        return mean_cost, 0.0

    covariance = sum(
        (distance - mean_distance) * (row.cost - mean_cost)
        for distance, row in zip(distances, observations)
    )
    rate = covariance / variance
    fixed_cost = mean_cost - rate * mean_distance
    return fixed_cost, rate


def estimate_cost(
    target: Location,
    observations: Sequence[Observation],
    *,
    origin: Location,
    k: int = 5,
    power: float = 2.0,
    max_observation_distance_miles: float = DEFAULT_MAX_OBSERVATION_DISTANCE_MILES,
    driving_miles: Mapping[str, float] | None = None,
) -> EstimateResult:
    """Estimate cost from an origin-distance trend plus local IDW residuals.

    A direct observation at the target coordinate is returned as an observed rate.
    If no historical observations qualify, return InsufficientData; the radius is
    never expanded to fill K. The distance baseline is fitted to all observations
    for this origin; only residual adjustments use the target's eligible neighbors.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if not isfinite(power) or power <= 0:
        raise ValueError("power must be a finite number greater than 0")
    if not isfinite(max_observation_distance_miles) or max_observation_distance_miles <= 0:
        raise ValueError("max observation distance must be a finite number greater than 0")

    measured = sorted(
        ((great_circle_miles(target, row.destination), row) for row in observations),
        key=lambda item: (item[0], item[1].destination.id),
    )

    routes = driving_miles or {}
    fixed_cost, per_mile_rate = fit_distance_baseline(origin, observations, routes)
    eligible = [item for item in measured if item[0] <= max_observation_distance_miles]
    if not eligible:
        return InsufficientData(
            max_observation_distance_miles=max_observation_distance_miles,
            coverage=rate_coverage(0, ()),
            nearest_available_observation_distance_miles=measured[0][0] if measured else None,
        )

    exact = next(((distance, row) for distance, row in eligible if distance < 1e-9), None)
    target_baseline_miles, target_distance_source = resolve_baseline_distance(origin, target, routes)
    baseline_at_target = fixed_cost + per_mile_rate * target_baseline_miles
    if exact:
        distance, row = exact
        return Estimate(
            estimated_cost=row.cost,
            is_observed=True,
            k=k,
            power=power,
            max_observation_distance_miles=max_observation_distance_miles,
            eligible_observation_count=len(eligible),
            coverage=None,
            neighbors=(NeighborContribution(
                row.destination,
                row.cost,
                distance,
                0.0,
                1.0,
                row.cost,
                baseline_distance_miles=resolve_baseline_distance(origin, row.destination, routes)[0],
                baseline_distance_source=resolve_baseline_distance(origin, row.destination, routes)[1],
            ),),
            distance_baseline=baseline_at_target,
            baseline_fixed_cost=fixed_cost,
            baseline_per_mile_rate=per_mile_rate,
            baseline_distance_miles=target_baseline_miles,
            baseline_distance_source=target_distance_source,
        )

    selected = eligible[:k]
    raw_weights = [1.0 / distance**power for distance, _ in selected]
    total_weight = sum(raw_weights)
    normalized = [weight / total_weight for weight in raw_weights]
    residuals = [
        row.cost - (fixed_cost + per_mile_rate * resolve_baseline_distance(origin, row.destination, routes)[0])
        for _, row in selected
    ]
    neighbors = tuple(
        NeighborContribution(
            destination=row.destination,
            observed_cost=row.cost,
            distance_miles=distance,
            idw_weight=weight,
            normalized_weight=share,
            contribution=share * row.cost,
            residual=residual,
            residual_contribution=share * residual,
            baseline_distance_miles=resolve_baseline_distance(origin, row.destination, routes)[0],
            baseline_distance_source=resolve_baseline_distance(origin, row.destination, routes)[1],
        )
        for (distance, row), weight, share, residual in zip(selected, raw_weights, normalized, residuals)
    )
    return Estimate(
        estimated_cost=baseline_at_target + sum(item.residual_contribution for item in neighbors),
        is_observed=False,
        k=k,
        power=power,
        max_observation_distance_miles=max_observation_distance_miles,
        eligible_observation_count=len(eligible),
        coverage=rate_coverage(len(eligible), [item.distance_miles for item in neighbors]),
        neighbors=neighbors,
        distance_baseline=baseline_at_target,
        baseline_fixed_cost=fixed_cost,
        baseline_per_mile_rate=per_mile_rate,
        baseline_distance_miles=target_baseline_miles,
        baseline_distance_source=target_distance_source,
    )
