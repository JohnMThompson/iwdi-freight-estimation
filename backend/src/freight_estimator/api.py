"""HTTP API for the freight estimation slice."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from freight_estimator.coverage import Coverage
from freight_estimator.domain import (
    DEFAULT_MAX_OBSERVATION_DISTANCE_MILES,
    Estimate,
    InsufficientData,
    Location,
    Observation,
    estimate_cost,
)
from freight_estimator.data.synthetic import DESTINATIONS, ORIGINS, Origin

DATA_FILE = Path(__file__).with_name("data") / "shipments.csv"
ROUTE_MILES_FILE = Path(__file__).with_name("data") / "osrm_driving_miles.csv"


class LocationResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float


class OriginResponse(LocationResponse):
    pass


class DestinationResponse(LocationResponse):
    zip: str
    has_observation: bool


class EstimateRequest(BaseModel):
    origin_id: str
    destination_zip: str
    k: int = Field(default=5, ge=1, le=20)
    p: float = Field(default=2.0, gt=0, le=5)
    max_observation_distance_miles: float = Field(
        default=DEFAULT_MAX_OBSERVATION_DISTANCE_MILES,
        gt=0,
        le=5000,
        allow_inf_nan=False,
    )


class NeighborResponse(BaseModel):
    destination: DestinationResponse
    observed_cost: float
    distance_miles: float
    idw_weight: float
    normalized_weight: float
    contribution: float
    residual: float
    residual_contribution: float
    baseline_distance_miles: float
    baseline_distance_source: str


class CoverageResponse(BaseModel):
    level: str
    eligible_observation_count: int
    used_observation_count: int
    nearest_observation_distance_miles: float | None
    furthest_contributing_observation_distance_miles: float | None


class EstimateResponse(BaseModel):
    origin: OriginResponse
    destination: DestinationResponse
    status: str
    estimated_cost: float | None
    is_observed: bool
    k: int
    p: float
    baseline_fixed_cost: float | None
    baseline_per_mile_rate: float | None
    distance_baseline: float | None
    baseline_distance_miles: float | None
    baseline_distance_source: str | None
    max_observation_distance_miles: float
    coverage: CoverageResponse | None
    nearest_available_observation_distance_miles: float | None = None
    message: str | None = None
    neighbors: list[NeighborResponse]


@lru_cache(maxsize=1)
def _load_rows() -> list[tuple[str, Observation]]:
    with DATA_FILE.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return [
            (
                row["origin_id"],
                Observation(
                    Location(row["destination_zip"], row["destination_name"], float(row["destination_latitude"]), float(row["destination_longitude"])),
                    float(row["observed_cost"]),
                ),
            )
            for row in rows
        ]


@lru_cache(maxsize=1)
def _load_route_miles() -> dict[str, dict[str, float]]:
    by_origin: dict[str, dict[str, float]] = {}
    with ROUTE_MILES_FILE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_origin.setdefault(row["origin_id"], {})[row["destination_zip"]] = float(row["osrm_driving_miles"])
    return by_origin


def _destination_response(location: Location, *, has_observation: bool = True) -> DestinationResponse:
    return DestinationResponse(id=location.id, zip=location.id, name=location.name, latitude=location.latitude, longitude=location.longitude, has_observation=has_observation)


def _coverage_response(coverage: Coverage) -> CoverageResponse:
    return CoverageResponse(
        level=coverage.level.value,
        eligible_observation_count=coverage.eligible_observation_count,
        used_observation_count=coverage.used_observation_count,
        nearest_observation_distance_miles=coverage.nearest_observation_distance_miles,
        furthest_contributing_observation_distance_miles=coverage.furthest_contributing_observation_distance_miles,
    )


app = FastAPI(title="Synthetic Freight Cost Estimator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/healthz", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    """Report process availability without checking data or dependencies."""
    return {"status": "ok"}


@app.get("/api/origins", response_model=list[OriginResponse])
async def list_origins() -> list[OriginResponse]:
    return [OriginResponse(id=row.id, name=row.name, latitude=row.latitude, longitude=row.longitude) for row in ORIGINS]


@app.get("/api/destinations", response_model=list[DestinationResponse])
async def list_destinations(origin_id: str) -> list[DestinationResponse]:
    if origin_id not in {origin.id for origin in ORIGINS}:
        raise HTTPException(status_code=404, detail="Origin not found")
    observed_ids = {observation.destination.id for row_origin, observation in _load_rows() if row_origin == origin_id}
    return [
        DestinationResponse(
            id=zip_code, zip=zip_code, name=name, latitude=latitude, longitude=longitude,
            has_observation=zip_code in observed_ids,
        )
        for zip_code, name, latitude, longitude in sorted(DESTINATIONS, key=lambda item: (item[1], item[0]))
    ]


@app.post("/api/estimate", response_model=EstimateResponse)
async def get_estimate(request: EstimateRequest) -> EstimateResponse:
    origin = next((item for item in ORIGINS if item.id == request.origin_id), None)
    if origin is None:
        raise HTTPException(status_code=404, detail="Origin not found")
    all_rows = [observation for row_origin, observation in _load_rows() if row_origin == request.origin_id]
    target_data = next((row for row in DESTINATIONS if row[0] == request.destination_zip), None)
    if target_data is not None:
        target = Location(target_data[0], target_data[1], target_data[2], target_data[3])
    else:
        raise HTTPException(status_code=404, detail="Destination ZIP not found for this origin")
    target_observation = next((item for item in all_rows if item.destination.id == request.destination_zip), None)
    try:
        estimate = estimate_cost(
            target,
            all_rows,
            origin=Location(origin.id, origin.name, origin.latitude, origin.longitude),
            k=request.k,
            power=request.p,
            max_observation_distance_miles=request.max_observation_distance_miles,
            driving_miles=_load_route_miles().get(origin.id, {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if isinstance(estimate, InsufficientData):
        return EstimateResponse(
            origin=OriginResponse(id=origin.id, name=origin.name, latitude=origin.latitude, longitude=origin.longitude),
            destination=_destination_response(target, has_observation=target_observation is not None),
            status="insufficient_data",
            estimated_cost=None,
            is_observed=False,
            k=request.k,
            p=request.p,
            baseline_fixed_cost=None,
            baseline_per_mile_rate=None,
            distance_baseline=None,
            baseline_distance_miles=None,
            baseline_distance_source=None,
            max_observation_distance_miles=request.max_observation_distance_miles,
            coverage=_coverage_response(estimate.coverage),
            nearest_available_observation_distance_miles=estimate.nearest_available_observation_distance_miles,
            message="No historical observations for this origin fall within the selected observation radius.",
            neighbors=[],
        )

    assert isinstance(estimate, Estimate)
    neighbors = estimate.neighbors
    return EstimateResponse(
        origin=OriginResponse(id=origin.id, name=origin.name, latitude=origin.latitude, longitude=origin.longitude),
        destination=_destination_response(target, has_observation=target_observation is not None),
        status="observed" if estimate.is_observed else "estimated",
        estimated_cost=estimate.estimated_cost,
        is_observed=estimate.is_observed,
        k=request.k,
        p=estimate.power,
        baseline_fixed_cost=estimate.baseline_fixed_cost,
        baseline_per_mile_rate=estimate.baseline_per_mile_rate,
        distance_baseline=estimate.distance_baseline,
        baseline_distance_miles=estimate.baseline_distance_miles,
        baseline_distance_source=estimate.baseline_distance_source,
        max_observation_distance_miles=estimate.max_observation_distance_miles,
        coverage=_coverage_response(estimate.coverage) if estimate.coverage else None,
        neighbors=[
            NeighborResponse(
                destination=_destination_response(item.destination, has_observation=True),
                observed_cost=item.observed_cost,
                distance_miles=item.distance_miles,
                idw_weight=item.idw_weight,
                normalized_weight=item.normalized_weight,
                contribution=item.contribution,
                residual=item.residual,
                residual_contribution=item.residual_contribution,
                baseline_distance_miles=item.baseline_distance_miles,
                baseline_distance_source=item.baseline_distance_source,
            )
            for item in neighbors
        ],
    )
