"""Descriptive observation coverage rules, kept separate for later validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class CoverageLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    LIMITED = "limited"
    SPARSE = "sparse"
    NONE = "none"


@dataclass(frozen=True)
class Coverage:
    level: CoverageLevel
    eligible_observation_count: int
    used_observation_count: int
    nearest_observation_distance_miles: float | None
    furthest_contributing_observation_distance_miles: float | None


def rate_coverage(
    eligible_observation_count: int,
    contributing_distances_miles: Sequence[float],
) -> Coverage:
    """Rate evidence by number of contributors and distance to the furthest one.

    Initial descriptive bands: Strong is at least five contributors within 300 mi;
    Moderate is at least three within 450 mi; Limited is at least two within 600 mi.
    The values are working thresholds, not empirically calibrated error bands.
    """
    distances = sorted(contributing_distances_miles)
    used_count = len(distances)
    nearest = distances[0] if distances else None
    furthest = distances[-1] if distances else None

    if used_count == 0:
        level = CoverageLevel.NONE
    elif used_count >= 5 and furthest <= 300:
        level = CoverageLevel.STRONG
    elif used_count >= 3 and furthest <= 450:
        level = CoverageLevel.MODERATE
    elif used_count >= 2 and furthest <= 600:
        level = CoverageLevel.LIMITED
    else:
        level = CoverageLevel.SPARSE

    return Coverage(
        level=level,
        eligible_observation_count=eligible_observation_count,
        used_observation_count=used_count,
        nearest_observation_distance_miles=nearest,
        furthest_contributing_observation_distance_miles=furthest,
    )
