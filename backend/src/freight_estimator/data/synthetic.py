"""Generate reproducible, synthetic freight observations with spatial structure."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from freight_estimator.domain import Location, Observation, great_circle_miles


@dataclass(frozen=True)
class Origin:
    id: str
    name: str
    latitude: float
    longitude: float


ORIGINS = (
    Origin("mpls", "Minneapolis, MN", 44.9778, -93.2650),
    Origin("dallas", "Dallas, TX", 32.7767, -96.7970),
    Origin("atl", "Atlanta, GA", 33.7490, -84.3880),
)

# Synthetic ZIP-like identifiers and approximate U.S. city coordinates.
DESTINATIONS = (
    ("55401", "Minneapolis, MN", 44.9833, -93.2667),
    ("55101", "Saint Paul, MN", 44.9444, -93.0933),
    ("53202", "Milwaukee, WI", 43.0389, -87.9065),
    ("60601", "Chicago, IL", 41.8864, -87.6231),
    ("46204", "Indianapolis, IN", 39.7684, -86.1581),
    ("63101", "St. Louis, MO", 38.6270, -90.1994),
    ("48226", "Detroit, MI", 42.3314, -83.0458),
    ("44114", "Cleveland, OH", 41.4993, -81.6944),
    ("43215", "Columbus, OH", 39.9612, -82.9988),
    ("55415", "Minneapolis South, MN", 44.9700, -93.2500),
    ("75201", "Dallas, TX", 32.7876, -96.7994),
    ("73102", "Oklahoma City, OK", 35.4676, -97.5164),
    ("64106", "Kansas City, MO", 39.0997, -94.5786),
    ("72201", "Little Rock, AR", 34.7465, -92.2896),
    ("70112", "New Orleans, LA", 29.9511, -90.0715),
    ("77002", "Houston, TX", 29.7604, -95.3698),
    ("78701", "Austin, TX", 30.2672, -97.7431),
    ("75001", "Dallas North, TX", 32.9618, -96.8292),
    ("30303", "Atlanta, GA", 33.7525, -84.3915),
    ("28202", "Charlotte, NC", 35.2271, -80.8431),
    ("37201", "Nashville, TN", 36.1627, -86.7816),
    ("35203", "Birmingham, AL", 33.5186, -86.8104),
    ("29601", "Greenville, SC", 34.8526, -82.3940),
    ("32801", "Orlando, FL", 28.5383, -81.3792),
    ("33130", "Miami, FL", 25.7617, -80.1918),
    ("20001", "Washington, DC", 38.9072, -77.0369),
    ("19103", "Philadelphia, PA", 39.9526, -75.1652),
    ("10001", "New York, NY", 40.7506, -73.9972),
    ("15222", "Pittsburgh, PA", 40.4406, -79.9959),
    ("02108", "Boston, MA", 42.3570, -71.0637),
    ("27601", "Raleigh, NC", 35.7796, -78.6382),
    ("97201", "Portland, OR", 45.5152, -122.6784),
    ("98101", "Seattle, WA", 47.6101, -122.3344),
    ("94103", "San Francisco, CA", 37.7739, -122.4312),
    ("90012", "Los Angeles, CA", 34.0522, -118.2437),
    ("85004", "Phoenix, AZ", 33.4484, -112.0740),
    ("80202", "Denver, CO", 39.7525, -104.9995),
    ("84101", "Salt Lake City, UT", 40.7608, -111.8910),
    ("87102", "Albuquerque, NM", 35.0844, -106.6504),
    ("80903", "Colorado Springs, CO", 38.8339, -104.8214),
)


def generate_observations(seed: int = 2018) -> list[tuple[Origin, Observation]]:
    rng = random.Random(seed)
    result: list[tuple[Origin, Observation]] = []
    for origin_index, origin in enumerate(ORIGINS):
        # Each origin has a deterministic but different sparse coverage pattern.
        chosen = [row for index, row in enumerate(DESTINATIONS) if (index + origin_index * 3) % 4 != 0]
        for row in chosen:
            zip_code, name, lat, lon = row
            destination = Location(zip_code, name, lat, lon)
            # A simple linehaul surface: dispatch floor + distance component + local lane noise.
            miles = great_circle_miles(Location(origin.id, origin.name, origin.latitude, origin.longitude), destination)
            cost = round(450 + miles * 2.25 + rng.uniform(-180, 180), 2)
            result.append((origin, Observation(destination, max(500.0, cost))))
    return result


def write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["origin_id", "origin_name", "origin_latitude", "origin_longitude", "destination_zip", "destination_name", "destination_latitude", "destination_longitude", "observed_cost"])
        for origin, observation in generate_observations():
            destination = observation.destination
            writer.writerow([origin.id, origin.name, origin.latitude, origin.longitude, destination.id, destination.name, destination.latitude, destination.longitude, f"{observation.cost:.2f}"])


if __name__ == "__main__":
    write_csv(Path(__file__).with_name("shipments.csv"))
