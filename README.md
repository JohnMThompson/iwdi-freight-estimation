# Freight Cost Estimator

A small, explainable freight estimation application based on inverse distance weighting (IDW). It recreates the 2018 project's core workflow: choose an origin and destination, then estimate linehaul cost from nearby destinations with known observations.

All shipment observations in this project are synthetic. They are generated for this application and do not represent actual customer shipments, freight rates, or market benchmarks. The generator gives costs a plausible spatial structure so the estimator can be explored; it is not calibrated to current market data.

## Run locally

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn freight_estimator.api:app --reload
```

The API runs at `http://localhost:8000`; interactive API docs are at `/docs`.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. The development server proxies `/api` requests to the API.

## Estimation method

For one origin, the estimator first filters observed destinations to a configurable maximum straight-line distance, then selects up to K of the closest eligible observations. It never reaches beyond the configured radius to fill K. The initial working default is 600 miles; it is configurable and has not been validated as an accuracy threshold. It computes great-circle distance in miles and weights each cost by `1 / distance^p`. The estimate is the weighted mean. The API returns each contributor's distance, raw IDW weight, normalized weight, and weighted cost contribution, so the result can be inspected directly.

When the requested destination has an observation for the selected origin, the application returns that exact observed cost rather than calculating an interpolation. The UI labels this case as an observed rate. If no observations fall inside the selected radius, the model returns an insufficient-data result without an estimate.

Coverage is a descriptive summary of the number and proximity of observations supporting an interpolated estimate. The initial rules are Strong for at least five contributors with the furthest within 300 miles, Moderate for at least three within 450 miles, Limited for at least two within 600 miles, Sparse for a smaller or more distant set, and None when no observation qualifies. These rules are intentionally isolated and are not probability or calibrated accuracy statements; empirical validation may change them.

The map uses OpenStreetMap tiles and shows the origin, selected destination, contributing observations, and straight lines between the estimate and its neighbors. Lines visualize geographic proximity; they are not truck routes.

## Data generation

`backend/src/freight_estimator/data/synthetic.py` is intentionally separate from the estimator. A fixed random seed makes its compact dataset reproducible. Several origins receive different regional cost surfaces plus lane noise, and each origin has a sparse set of observed ZIP-like destinations. ZIPs and coordinates are representative synthetic locations, not authoritative ZIP centroid data.

The generated records are checked in at `backend/src/freight_estimator/data/shipments.csv` so the application starts with a stable, inspectable dataset. To regenerate the file after changing the generator:

```bash
cd backend
python -m freight_estimator.data.synthetic
```

## API

- `GET /api/origins` returns available origins.
- `GET /api/destinations?origin_id=...` returns candidate destinations and whether each has an observation for that origin.
- `POST /api/estimate` accepts an origin, destination ZIP, `k`, `p`, and `max_observation_distance_miles`; response includes estimate status, Coverage facts, and contributing observations.

Defaults are `k=5`, `p=2`, and `max_observation_distance_miles=600`. This is a small demonstration slice: there is no persistence, external market-data refresh, live ZIP geocoding, or backtesting yet.
