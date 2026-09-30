from math import degrees

import pytest

from freight_estimator.domain import (
    EARTH_RADIUS_MILES,
    Estimate,
    InsufficientData,
    Location,
    Observation,
    estimate_cost,
    great_circle_miles,
)


def loc(identifier: str, lat: float, lon: float) -> Location:
    return Location(identifier, identifier, lat, lon)


def point_at_miles(identifier: str, distance: float, cost: float = 100.0) -> Observation:
    longitude = degrees(distance / EARTH_RADIUS_MILES)
    return Observation(loc(identifier, 0.0, longitude), cost)


def test_exact_observation_returns_its_cost_without_dividing_by_zero():
    target = loc("target", 41.0, -90.0)
    estimate = estimate_cost(target, [Observation(target, 1234.5), Observation(loc("far", 42.0, -90.0), 900)], origin=target)
    assert isinstance(estimate, Estimate)
    assert estimate.is_observed
    assert estimate.estimated_cost == 1234.5
    assert estimate.coverage is None
    assert estimate.neighbors[0].normalized_weight == 1


def test_inverse_distance_weights_interpolate_local_residuals():
    target = loc("target", 0, 0)
    near, far = loc("near", 0, 1), loc("far", 0, 2)
    estimate = estimate_cost(target, [Observation(far, 300), Observation(near, 100)], origin=loc("origin", 0, 1.5), k=2, power=2)
    assert isinstance(estimate, Estimate)
    assert [row.destination.id for row in estimate.neighbors] == ["near", "far"]
    assert estimate.neighbors[0].normalized_weight > estimate.neighbors[1].normalized_weight
    assert sum(row.normalized_weight for row in estimate.neighbors) == pytest.approx(1)
    assert sum(row.normalized_weight * row.residual for row in estimate.neighbors) == pytest.approx(
        sum(row.residual_contribution for row in estimate.neighbors)
    )
    assert estimate.estimated_cost == pytest.approx(
        estimate.distance_baseline + sum(row.residual_contribution for row in estimate.neighbors)
    )


def test_osrm_miles_fit_baseline_while_straight_line_distance_selects_neighbors():
    origin = loc("origin", 0, 0)
    target = loc("target", 0, 1.5)
    near, far = loc("near", 0, 1), loc("far", 0, 2)
    estimate = estimate_cost(
        target,
        [Observation(near, 1000), Observation(far, 2000)],
        origin=origin,
        driving_miles={"near": 100, "far": 300, "target": 150},
        k=2,
    )

    assert isinstance(estimate, Estimate)
    assert estimate.baseline_per_mile_rate == pytest.approx(5)
    assert estimate.baseline_distance_miles == 150
    assert estimate.baseline_distance_source == "osrm"
    assert estimate.estimated_cost == pytest.approx(1250)
    assert {row.destination.id: row.baseline_distance_miles for row in estimate.neighbors} == {"near": 100, "far": 300}
    assert all(row.baseline_distance_source == "osrm" for row in estimate.neighbors)
    assert all(row.distance_miles == pytest.approx(great_circle_miles(target, row.destination)) for row in estimate.neighbors)


def test_missing_osrm_distance_uses_road_factor_fallback():
    origin = loc("origin", 0, 0)
    target = loc("target", 0, 1.5)
    result = estimate_cost(
        target,
        [Observation(loc("near", 0, 1), 1000), Observation(loc("far", 0, 2), 2000)],
        origin=origin,
        driving_miles={"near": 100, "far": 300},
        k=2,
    )

    assert isinstance(result, Estimate)
    assert result.baseline_distance_source == "factor_fallback"
    assert result.baseline_distance_miles == pytest.approx(1.18 * great_circle_miles(origin, target))
    assert all(row.baseline_distance_source == "osrm" for row in result.neighbors)


def test_more_than_k_observations_inside_radius_uses_nearest_k_only():
    target = loc("target", 0, 0)
    rows = [point_at_miles(str(distance), distance, distance) for distance in (100, 200, 300, 700)]
    estimate = estimate_cost(target, rows, origin=target, k=2, max_observation_distance_miles=400)
    assert isinstance(estimate, Estimate)
    assert estimate.eligible_observation_count == 3
    assert [row.distance_miles for row in estimate.neighbors] == pytest.approx([100, 200])
    assert estimate.coverage.used_observation_count == 2


def test_exactly_k_observations_inside_radius_uses_all_eligible_rows():
    target = loc("target", 0, 0)
    rows = [point_at_miles(str(distance), distance, distance) for distance in (100, 200, 500)]
    estimate = estimate_cost(target, rows, origin=target, k=3, max_observation_distance_miles=500)
    assert isinstance(estimate, Estimate)
    assert estimate.eligible_observation_count == 3
    assert len(estimate.neighbors) == 3


def test_fewer_than_k_observations_inside_radius_uses_only_available_rows():
    target = loc("target", 0, 0)
    rows = [point_at_miles("near", 100), point_at_miles("far", 300), point_at_miles("outside", 700)]
    estimate = estimate_cost(target, rows, origin=target, k=5, max_observation_distance_miles=400)
    assert isinstance(estimate, Estimate)
    assert estimate.eligible_observation_count == 2
    assert len(estimate.neighbors) == 2


def test_one_observation_inside_radius_still_produces_an_estimate():
    target = loc("target", 0, 0)
    estimate = estimate_cost(
        target,
        [point_at_miles("near", 146, 875), point_at_miles("far", 680, 1400)],
        origin=target,
        k=3,
        max_observation_distance_miles=600,
    )
    assert isinstance(estimate, Estimate)
    assert estimate.estimated_cost == pytest.approx(
        estimate.distance_baseline + sum(row.residual_contribution for row in estimate.neighbors)
    )
    assert estimate.eligible_observation_count == 1
    assert len(estimate.neighbors) == 1


def test_no_observations_inside_radius_is_a_first_class_result():
    target = loc("target", 0, 0)
    result = estimate_cost(target, [point_at_miles("far", 680)], origin=target, max_observation_distance_miles=600)
    assert isinstance(result, InsufficientData)
    assert result.coverage.level.value == "none"
    assert result.coverage.eligible_observation_count == 0
    assert result.nearest_available_observation_distance_miles == pytest.approx(680)


def test_observation_on_maximum_distance_boundary_is_eligible():
    target = loc("target", 0, 0)
    boundary = point_at_miles("boundary", 600, 900)
    boundary_distance = great_circle_miles(target, boundary.destination)
    result = estimate_cost(target, [boundary], origin=target, k=1, max_observation_distance_miles=boundary_distance)
    assert isinstance(result, Estimate)
    assert result.eligible_observation_count == 1
    assert result.neighbors[0].observed_cost == 900


def test_observation_immediately_beyond_maximum_distance_is_excluded():
    target = loc("target", 0, 0)
    boundary = point_at_miles("outside", 600.01)
    radius = great_circle_miles(target, point_at_miles("at-radius", 600).destination)
    result = estimate_cost(target, [boundary], origin=target, max_observation_distance_miles=radius)
    assert isinstance(result, InsufficientData)
    assert result.nearest_available_observation_distance_miles > radius


def test_invalid_parameters_are_rejected():
    observation = point_at_miles("known", 100)
    with pytest.raises(ValueError, match="at least 1"):
        estimate_cost(loc("target", 0, 0), [observation], origin=loc("target", 0, 0), k=0)
    with pytest.raises(ValueError, match="greater than 0"):
        estimate_cost(loc("target", 0, 0), [observation], origin=loc("target", 0, 0), power=0)
    with pytest.raises(ValueError, match="distance"):
        estimate_cost(loc("target", 0, 0), [observation], origin=loc("target", 0, 0), max_observation_distance_miles=0)


def test_great_circle_distance_is_in_miles():
    assert great_circle_miles(loc("a", 0, 0), loc("b", 0, 1)) == pytest.approx(69.09, abs=0.1)
