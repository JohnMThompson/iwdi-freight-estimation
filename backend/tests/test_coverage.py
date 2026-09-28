import pytest

from freight_estimator.coverage import CoverageLevel, rate_coverage


@pytest.mark.parametrize(
    ("eligible", "distances", "expected"),
    [
        (8, [80, 120, 170, 220, 299], CoverageLevel.STRONG),
        (7, [100, 180, 300], CoverageLevel.MODERATE),
        (4, [110, 430], CoverageLevel.LIMITED),
        (9, [20], CoverageLevel.SPARSE),
        (0, [], CoverageLevel.NONE),
    ],
)
def test_coverage_ratings_use_count_and_furthest_distance(eligible, distances, expected):
    coverage = rate_coverage(eligible, distances)
    assert coverage.level is expected
    assert coverage.eligible_observation_count == eligible
    assert coverage.used_observation_count == len(distances)
    assert coverage.nearest_observation_distance_miles == (min(distances) if distances else None)
    assert coverage.furthest_contributing_observation_distance_miles == (max(distances) if distances else None)


def test_coverage_threshold_boundaries_are_inclusive():
    assert rate_coverage(5, [60, 100, 150, 220, 300]).level is CoverageLevel.STRONG
    assert rate_coverage(3, [100, 250, 450]).level is CoverageLevel.MODERATE
    assert rate_coverage(2, [100, 600]).level is CoverageLevel.LIMITED
