"""Framework-independent inverse distance weighted freight estimator."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Sequence, TypeAlias

from freight_estimator.coverage import Coverage, rate_coverage

EARTH_RADIUS_MILES = 3958.7613
DEFAULT_MAX_OBSERVATION_DISTANCE_MILES = 600.0


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


def estimate_cost(
    target: Location,
    observations: Sequence[Observation],
    *,
    k: int = 5,
    power: float = 2.0,
    max_observation_distance_miles: float = DEFAULT_MAX_OBSERVATION_DISTANCE_MILES,
) -> EstimateResult:
    """Estimate a target cost using up to K observations inside the distance limit.

    A direct observation at the target coordinate is returned as an observed rate.
    If no historical observations qualify, return InsufficientData; the radius is
    never expanded to fill K.
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
    eligible = [item for item in measured if item[0] <= max_observation_distance_miles]
    if not eligible:
        return InsufficientData(
            max_observation_distance_miles=max_observation_distance_miles,
            coverage=rate_coverage(0, ()),
            nearest_available_observation_distance_miles=measured[0][0] if measured else None,
        )

    exact = next(((distance, row) for distance, row in eligible if distance < 1e-9), None)
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
            neighbors=(NeighborContribution(row.destination, row.cost, distance, 0.0, 1.0, row.cost),),
        )

    selected = eligible[:k]
    raw_weights = [1.0 / distance**power for distance, _ in selected]
    total_weight = sum(raw_weights)
    normalized = [weight / total_weight for weight in raw_weights]
    neighbors = tuple(
        NeighborContribution(
            destination=row.destination,
            observed_cost=row.cost,
            distance_miles=distance,
            idw_weight=weight,
            normalized_weight=share,
            contribution=share * row.cost,
        )
        for (distance, row), weight, share in zip(selected, raw_weights, normalized)
    )
    return Estimate(
        estimated_cost=sum(item.contribution for item in neighbors),
        is_observed=False,
        k=k,
        power=power,
        max_observation_distance_miles=max_observation_distance_miles,
        eligible_observation_count=len(eligible),
        coverage=rate_coverage(len(eligible), [item.distance_miles for item in neighbors]),
        neighbors=neighbors,
    )
