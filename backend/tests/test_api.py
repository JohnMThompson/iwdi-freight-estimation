import asyncio

import httpx

from freight_estimator.api import app


def request(method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(send())


def test_origins_and_destination_catalog_are_available():
    origins = request("GET", "/api/origins").json()
    assert len(origins) == 3
    destinations = request("GET", "/api/destinations", params={"origin_id": "mpls"})
    assert destinations.status_code == 200
    assert destinations.json()


def test_estimate_response_contains_explainable_neighbors():
    response = request("POST", "/api/estimate", json={"origin_id": "mpls", "destination_zip": "55401", "k": 4, "p": 2})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "estimated"
    assert result["estimated_cost"] > 0
    assert len(result["neighbors"]) == 4
    assert result["max_observation_distance_miles"] == 600
    assert result["coverage"]["eligible_observation_count"] >= result["coverage"]["used_observation_count"]
    assert result["coverage"]["used_observation_count"] == len(result["neighbors"])
    assert {"observed_cost", "distance_miles", "idw_weight", "normalized_weight", "contribution"} <= result["neighbors"][0].keys()


def test_insufficient_data_is_a_successful_domain_response():
    response = request("POST", "/api/estimate", json={
        "origin_id": "mpls",
        "destination_zip": "55401",
        "max_observation_distance_miles": 0.1,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "insufficient_data"
    assert result["estimated_cost"] is None
    assert result["neighbors"] == []
    assert result["coverage"]["level"] == "none"
    assert result["coverage"]["eligible_observation_count"] == 0
    assert result["message"].startswith("No historical observations")


def test_known_destination_still_returns_observed_rate():
    response = request("POST", "/api/estimate", json={"origin_id": "mpls", "destination_zip": "55101"})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "observed"
    assert result["is_observed"]
    assert result["coverage"] is None


def test_unknown_location_is_a_clear_404():
    response = request("POST", "/api/estimate", json={"origin_id": "mpls", "destination_zip": "99999"})
    assert response.status_code == 404
